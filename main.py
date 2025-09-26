# main.py

from wechat_pubaccount_fetcher import fetch_articles_from_rss
from yuque_fetcher import fetch_all_yuque_docs
from ai_processer import process_all_data_with_ai, filter_duplicates
from logger import setup_logger
import json
# --- 修正 3: 引入配置 ---
from config import YUQUE_TOKEN, YUQUE_GROUP, YUQUE_BOOK
from yuque_summarizer import save_data


# 移除硬编码的语雀配置

def run_data_aggregation():
    print("--- 启动信息聚合任务 ---")

    # A. 微信内容接出 (简化为一步，使用 RSS 模式)
    wechat_full_articles = fetch_articles_from_rss()
    print(f" [微信] 成功获取 {len(wechat_full_articles)} 篇 RSS 文章。")

    # B. 语雀内容接出
    # 使用 config 中的变量作为默认参数或直接传入
    yuque_full_docs = fetch_all_yuque_docs(YUQUE_TOKEN, YUQUE_GROUP, YUQUE_BOOK)
    print(f" [语雀] 成功获取 {len(yuque_full_docs)} 篇文档。")

    # C. 数据汇集
    all_raw_data = wechat_full_articles + yuque_full_docs
    print(f" [汇总] 原始数据总量: {len(all_raw_data)} 篇。")

    return all_raw_data


def run_full_pipeline():
    print("--- 启动信息聚合与 AI 智能处理管道 ---")

    # 1. 数据接出与汇集
    all_raw_data = run_data_aggregation()

    # 2. 本地数据去重 (SimHash)
    unique_data = filter_duplicates(all_raw_data)  # 使用 ai_processer 中的修正函数
    print(f" [总结] 原始数据 {len(all_raw_data)} 篇，SimHash 去重后保留 {len(unique_data)} 篇。")

    # 3. AI 智能处理 (通义千问 Qwen)
    print("\n--- 启动 LLM 深度处理 (注意：这会消耗您的 API 额度) ---")
    final_processed_data = process_all_data_with_ai(unique_data)

    # 4. 存储最终结果
    save_data('final_knowledge_base.json', final_processed_data)

    print("\n--- LLM 处理结果摘要 ---")
    if final_processed_data:
        print(f"  成功处理 {len(final_processed_data)} 篇文章/文档。")
        print(f"  第一篇标题: {final_processed_data[0].get('title', 'N/A')}")
        # 假设 AI 处理后的数据包含一个 'deep_summary' 字段
        summary_text = final_processed_data[0].get('deep_summary', '未找到摘要信息')
        print(f"  第一篇摘要: {summary_text[:100]}...")

    print("--- 管道处理完毕。所有知识已聚合、总结并扩展 ---")
    return final_processed_data

    print("--- 管道处理完毕。所有知识已聚合、总结并扩展 ---")
    return final_processed_data


if __name__ == '__main__':
    run_full_pipeline()