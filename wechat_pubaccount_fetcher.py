import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
# --- 修正: 引入配置 ---
from config import WECHAT_RSS_URL

# --- 新的配置区域 ---
# 移除硬编码的 RSS_URL
# --------------------

def fetch_articles_from_rss() -> list:
    """
    通过访问 RSS Feed 一次性获取所有文章的元数据和全文内容。
    """
    all_articles_data = []

    # 使用统一的配置变量
    print(f"尝试从 RSS Feed 获取所有文章: {WECHAT_RSS_URL}")
    try:
        # RSS Feed 通常无需 Headers 认证，直接请求
        response = requests.get(WECHAT_RSS_URL, timeout=30)
        response.raise_for_status()

        # 1. 解析 XML 结构
        # ET.fromstring 接收 bytes 或 string，requests.content 是 bytes
        root = ET.fromstring(response.content)

        # RSS 结构：<rss> -> <channel> -> <item>
        channel = root.find('channel')
        if channel is None:
            print("警告: XML 结构异常，未找到 <channel> 标签。")
            return []

        # 2. 遍历所有 <item> 标签（即每一篇文章）
        for item in channel.findall('item'):
            title_element = item.find('title')
            link_element = item.find('link')
            pubdate_element = item.find('pubDate')
            content_element = item.find('description') # we-mp-rss将全文放在 description 中

            # 确保元素存在并提取内容
            title = title_element.text if title_element is not None else 'No Title'
            link = link_element.text if link_element is not None else 'No Link'
            content = content_element.text if content_element is not None else 'No Content'

            # 格式化日期，以防后续处理需要标准格式
            pub_date = pubdate_element.text if pubdate_element is not None else datetime.now().isoformat()

            # 3. 封装为与原脚本一致的数据结构 (方便后续 LLM 处理)
            all_articles_data.append({
                'title': title,
                'link': link,
                'published_time': pub_date,
                'content': content,
                'content_format': 'Markdown'
            })

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
        sample_article = full_articles[0]
        sample_article['content'] = sample_article['content'][:300] + '...'
        print(json.dumps(sample_article, indent=4, ensure_ascii=False))

        # TODO: 3. 将 full_articles 传入 LLM 进行分析和知识提取
        # LLM_analysis_function(full_articles)
        # ...

    else:
        print("\n警告：未能获取任何文章数据。请检查 we-mp-rss 服务是否正在运行。")