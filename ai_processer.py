# ai_processer.py (LLM 并发优化修正版)

import json
from datetime import datetime
from openai import OpenAI
from simhash import Simhash
import re
from simhash_utils import generate_simhash
import concurrent.futures  # 引入并发库
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL_NAME, SIMHASH_THRESHOLD

# 假设 SimHash 位宽为 128 (与 simhash_utils.py 保持一致)
SIMHASH_F_BITS = 128
MAX_LLM_WORKERS = 5  # LLM 并发线程数：不宜设置过高，以避免API限速

# ----------------------------------------------------------------------
# 阿里云 Dashscope 通义千问 配置 (Qwen)
# ----------------------------------------------------------------------
client = OpenAI(
    api_key=AI_API_KEY,
    base_url=AI_BASE_URL,
)


# ----------------------------------------------------------------------
# 辅助函数：SimHash 去重 (已包含 SimHash 位宽修正)
# ----------------------------------------------------------------------
def filter_duplicates(articles: list, threshold: int = SIMHASH_THRESHOLD) -> tuple[list, list]:
    stored_entries: list[dict] = []
    unique_articles: list[dict] = []
    filtered_articles: list[dict] = []

    for item in articles:
        content = item.get('content', '')
        if not content:
            filtered_item = item.copy()
            filtered_item['_filtered_reason'] = 'empty_content'
            filtered_articles.append(filtered_item)
            continue

        try:
            item_simhash = generate_simhash(content)
        except Exception as e:
            filtered_item = item.copy()
            filtered_item['_filtered_reason'] = f'simhash_error: {e}'
            filtered_articles.append(filtered_item)
            continue

        duplicate_of = None
        for entry in stored_entries:
            existing_simhash = Simhash(int(entry['value']), f=SIMHASH_F_BITS)
            distance = item_simhash.distance(existing_simhash)

            if distance <= threshold:
                duplicate_of = entry['article']
                break

        if duplicate_of is None:
            unique_articles.append(item)
            stored_entries.append({'value': item_simhash.value, 'article': item})
        else:
            filtered_item = item.copy()
            filtered_item['_filtered_reason'] = 'duplicate'
            filtered_item['_duplicate_of_title'] = duplicate_of.get('title')
            filtered_item['_duplicate_of_source'] = duplicate_of.get('source')
            filtered_articles.append(filtered_item)

    return unique_articles, filtered_articles


