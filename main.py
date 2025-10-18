# main.py

from fetchers.wechat_fetcher_factory import create_wechat_fetcher
from yuque_fetcher import fetch_all_yuque_docs
from ai_processer import process_all_data_with_ai, filter_duplicates
from logger import setup_logger
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor
# --- 修正 3: 引入配置 ---
from config import YUQUE_TOKEN, YUQUE_GROUP, YUQUE_BOOK
from yuque_summarizer import save_data


FINAL_DATA_FILE = 'final_knowledge_base.json'
FETCH_STATE_FILE = 'fetch_state.json'

_WECHAT_ALIASES = {
    'wechat', '微信公众号', 'weixin', 'wx', 'mp', 'official account'
}


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _parse_datetime(value) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return _normalize_datetime(value)

    if isinstance(value, (int, float)):
        try:
            return _normalize_datetime(datetime.fromtimestamp(float(value)))
        except (OverflowError, ValueError):
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        replacement = text.replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(replacement)
            return _normalize_datetime(dt)
        except ValueError:
            try:
                return _normalize_datetime(datetime.fromtimestamp(float(text)))
            except (OverflowError, ValueError):
                return None

    return None


def _load_fetch_state() -> dict:
    path = Path(FETCH_STATE_FILE)
    if not path.exists():
        return {}
    try:
        with path.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _save_fetch_state(state: dict) -> None:
    path = Path(FETCH_STATE_FILE)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)


def _get_last_published_time(state: dict, source: str) -> datetime | None:
    entry = state.get(source)
    if not isinstance(entry, dict):
        return None
    return _parse_datetime(entry.get('last_published_time'))


def _update_last_published_time(state: dict, source: str, value: datetime) -> None:
    normalized = _normalize_datetime(value)
    state.setdefault(source, {})['last_published_time'] = normalized.isoformat()
    _save_fetch_state(state)


def _is_wechat_article(article: dict) -> bool:
    if not isinstance(article, dict):
        return False

    platform = article.get('platform')
    if isinstance(platform, str) and platform.strip().lower() in _WECHAT_ALIASES:
        return True

    source = article.get('source')
    if isinstance(source, str) and source.strip().lower() in _WECHAT_ALIASES:
        return True

    return False


def _filter_new_wechat_articles(
    articles: list[dict],
    last_seen: datetime | None
) -> tuple[list[dict], datetime | None]:
    reference = _normalize_datetime(last_seen) if last_seen else None
    newest = reference
    fresh: list[dict] = []

    for article in articles:
        timestamp = (
            article.get('published_time')
            or article.get('published_at')
            or article.get('updated_at')
        )
        parsed = _parse_datetime(timestamp)

        if parsed and reference and parsed <= reference:
            continue

        fresh.append(article)

        if parsed:
            if newest is None or parsed > newest:
                newest = parsed

    return fresh, newest


def load_existing_knowledge_base(file_path: str = FINAL_DATA_FILE) -> List[dict]:
    path = Path(file_path)
    if not path.exists():
        return []

    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except json.JSONDecodeError:
        print(f"警告: 无法解析现有知识库 {file_path}，将重新生成 AI 摘要。")

    return []


