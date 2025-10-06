import json
import re
import sqlite3
import xml.etree.ElementTree as ET
import requests
from contextlib import closing
from datetime import datetime
from functools import lru_cache
from typing import Iterable, Optional, Set, Tuple

from bs4 import BeautifulSoup

from config import (
    WECHAT_API_INCLUDE_CONTENT_FOR_NEW,
    WECHAT_API_MAX_PAGES,
    WECHAT_API_PAGE_SIZE,
    WECHAT_FORCE_REFRESH,
    WECHAT_RSS_URL,
)
from we_mp_rss_api import APIError, AuthError, WeMPRSSClient
from we_mp_rss_sync import locate_we_rss_root

# --- 新的配置区域 ---
# 移除硬编码的 RSS_URL
# --------------------

_refresh_attempted = False

_GENERIC_WECHAT_LABELS = {
    'wechat', '微信公众号', 'weixin', 'wx', 'mp', '公众号', 'official account'
}

_SCRAPE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/128.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'zh-CN,zh;q=0.9'
}


@lru_cache(maxsize=256)
def _scrape_mp_name_from_article(url: Optional[str]) -> Optional[str]:
    normalized = _normalize_wechat_url(url)
    if not normalized:
        return None

    try:
        response = requests.get(normalized, headers=_SCRAPE_HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        return None

    html = response.text or ''
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    selectors = (
        '#js_wx_account_nickname',
        '#js_wx_follow_nickname',
        '#js_wx_account_name',
        '#js_name',
        '.profile_nickname',
        '.wx_follow_nickname',
        '[aria-labelledby="js_wx_follow_nickname"]',
    )

    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(strip=True)
            if text:
                return text

    meta = soup.find('meta', attrs={'property': 'og:site_name'})
    if meta:
        text = (meta.get('content') or '').strip()
        if text:
            return text

    fallback_match = re.search(r'id="js_wx_follow_nickname"[^>]*>([^<]+)', html)
    if fallback_match:
        text = fallback_match.group(1).strip()
        if text:
            return text

    return None


def _should_scrape_mp_label(name: Optional[str]) -> bool:
    if not name:
        return True
    lowered = name.strip().lower()
    if not lowered:
        return True
    return lowered in _GENERIC_WECHAT_LABELS


def _normalize_wechat_url(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    return cleaned.rstrip('/')


def _normalize_publish_time(value) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value)).isoformat()
        except (OverflowError, ValueError):  # pragma: no cover - 防御性
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            try:
                return datetime.fromtimestamp(int(text)).isoformat()
            except (OverflowError, ValueError):
                return text
        return text

    return None


