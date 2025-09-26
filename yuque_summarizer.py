# yuque_summarizer.py (修正版)

from simhash import Simhash
from diff_utils import find_diff
# --- 修正 1: 导入正确的语雀获取函数 ---
from yuque_fetcher import fetch_yuque_data
import json
import os
import requests
from datetime import datetime, timedelta
from simhash_utils import generate_simhash, get_hamming_distance
# --- 修正 2: 导入统一配置中心的配置 ---
from config import YUQUE_TOKEN, YUQUE_GROUP, YUQUE_BOOK, YUQUE_BASE_URL, SIMHASH_THRESHOLD


# ----------------------------------------------------------------------
# 辅助函数：数据存储与加载
# ----------------------------------------------------------------------

def load_data(filename):
    """从文件中加载历史数据。"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError:
            print(f"警告，无法解析文件{filename}，将重新创建。")
            return {}
    else:
        return {}


def save_data(filename, data):
    """将数据保存到文件。"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"错误：无法将数据保存到文件{filename}:{e}")


# ----------------------------------------------------------------------
# 辅助函数：获取单个文档正文
# ----------------------------------------------------------------------

def get_doc_body(doc_id: str) -> str or None:
    """
    获取单个语雀文档的正文内容（Markdown格式）。
    内部使用 config.py 中的全局配置。
    """
    # 使用 config.py 中的配置
    url = f"{YUQUE_BASE_URL}/repos/{YUQUE_GROUP}/{YUQUE_BOOK}/docs/{doc_id}?raw=true"
    headers = {
        "X-Auth-Token": YUQUE_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        doc_data = response.json().get("data")

        if doc_data:
            return doc_data.get('body_markdown', doc_data.get('body'))
        return None

    except requests.exceptions.RequestException as e:
        print(f"ERROR: 获取文档 {doc_id} 正文失败: {e}")
        return None


# ----------------------------------------------------------------------
# 核心功能：语雀文档增量更新与差异检测
# ----------------------------------------------------------------------

def check_yuque_updates(data_file='yuque_history.json', simhash_threshold=SIMHASH_THRESHOLD):
    """
    检查语雀知识库的更新，过滤不显著的更改和同质化内容。

    返回:
    list: 包含有显著变化或新增文档的列表 (仅包含文档元数据)。
    """
    # 1. 获取本次运行的文档元数据
    yuque_metadata = fetch_yuque_data()

    if not yuque_metadata:
        print("无法获取语雀数据，请检查配置或网络连接。")
        return []

    # 2. 加载上次运行的历史数据
    last_run_data = load_data(data_file)
    new_run_data = {}  # 用于存储本次运行后的所有数据
    updated_docs_meta = []  # 存储需要返回给主流程进行 AI 处理的文档元数据

    for doc_meta in yuque_metadata:
        doc_id_str = str(doc_meta.get('id'))

        # 提取关键信息
        updated_at = doc_meta.get('updated_at')
        last_doc_info = last_run_data.get(doc_id_str)

        # --------------------------------------------
        # 步骤 A: 判断文档是否更新 (时间戳比对)
        # --------------------------------------------
        is_updated = False
        if not last_doc_info:
            # 新增文档
            is_updated = True
            print(f" [NEW] 新增文档: {doc_meta.get('title')}")
        elif updated_at > last_doc_info.get('updated_at', '1970-01-01T00:00:00Z'):
            # 已有文档，且时间戳发生变化
            is_updated = True
            print(f" [UPDATE] 文档已更新: {doc_meta.get('title')}")

        # --------------------------------------------
        # 步骤 B: 如果已更新，则进一步判断差异是否显著 (SimHash比对)
        # --------------------------------------------
        if is_updated:
            document_body = get_doc_body(doc_id_str)
            if not document_body:
                # 无法获取正文，跳过本次处理
                new_run_data[doc_id_str] = last_doc_info or doc_meta  # 至少保留元数据
                continue

            # 生成新文档的 SimHash
            new_simhash_obj = generate_simhash(document_body)
            new_doc_info = doc_meta.copy()

            # 检查差异是否显著
            is_significant = False

            if not last_doc_info:
                # 新文档：自动视为显著更新
                is_significant = True
            elif last_doc_info.get('simhash'):
                # 非首次：比对 SimHash 汉明距离
                old_simhash_value = last_doc_info['simhash']
                old_simhash_obj = Simhash(int(old_simhash_value))

                distance = get_hamming_distance(old_simhash_obj, new_simhash_obj)
                print(f"   - SimHash 距离: {distance} (阈值: {simhash_threshold})")

                if distance > simhash_threshold:
                    # 距离大于阈值，判定为显著更新
                    is_significant = True

                    # 额外输出差异内容（可选，仅作调试/通知用）
                    # old_doc_body = last_doc_info.get("body", "")
                    # diff_content = find_diff(old_doc_body, document_body)
                    # if diff_content:
                    #     print("   - 行级差异内容已检出...")

            if is_significant:
                # 显著更新：加入待处理列表
                updated_docs_meta.append(doc_meta)
                print("   -> 判定为显著更新/新增，将提交给 LLM 重新处理。")
            else:
                print("   -> SimHash 距离较近，判定为微小修改，过滤。")

            # 无论是否显著，都需要更新历史数据中的 'body' 和 'simhash'
            new_run_data[doc_id_str] = new_doc_info
            new_run_data[doc_id_str]["body"] = document_body
            new_run_data[doc_id_str]["simhash"] = new_simhash_obj.value

        else:
            # 3. 文档未更新：直接复制旧数据，确保指纹和正文不丢失
            new_run_data[doc_id_str] = last_doc_info.copy()

    # 4. 保存本次运行的数据
    save_data(data_file, new_run_data)
    print(f"\n--- 语雀增量检测完成：{len(updated_docs_meta)} 篇文档需重新处理。 ---")

    return updated_docs_meta


# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("--- 🔬 yuque_summarizer.py 增量检测模块自检 ---")

    # 运行增量检测函数
    significant_updates = check_yuque_updates()

    if significant_updates:
        print("\n以下文档有显著更新，需提交给 LLM：")
        for doc in significant_updates:
            print(f" - {doc.get('title')} (ID: {doc.get('id')})")
    else:
        print("\n本次运行未检测到显著更新或新增文档。")