def build_article_key(article: dict) -> str:
    for field in ('slug', 'id', 'link', 'url'):
        value = article.get(field)
        if value:
            return str(value)

    title = article.get('title')
    source = article.get('source')
    if title and source:
        return f"{source}::{title}"

    content = article.get('content')
    if isinstance(content, str) and content:
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    stable_repr = json.dumps(article, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(stable_repr.encode('utf-8')).hexdigest()


def _normalize_text(value) -> str:
    return value.strip() if isinstance(value, str) else ''


def article_changed(new_article: dict, existing_article: dict) -> bool:
    if _is_wechat_article(new_article) or _is_wechat_article(existing_article):
        return False

    new_content = _normalize_text(new_article.get('content'))
    old_content = _normalize_text(existing_article.get('content'))

    if new_content or old_content:
        return new_content != old_content

    new_time = new_article.get('updated_at') or new_article.get('published_at') or new_article.get('published_time')
    old_time = existing_article.get('updated_at') or existing_article.get('published_at') or existing_article.get('published_time')

    if new_time and old_time:
        return str(new_time) > str(old_time)

    return False


def merge_article_with_existing(new_article: dict, existing_article: dict) -> dict:
    merged = existing_article.copy()
    fields_to_sync = [
        'source', 'title', 'slug', 'id', 'url', 'link',
        'published_at', 'published_time', 'author',
        'content', 'content_format', 'platform'
    ]

    for field in fields_to_sync:
        if new_article.get(field) is not None:
            merged[field] = new_article[field]

    return merged


def split_articles_for_processing(
    fresh_articles: List[dict],
    existing_articles: List[dict]
) -> Tuple[List[dict], Dict[str, dict]]:
    existing_map = {build_article_key(item): item for item in existing_articles}

    articles_for_ai: List[dict] = []
    reused_articles: Dict[str, dict] = {}
    seen_keys = set()

    for article in fresh_articles:
        key = build_article_key(article)
        seen_keys.add(key)
        existing_entry = existing_map.get(key)

        if existing_entry and not article_changed(article, existing_entry):
            reused_articles[key] = merge_article_with_existing(article, existing_entry)
        else:
            articles_for_ai.append(article)

    missing_keys = set(existing_map.keys()) - seen_keys
    for key in missing_keys:
        reused_articles[key] = existing_map[key]

    return articles_for_ai, reused_articles


def combine_processed_articles(
    ordered_articles: List[dict],
    processed_articles: List[dict],
    reused_articles: Dict[str, dict]
) -> List[dict]:
    processed_map = {build_article_key(item): item for item in processed_articles}
    final_sequence: List[dict] = []
    included_keys = set()

    for raw_article in ordered_articles:
        key = build_article_key(raw_article)
        if key in processed_map:
            final_sequence.append(processed_map[key])
            included_keys.add(key)
        elif key in reused_articles:
            final_sequence.append(reused_articles[key])
            included_keys.add(key)
        else:
            final_sequence.append(raw_article)
            included_keys.add(key)

    for key, article in reused_articles.items():
        if key not in included_keys:
            final_sequence.append(article)

    return final_sequence


# 移除硬编码的语雀配置

def run_data_aggregation():
    print("--- 启动信息聚合任务 ---")

    fetch_state = _load_fetch_state()
    last_wechat_timestamp = _get_last_published_time(fetch_state, 'wechat')

    # A & B. 并发获取微信和语雀内容
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 通过工厂创建实现（当前默认仍为 We-MP-RSS 适配器，行为不变）
        wechat_fetcher = create_wechat_fetcher()
        future_wechat = executor.submit(wechat_fetcher.list_articles)
        future_yuque = executor.submit(
            fetch_all_yuque_docs,
            YUQUE_TOKEN,
            YUQUE_GROUP,
            YUQUE_BOOK,
        )

        try:
            wechat_full_articles = future_wechat.result()
        except Exception as exc:  # pragma: no cover - 防御性日志
            print(f" [微信] 获取过程出现异常: {exc}")
            wechat_full_articles = []

        try:
            yuque_full_docs = future_yuque.result()
        except Exception as exc:  # pragma: no cover - 防御性日志
            print(f" [语雀] 获取过程出现异常: {exc}")
            yuque_full_docs = []

    raw_wechat_count = len(wechat_full_articles)
    wechat_full_articles, latest_wechat_timestamp = _filter_new_wechat_articles(
        wechat_full_articles,
        last_wechat_timestamp,
    )

    if latest_wechat_timestamp and (
        last_wechat_timestamp is None or latest_wechat_timestamp > last_wechat_timestamp
    ):
        _update_last_published_time(fetch_state, 'wechat', latest_wechat_timestamp)

    if last_wechat_timestamp:
        print(
            f" [微信] RSS 拉取 {raw_wechat_count} 篇，新增 {len(wechat_full_articles)} 篇，"
            f" 上次时间 {last_wechat_timestamp.isoformat()}。"
        )
    else:
        print(f" [微信] 初次运行，纳入 {len(wechat_full_articles)} 篇文章。")

    print(f" [语雀] 成功获取 {len(yuque_full_docs)} 篇文档。")

    # C. 数据汇集
    all_raw_data = wechat_full_articles + yuque_full_docs

    for item in all_raw_data:
        source = item.get('source')
        if isinstance(source, str):
            item['source'] = source.strip()

        author = item.get('author')
        if isinstance(author, str):
            item['author'] = author.strip()

        platform = item.get('platform')
        platform_label = None
        if isinstance(platform, str) and platform.strip():
            raw_platform = platform.strip()
            lowered = raw_platform.lower()
            if lowered in {'wechat', '微信公众号', 'weixin', 'wx', 'mp'}:
                platform_label = '微信公众号'
            elif lowered in {'yuque', '语雀'}:
                platform_label = '语雀'
            else:
                platform_label = raw_platform

        link = item.get('link') or item.get('url') or ''

        if not platform_label:
            source_lower = item.get('source', '').lower() if isinstance(item.get('source'), str) else ''
            if 'yuque' in source_lower or source_lower == '语雀':
                platform_label = '语雀'
            elif 'mp.weixin.qq.com' in link or 'wechat' in source_lower or '微信公众号' in source_lower:
                platform_label = '微信公众号'

        if platform_label:
            item['platform'] = platform_label

        if item.get('platform') == '微信公众号':
            mp_label = item.get('source') if isinstance(item.get('source'), str) else ''
            mp_label = mp_label.strip() if mp_label else ''
            author_text = item.get('author') if isinstance(item.get('author'), str) else ''
            author_text = author_text.strip()
            if mp_label:
                if author_text:
                    if mp_label not in author_text:
                        author_text = f"{author_text} · {mp_label}"
                else:
                    author_text = mp_label
            else:
                author_text = author_text or '作者未注明'
            item['author'] = author_text
        elif not item.get('author') and item.get('source'):
            item['author'] = item['source']

    print(f" [汇总] 原始数据总量: {len(all_raw_data)} 篇。")

    return all_raw_data


def run_full_pipeline():
    print("--- 启动信息聚合与 AI 智能处理管道 ---")

    # 1. 数据接出与汇集
    all_raw_data = run_data_aggregation()

    # 2. 本地数据去重 (SimHash)
    unique_data, filtered_out = filter_duplicates(all_raw_data)  # 使用 ai_processer 中的修正函数
    print(f" [总结] 原始数据 {len(all_raw_data)} 篇，SimHash 去重后保留 {len(unique_data)} 篇，过滤 {len(filtered_out)} 篇。")

    # 3. 复用历史结果并决定是否调用 AI
    existing_processed_data = load_existing_knowledge_base(FINAL_DATA_FILE)
    articles_for_ai, reused_articles = split_articles_for_processing(unique_data, existing_processed_data)

    print(
        f"\n--- LLM 处理准备: 需重新处理 {len(articles_for_ai)} 篇，复用 {len(reused_articles)} 篇历史摘要 ---"
    )

    processed_articles = []
    if articles_for_ai:
        print("--- 启动 LLM 深度处理 (注意：这会消耗您的 API 额度) ---")
        processed_articles = process_all_data_with_ai(articles_for_ai)
    else:
        print("--- 未检测到新增或更新的文章，跳过 LLM 调用 ---")

    final_processed_data = combine_processed_articles(unique_data, processed_articles, reused_articles)

    existing_key_map = {build_article_key(item): item for item in existing_processed_data}
    final_keys = {build_article_key(item) for item in final_processed_data}
    for key, article in existing_key_map.items():
        if key not in final_keys:
            final_processed_data.append(article)
            final_keys.add(key)

    # 4. 存储最终结果
    save_data(FINAL_DATA_FILE, final_processed_data)
    if filtered_out:
        save_data('filtered_articles.json', filtered_out)
    else:
        filtered_path = Path('filtered_articles.json')
        if filtered_path.exists():
            filtered_path.unlink()

    print("\n--- LLM 处理结果摘要 ---")
    if final_processed_data:
        first_item = final_processed_data[0]
        print(f"  成功处理 {len(final_processed_data)} 篇文章/文档。")
        print(f"  第一篇标题: {first_item.get('title', 'N/A')}")

        source_label = first_item.get('source', '未知来源')
        author_label = first_item.get('author') or '作者未注明'
        print(f"  第一篇来源: {source_label} · {author_label}")

        summary_text = (
            first_item.get('deep_summary')
            or first_item.get('llm_result', {}).get('deep_summary')
            or '未找到摘要信息'
        )
        print(f"  第一篇摘要: {summary_text[:120]}...")

        link = first_item.get('link') or first_item.get('url')
        if link:
            print(f"  原文链接: {link}")

    print("--- 管道处理完毕。所有知识已聚合、总结并扩展 ---")
    return final_processed_data



if __name__ == '__main__':
    run_full_pipeline()