# ----------------------------------------------------------------------
# LLM 核心处理逻辑
# ----------------------------------------------------------------------
def process_with_llm(article: dict) -> dict:
    """调用 Qwen API 为单篇文章生成结构化摘要。"""

    title = article.get('title', '无标题')
    content = article.get('content', '')

    system_prompt = (
        "你是一位善于提炼要点的中文写作教练。"
        "请阅读给定文章，并输出清晰、可靠、方便引用的结果。"
        "严格按照指定 JSON 结构返回，不要包含额外说明。"
    )

    user_prompt = f"""
文章标题：{title}
文章内容（已截断）：
{content[:8000]}

请返回 JSON，字段要求：
- deep_summary：不少于180字的中文摘要，聚焦关键论点与结论。
- key_points：长度为3的字符串数组，每项20字以内，概述核心要点。
- open_question：一个引导深入思考的开放性问题。
"""

    try:
        completion = client.chat.completions.create(
            model=AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        llm_output_json = json.loads(completion.choices[0].message.content)

        llm_result = {
            'deep_summary': llm_output_json.get('deep_summary', '').strip(),
            'key_points': llm_output_json.get('key_points', []),
            'open_question': llm_output_json.get('open_question', '').strip()
        }

        link = article.get('link') or article.get('url')
        summary_with_link = llm_result['deep_summary']
        if link and llm_result['deep_summary']:
            summary_with_link = f"{llm_result['deep_summary'].rstrip()}\n\n原文链接：{link}"

        llm_result['deep_summary_with_link'] = summary_with_link

        article['llm_result'] = llm_result
        article['deep_summary'] = llm_result['deep_summary']
        article['deep_summary_with_link'] = summary_with_link
        article['key_points'] = llm_result['key_points']
        article['open_question'] = llm_result['open_question']
        article['processed_at'] = datetime.now().isoformat()

        print(f" [AI] 成功处理文章: {title}")
        return article

    except Exception as e:
        print(f" [AI] ERROR: 处理文章 '{title}' 失败: {e}")
        article.setdefault('llm_result', {})
        article['llm_result']['error'] = str(e)
        article['llm_result'].setdefault('deep_summary', '')
        return article


# ----------------------------------------------------------------------
# 核心修正：主处理流程引入并发
# ----------------------------------------------------------------------
def process_all_data_with_ai(unique_articles: list) -> list:
    """
    使用线程池并发调用 LLM API，处理去重后的所有文章。
    """
    processed_list = []

    print(f" [AI] 启动并发处理 {len(unique_articles)} 篇文章...")

    # 创建线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:

        # 提交所有任务给线程池
        # executor.map 适用于将一个函数应用于列表中的所有元素
        futures = {
            executor.submit(process_with_llm, item): item
            for item in unique_articles
        }

        # 迭代已完成的任务，并打印进度
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            article_item = futures[future]

            try:
                # 获取任务结果
                result = future.result()
                processed_list.append(result)

                # 打印实时进度
                print(f" [进度] 已完成 {i + 1}/{len(unique_articles)} 篇文章。")

            except Exception as e:
                # 如果单个任务失败，捕获异常，主流程继续
                print(f" [严重] 任务失败，跳过文章 '{article_item.get('title')}'。错误: {e}")
                processed_list.append(article_item)  # 即使失败，也保留原始数据

    return processed_list


#
# (process_article_with_ai 和 process_all_data_with_ai 保持不变)

# ----------------------------------------------------------------------
# 辅助函数：SimHash 去重
# ----------------------------------------------------------------------

def get_text_features(s):
    """
    Simhash 辅助函数：将文本分词并处理为特征列表。
    这里使用简单的正则分词，你可以根据需要使用更专业的中文分词库如 jieba。
    """
    width = 3
    s = s.lower()
    s = re.sub(r'[^\w]+', '', s)  # 去除非字母数字字符

    # 使用滑动窗口生成 n-gram 特征
    return [s[i:i + width] for i in range(max(len(s) - width + 1, 1))]



# ----------------------------------------------------------------------
# 测试代码示例
# ----------------------------------------------------------------------

if __name__ == '__main__':
    print("--- 运行 ai_processor.py 测试 ---")

    # 构造两条相似但有差异的文章（测试 Simhash）
    test_data = [
        {
            'source': 'WeChat',
            'title': 'AI与哲学：机器意识的伦理困境',
            'url': 'http://test.com/a1',
            'content': '本文深入探讨了人工智能在伦理学中的位置，特别是关于机器是否可能拥有真正的意识，以及这对人类社会将带来的冲击。意识的定义一直是哲学的核心问题之一。'
        },
        {
            'source': 'Yuque',
            'title': '机器意识：图灵测试之后的哲学反思',
            'url': 'http://test.com/b2',
            'content': '文章分析了当代人工智能发展趋势，并反思了意识这一哲学核心问题。讨论了图灵测试在机器是否拥有真正的意识这一命题上的局限性，对人类伦理和社会产生了巨大冲击。'
        },
        {
            'source': 'Blog',
            'title': '完全不相关的第三篇文章',
            'url': 'http://test.com/c3',
            'content': '这是一篇关于南京大学最新招生政策的通知，介绍了大一新生导师制和新生学院的特色培养方案。'
        }
    ]

    # 1. Simhash 去重测试
    unique_articles = filter_duplicates(test_data, threshold=4)

    # 2. AI 深度处理测试 (只会处理去重后的文章)
    if unique_articles:
        print("\n--- 启动 LLM 处理测试 (注意：这会消耗您的 API 额度) ---")
        final_knowledge_base = process_all_data_with_ai(unique_articles)

        print("\n--- 最终处理结果 ---")
        for item in final_knowledge_base:
            print(f"标题: {item['title']}")
            print(f"来源: {item['source']}")
            if 'llm_result' in item:
                print(f" - 摘要: {item['llm_result']['deep_summary'][:50]}...")
            else:
                print(" - LLM 处理失败。")
            print("---------------------------------")
    else:
        print("\n没有通过去重测试的唯一文章，LLM处理跳过。")