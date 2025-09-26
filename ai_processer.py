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
def filter_duplicates(articles: list, threshold: int = SIMHASH_THRESHOLD) -> list:
    # ... (此函数内容保持不变，确保其中 Simhash(int(...), f=SIMHASH_F_BITS) 的修正已在)
    stored_simhashes = []
    unique_articles = []

    for item in articles:
        content = item.get('content', '')
        if not content:
            continue

        try:
            item_simhash = generate_simhash(content)
        except Exception as e:
            # ...
            continue

        is_duplicate = False
        for existing_simhash_value in stored_simhashes:
            # 确保 SimHash 位宽一致
            existing_simhash = Simhash(int(existing_simhash_value), f=SIMHASH_F_BITS)

            distance = item_simhash.distance(existing_simhash)

            if distance <= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_articles.append(item)
            stored_simhashes.append(item_simhash.value)

    return unique_articles


# ----------------------------------------------------------------------
# LLM 核心处理逻辑 (process_with_llm 保持不变)
# ----------------------------------------------------------------------
def process_with_llm(article: dict) -> dict:
    """
    调用 Qwen API 对单篇文章进行深度总结和跨学科洞察。
    """

    # 构造 LLM 提示 (Prompt)
    title = article.get('title', '无标题')
    content = article.get('content', '')

    system_prompt = f"""你是一位跨学科分析专家，尤其擅长计算机科学、人工智能、哲学、社会学、文学和神经科学。你的任务是阅读给定的文章，并以一个南京大学大一学生的知识水平，提供一个结构化的、深度思考后的分析报告。

    请严格按照以下 JSON 格式输出，不要输出任何其他内容。

    [JSON 格式要求]
    {{
        "deep_summary": "请用中文提炼文章的**核心观点和主要论据**，字数不少于200字，要求条理清晰，可读性强。",
        "cross_disciplinary_insights": [
            {{
                "field": "请选择一个最相关的跨学科领域（如：神经科学/哲学/社会学/文学）",
                "insight": "请从该领域的角度出发，提出一个**独特的、发散性的洞察或反思**，并阐述该洞察如何加深对文章主题的理解。",
                "connection": "请简述此洞察如何与文章的**核心技术或观点**进行交叉映射。"
            }}
        ],
        "key_terms": ["专业名词1", "专业名词2", "专业名词3"]
    }}"""

    user_prompt = f"文章标题: {title}\n文章内容:\n{content[:5000]}..."  # 限制内容长度，避免API超限

    try:
        completion = client.chat.completions.create(
            model=AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        # 解析 JSON 响应
        llm_output_json = json.loads(completion.choices[0].message.content)

        # 将 LLM 结果合并到原始文章字典中
        article['deep_summary'] = llm_output_json.get('deep_summary')
        article['cross_disciplinary_insights'] = llm_output_json.get('cross_disciplinary_insights')
        article['key_terms'] = llm_output_json.get('key_terms')
        article['processed_at'] = datetime.now().isoformat()

        print(f" [AI] 成功处理文章: {title}")
        return article

    except Exception as e:
        print(f" [AI] ERROR: 处理文章 '{title}' 失败: {e}")
        # 失败的文章也返回，但没有处理结果
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


def process_with_llm(article_data: dict) -> dict:
    """
    调用通义千问 API 进行总结和跨学科扩展。
    """
    article_title = article_data.get('title')
    article_content = article_data.get('content', '')

    # 提示词融入你的知识输出型要求和兴趣领域
    prompt = f"""
    你是一名南京大学大一学生，对计算机科学、人工智能、哲学、社会学、文学、语言学和神经科学等领域有浓厚兴趣。

    你的任务是分析以下文章内容，并以一种**知识输出型**的方式回答。请用 Markdown 格式输出分析内容。

    **文章标题:** {article_title}
    **文章内容:** ---
    {article_content[:8000]} # 截断内容，避免超长
    ---

    请严格按照以下 **JSON 结构**返回结果，不要包含任何额外的文字解释、注释或Markdown块。

    {{
        "deep_summary": "用200字左右提炼文章的核心思想、关键论点和结论。",
        "cross_disciplinary_insights": [
            {{
                "domain": "请从计算机科学、哲学、社会学等兴趣领域中选择一个与文章内容最相关的领域",
                "analysis": "从该学科角度对文章内容进行深入解读、联想或启发。",
                "connection": "请指出文章内容与该学科的某个具体概念（如：控制论、符号学、社会场的理论）的联系。"
            }},
            {{
                "domain": "请选择另一个跨学科领域",
                "analysis": "从该学科角度对文章内容进行解读、联想或启发。",
                "connection": "请指出文章内容与该学科的某个具体概念（如：海德格尔的此在、生成语法、图灵测试）的联系。"
            }}
        ],
        "open_question": "提出一个具有深度和启发性的开放式思考题，鼓励进一步研究。"
    }}
    """

    print(f" [LLM] 正在处理: {article_title}...")

    try:
        completion = client.chat.completions.create(
            model=AI_MODEL_NAME,
            messages=[
                {"role": "system",
                 "content": "你是一位拥有多学科背景的、逻辑严谨的分析师，请严格以用户要求的 JSON 格式返回分析结果。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            response_format={"type": "json_object"}
        )

        # 解析返回的 JSON 字符串
        llm_output_json = json.loads(completion.choices[0].message.content)

        # 将 LLM 结构化结果添加到数据中
        article_data['llm_result'] = llm_output_json
        article_data['processed_at'] = datetime.now().isoformat()
        article_data['llm_model'] = AI_MODEL_NAME

        print(f" [LLM] 处理成功: {article_title}")
        return article_data

    except Exception as e:
        print(f" ERROR: LLM API 调用或 JSON 解析失败 ({article_title}): {e}")
        # 如果失败，至少返回原始数据，并标记为失败
        article_data['llm_status'] = 'FAILED'
        return article_data



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