@lru_cache(maxsize=1)
def _load_article_source_map() -> dict[str, str]:
    root_path = locate_we_rss_root()
    if root_path is None:
        return {}

    db_path = root_path / 'data' / 'db.db'
    if not db_path.exists():
        return {}

    mapping: dict[str, str] = {}
    try:
        with closing(sqlite3.connect(db_path, timeout=1)) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT a.url AS article_url, f.mp_name AS mp_name
                    FROM articles AS a
                    LEFT JOIN feeds AS f ON a.mp_id = f.id
                    WHERE a.url IS NOT NULL AND f.mp_name IS NOT NULL
                    """
                )
                for row in cursor.fetchall():
                    url = _normalize_wechat_url(row['article_url'])
                    name = (row['mp_name'] or '').strip()
                    if url and name:
                        mapping[url] = name
                        if url.startswith('http://'):
                            https_variant = 'https://' + url[len('http://'):]
                            mapping.setdefault(https_variant, name)
                        elif url.startswith('https://'):
                            http_variant = 'http://' + url[len('https://'):]
                            mapping.setdefault(http_variant, name)

    except Exception as exc:  # pragma: no cover - 本地环境问题记录日志即可
        print(f"警告: 读取 We-MP-RSS 数据库失败，无法映射公众号名称: {exc}")
        return {}

    return mapping


def _load_api_article_index() -> Tuple[dict[str, dict], Optional[WeMPRSSClient]]:
    try:
        client = WeMPRSSClient()
    except AuthError as exc:
        print(f"警告: 无法登录 We-MP-RSS API，跳过接口增强。原因: {exc}")
        return {}, None

    enriched: dict[str, dict] = {}
    page_size = max(1, WECHAT_API_PAGE_SIZE)
    max_pages = WECHAT_API_MAX_PAGES if WECHAT_API_MAX_PAGES > 0 else None

    try:
        for item in client.iter_articles(page_size=page_size, max_pages=max_pages):
            link = item.get('link') or item.get('source_url') or item.get('url')
            normalized = _normalize_wechat_url(link)
            if not normalized:
                continue

            enriched[normalized] = {
                'id': item.get('id'),
                'title': item.get('title'),
                'link': link or normalized,
                'author': item.get('author') or item.get('mp_name') or item.get('account'),
                'mp_name': item.get('mp_name') or item.get('mpNickname') or item.get('account'),
                'publish_time': _normalize_publish_time(item.get('publish_time')),
                'digest': item.get('digest'),
            }

    except (APIError, AuthError, requests.RequestException) as exc:
        print(f"警告: 调用 We-MP-RSS API 列表失败，跳过接口增强。原因: {exc}")
        return {}, None

    if not enriched:
        return {}, None

    return enriched, client


def _extract_first_text_by_names(element: ET.Element, candidate_names: Iterable[str]) -> Optional[str]:
    """在忽略命名空间的情况下，从元素的子节点或属性中提取首个匹配候选名称的文本。"""

    if not isinstance(element, ET.Element):  # 简单防御
        return None

    candidate_lower = {name.lower() for name in candidate_names}

    for child in element.iter():
        if not isinstance(child.tag, str):
            continue
        local_name = child.tag.split('}')[-1].lower()
        if local_name not in candidate_lower:
            continue
        text = (child.text or '').strip()
        if text:
            return text

    for attr_name, attr_value in element.attrib.items():
        if attr_name.lower() in candidate_lower and attr_value and attr_value.strip():
            return attr_value.strip()

    return None


def _collect_category_labels(element: ET.Element) -> list[str]:
    """收集 item 中的类别标签，通常 RSS 会用来标记来源或话题。"""

    labels: list[str] = []
    for child in element.iter():
        if not isinstance(child.tag, str):
            continue
        local_name = child.tag.split('}')[-1].lower()
        if local_name != 'category':
            continue
        text = (child.text or '').strip()
        if text and text not in labels:
            labels.append(text)

    return labels


def _trigger_we_rss_refresh_once() -> None:
    """在本进程生命周期内只触发一次 We-MP-RSS 主动刷新。"""

    global _refresh_attempted  # noqa: PLW0603 - 简单的进程级标记

    if _refresh_attempted or not WECHAT_FORCE_REFRESH:
        return

    _refresh_attempted = True
    try:
        from we_mp_rss_sync import refresh_wechat_articles
    except ImportError as exc:  # pragma: no cover - 外部依赖
        print(f"警告: 无法导入 We-MP-RSS 同步模块，跳过刷新。原因: {exc}")
        return

    if not refresh_wechat_articles():
        print('警告: We-MP-RSS 主动刷新失败，将继续使用现有 RSS 数据。')


def fetch_articles_from_rss() -> list[dict]:
    """抓取 RSS 数据并用 We-MP-RSS API 进行补全。"""

    all_articles_data: list[dict] = []
    source_lookup = _load_article_source_map()
    api_index, api_client = _load_api_article_index()
    seen_links: Set[str] = set()
    api_enhanced = 0
    api_only_count = 0

    _trigger_we_rss_refresh_once()

    print(f"尝试从 RSS Feed 获取所有文章: {WECHAT_RSS_URL}")
    try:
        response = requests.get(WECHAT_RSS_URL, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        channel = root.find('channel')
        if channel is None:
            print("警告: XML 结构异常，未找到 <channel> 标签。")
            return []

        for item in channel.findall('item'):
            title_element = item.find('title')
            link_element = item.find('link')
            guid_element = item.find('guid')
            pubdate_element = item.find('pubDate')
            content_element = item.find('description')  # we-mp-rss 将全文放在 description 中
            author_element = item.find('author')

            author: Optional[str] = None
            if author_element is not None and author_element.text:
                author = author_element.text.strip()
            if not author:
                author = item.findtext('{http://purl.org/dc/elements/1.1/}creator')
                if author:
                    author = author.strip()

            mp_name = _extract_first_text_by_names(
                item,
                (
                    'mpname', 'mp_name', 'mp-nickname', 'mpnickname', 'nickname',
                    'account', 'account_name', 'accountname', 'wechatname',
                    'wechat_name', 'wechatid', 'source', 'publisher', 'origin'
                )
            )

            if not mp_name:
                categories = _collect_category_labels(item)
                if categories:
                    mp_name = categories[0]

            if not author and mp_name:
                author = mp_name

            raw_link = link_element.text.strip() if link_element is not None and link_element.text else None
            raw_guid = guid_element.text.strip() if guid_element is not None and guid_element.text else None
            link_value = raw_link or raw_guid

            unique_candidates: list[str] = []
            for candidate in (raw_link, raw_guid):
                normalized_candidate = _normalize_wechat_url(candidate)
                if normalized_candidate and normalized_candidate not in unique_candidates:
                    unique_candidates.append(normalized_candidate)

            normalized_link = unique_candidates[0] if unique_candidates else None
            for normalized_candidate in unique_candidates:
                seen_links.add(normalized_candidate)
                if normalized_candidate in source_lookup and source_lookup[normalized_candidate].strip():
                    mp_name = source_lookup[normalized_candidate].strip()
                    break

            title = title_element.text if title_element is not None else 'No Title'
            content = content_element.text if content_element is not None else 'No Content'
            content_format = 'Markdown' if content_element is not None else 'Text'

            pub_date = _normalize_publish_time(pubdate_element.text if pubdate_element is not None else None)
            if not pub_date:
                pub_date = datetime.now().isoformat()

            api_meta = None
            if normalized_link:
                api_meta = api_index.get(normalized_link)
            if not api_meta and unique_candidates:
                for candidate in unique_candidates[1:]:
                    api_meta = api_index.get(candidate)
                    if api_meta:
                        normalized_link = candidate
                        break

            enhanced = False
            if api_meta:
                if api_meta.get('mp_name') and api_meta.get('mp_name') != mp_name:
                    mp_name = api_meta['mp_name']
                    enhanced = True
                if (not author or author == '作者未注明') and api_meta.get('author'):
                    author = api_meta['author']
                    enhanced = True
                if api_meta.get('publish_time'):
                    pub_date = api_meta['publish_time']
                    enhanced = True
                if api_meta.get('title') and (not title or title == 'No Title'):
                    title = api_meta['title']
                    enhanced = True
                api_link_value = api_meta.get('link')
                if api_link_value and api_link_value != (link_value or ''):
                    link_value = api_link_value
                    enhanced = True
                if (not content or content == 'No Content') and api_meta.get('digest'):
                    content = api_meta['digest']
                    content_format = 'Text'
                    enhanced = True

            if enhanced:
                api_enhanced += 1

            final_link = link_value or raw_link or raw_guid or normalized_link or 'No Link'
            final_normalized = _normalize_wechat_url(final_link)
            if final_normalized:
                seen_links.add(final_normalized)
                normalized_link = final_normalized
                if final_normalized in source_lookup and source_lookup[final_normalized].strip():
                    mp_name = source_lookup[final_normalized].strip()

            scrape_target = final_link if final_link != 'No Link' else normalized_link
            if _should_scrape_mp_label(mp_name) and scrape_target:
                scraped_name = _scrape_mp_name_from_article(scrape_target)
                if not scraped_name and normalized_link and scrape_target != normalized_link:
                    scraped_name = _scrape_mp_name_from_article(normalized_link)
                if scraped_name:
                    mp_name = scraped_name

            if (not author or author == '作者未注明') and mp_name:
                author = mp_name

            if not author:
                author = '作者未注明'

            mp_label = (mp_name or '微信公众号').strip() or '微信公众号'
            author_label = (author or '').strip()
            if mp_label:
                if author_label and mp_label not in author_label:
                    author_label = f"{author_label} · {mp_label}"
                if not author_label:
                    author_label = mp_label
            else:
                author_label = author_label or '作者未注明'

            all_articles_data.append({
                'title': title,
                'link': final_link,
                'published_time': pub_date,
                'content': content,
                'content_format': content_format,
                'source': mp_label,
                'author': author_label,
                'platform': '微信公众号'
            })

        if api_index:
            for normalized_link, meta in api_index.items():
                if normalized_link in seen_links:
                    continue

                article_id = meta.get('id')
                link = meta.get('link') or normalized_link or 'No Link'
                title = meta.get('title') or 'No Title'
                mp_name = meta.get('mp_name') or '微信公众号'
                author = meta.get('author') or mp_name
                pub_date = meta.get('publish_time') or datetime.now().isoformat()
                content = meta.get('digest') or ''
                content_format = 'Text'

                if WECHAT_API_INCLUDE_CONTENT_FOR_NEW and api_client and article_id:
                    try:
                        detail = api_client.fetch_article_content(int(article_id))
                    except APIError as exc:
                        print(f"警告: 获取文章 {article_id} 正文失败，使用摘要代替。原因: {exc}")
                        detail = None

                    if detail:
                        content = detail.get('content') or content
                        content_format = detail.get('content_format') or 'HTML'
                        pub_detail = _normalize_publish_time(detail.get('publish_time'))
                        if pub_detail:
                            pub_date = pub_detail
                        mp_name = (
                            detail.get('mp_name')
                            or detail.get('mp_nickname')
                            or mp_name
                        )
                        author = detail.get('author') or author or mp_name
                        link = detail.get('link') or link
                        title = detail.get('title') or title

                if not content:
                    content = '暂无正文'

                final_normalized = _normalize_wechat_url(link) or normalized_link
                if final_normalized:
                    seen_links.add(final_normalized)
                    if final_normalized in source_lookup and source_lookup[final_normalized].strip():
                        mp_name = source_lookup[final_normalized].strip()

                scrape_target = link if link and link != 'No Link' else final_normalized
                if _should_scrape_mp_label(mp_name) and scrape_target:
                    scraped_name = _scrape_mp_name_from_article(scrape_target)
                    if not scraped_name and final_normalized and scrape_target != final_normalized:
                        scraped_name = _scrape_mp_name_from_article(final_normalized)
                    if scraped_name:
                        mp_name = scraped_name

                if (not author or author == '作者未注明') and mp_name:
                    author = mp_name

                mp_label = (mp_name or '微信公众号').strip() or '微信公众号'
                author_label = (author or '').strip()
                if mp_label:
                    if author_label and mp_label not in author_label:
                        author_label = f"{author_label} · {mp_label}"
                    if not author_label:
                        author_label = mp_label
                else:
                    author_label = author_label or '作者未注明'

                all_articles_data.append({
                    'title': title,
                    'link': link,
                    'published_time': pub_date,
                    'content': content,
                    'content_format': content_format,
                    'source': mp_label,
                    'author': author_label,
                    'platform': '微信公众号'
                })

                api_only_count += 1
                if normalized_link:
                    seen_links.add(normalized_link)

        if api_enhanced:
            print(f" [API] 已利用 We-MP-RSS 接口增强 {api_enhanced} 篇 RSS 文章。")

        if api_only_count:
            print(f" [API] 额外补充 {api_only_count} 篇仅在接口中返回的文章。")

    except requests.exceptions.RequestException as e:
        print(f"错误: 无法访问 RSS Feed - {e}")
        return []

    print(f"\n成功从 RSS Feed 获取 {len(all_articles_data)} 篇文章（元数据+全文）。")
    return all_articles_data

# ----------------------------------------------------------------------
if __name__ == '__main__':

    print("--- 启动 wechat_pubaccount_fetcher.py 模块自检 (RSS 模式) ---")

    # 1. 模拟输入数据 (在 RSS 模式下，这个列表只用于参考，RSS Feed 获取的是所有订阅号的数据)
    test_mp_names = ["南京大学招生小蓝鲸"]
    print(f"测试公众号列表: {test_mp_names} (RSS将获取所有已订阅号的最新文章)")

    # 2. 直接获取全文数据
    # 原有的 fetch_articles_metadata 和 fetch_articles_with_content 函数已被此函数取代
    full_articles = fetch_articles_from_rss()

    if full_articles:
        print(f"\n成功获取文章总量: {len(full_articles)} 篇")
        print(f"文章第一条示例 (包含全文):\n")
        # 仅显示前 300 字符，避免输出过长
        sample_article = full_articles[0].copy()
        sample_article['content'] = sample_article.get('content', '')[:300] + '...'
        print(json.dumps(sample_article, indent=4, ensure_ascii=False))

        # TODO: 3. 将 full_articles 传入 LLM 进行分析和知识提取
        # LLM_analysis_function(full_articles)
        # ...

    else:
        print("\n警告：未能获取任何文章数据。请检查 we-mp-rss 服务是否正在运行。")