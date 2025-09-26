# yuque_fetcher.py (最终稳定并发修正版)

import requests
import concurrent.futures  # 引入并发库
# 从统一配置中心导入所有配置
from config import YUQUE_TOKEN, YUQUE_GROUP, YUQUE_BOOK, YUQUE_BASE_URL


# ----------------------------------------------------------------------
# 1. 获取知识库的文档元数据列表 (fetch_yuque_data)
# ----------------------------------------------------------------------
# ... (此函数代码保持不变，因为它只被调用一次，无需并发优化)
def fetch_yuque_data(
        token: str = YUQUE_TOKEN,
        group_login: str = YUQUE_GROUP,
        book_slug: str = YUQUE_BOOK
) -> list:
    """
    获取指定知识库的所有文档元数据列表。
    """
    docs_url = f"{YUQUE_BASE_URL}/repos/{group_login}/{book_slug}/docs"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    print(f"尝试获取语雀知识库: {group_login}/{book_slug} 的元数据...")
    try:
        docs_response = requests.get(docs_url, headers=headers)
        docs_response.raise_for_status()
        docs_data = docs_response.json().get("data")

        return docs_data if docs_data is not None else []
    except requests.exceptions.RequestException as e:
        print(f"ERROR: 语雀元数据获取失败: {e}")
        return []


# ----------------------------------------------------------------------
# 2. 获取单个文档的全文内容 (fetch_doc_body: 并发执行的目标函数)
# ----------------------------------------------------------------------
def fetch_doc_body(
        doc_meta: dict,
        token: str,
        group_login: str,
        book_slug: str
) -> dict or None:
    """
    获取单个语雀文档的全文内容。为并发执行优化。
    """
    # 错误修正：确保 doc_meta 已经被定义，并从中提取 doc_id_or_slug
    # 如果 doc_meta 不存在（不太可能，但保险起见），则退出
    if not isinstance(doc_meta, dict):
        return None

    # **核心修正区域**：确保变量 doc_id_or_slug 被正确定义
    doc_id_or_slug = doc_meta.get('slug') or str(doc_meta.get('id'))
    if not doc_id_or_slug:
        return None

    # 强制获取 Markdown 格式的原文内容
    url = f"{YUQUE_BASE_URL}/repos/{group_login}/{book_slug}/docs/{doc_id_or_slug}?raw=true"

    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        doc_data = response.json().get("data")

        if doc_data is None:
            return None

        # 将语雀数据标准化
        return {
            'source': 'Yuque',
            'title': doc_data.get('title'),
            'slug': doc_data.get('slug'),
            'url': doc_data.get('url'),
            'published_at': doc_data.get('created_at'),
            # body_markdown 字段包含了 Markdown 格式的全文内容
            'content': doc_data.get('body_markdown', doc_data.get('body')),
            'content_format': 'Markdown'
        }
    except requests.exceptions.RequestException:
        # 捕获请求异常，并安静地返回 None，以便并发执行不中断
        return None


# ----------------------------------------------------------------------
# 3. 聚合所有文档的全文获取 (核心：使用并发提速)
# ----------------------------------------------------------------------
def fetch_all_yuque_docs(
        token: str = YUQUE_TOKEN,
        group_login: str = YUQUE_GROUP,
        book_slug: str = YUQUE_BOOK
) -> list:
    """
    使用线程池并发获取知识库中所有文档的全文内容，实现加速。
    """
    metadata_result = fetch_yuque_data(token, group_login, book_slug)

    if not metadata_result:
        return []

    print(f" [语雀] 准备并发获取 {len(metadata_result)} 篇文档全文...")

    MAX_WORKERS = 10
    full_docs = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        # 使用 executor.submit + as_completed 提交任务并收集结果
        # 为每个文档元数据提交一个 fetch_doc_body 任务，并传递所有必要的配置参数
        future_to_doc = {
            executor.submit(
                fetch_doc_body,
                doc_meta,
                token,
                group_login,
                book_slug
            ): doc_meta
            for doc_meta in metadata_result
        }

        # 收集结果
        for future in concurrent.futures.as_completed(future_to_doc):
            doc_content = future.result()
            if doc_content:
                full_docs.append(doc_content)

    print(f" [语雀] 成功并发获取 {len(full_docs)} 篇文档的全文内容。")
    return full_docs


# ----------------------------------------------------------------------
if __name__ == '__main__':
    print("--- 🔬 yuque_fetcher.py 性能优化自检 (并发模式) ---")
    all_docs = fetch_all_yuque_docs()

    if all_docs:
        print(f"\n总共获取到 {len(all_docs)} 篇文档。")
        print(f"验证: {all_docs[0]['title']} => {all_docs[0]['content'][:100]}...")
    else:
        print("文档获取失败，请检查配置。")