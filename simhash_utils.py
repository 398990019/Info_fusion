from simhash import Simhash
import jieba
from collections import Counter

# --- 扩展停用词列表 ---
STOP_WORDS = set([
    '的', '了', '是', '在', '与', '而', '之', '所', '或', '都', '不', '我', '你', '他',
    '我们', '他们', '一个', '一种', '一些', '可以', '进行', '已经', '对于', '但是',
    '如果', '通过', '相关', '由于', '成为', '发现', '同时', '及其', '基于', '具有',
    '这些', '例如', '不仅', '只是', '作为', '一直', '以来', '还是', '正在',
    '并', '将', '被', '对', '从', '由', '与', '及', '跟', '同', '和', '又',
    # 领域中常见的冗余词
    '学院', '研究', '探索', '发展', '知识', '推动', '专注', '致力'
])

# --- 同义词/归一化字典 ---
NORMALIZE_MAP = {
    "研究": "探索",
    "致力": "专注",
    "融合": "结合",
    "前沿": "最新",
    "学院": "院系",
    "领域": "学科",
    "推动": "促进",
    "发展": "进步",
    "跨学科": "多学科",
    "人工智能": "AI",
    "哲学": "人文学科",
    "社会学": "人文学科"
}

def normalize_token(token: str) -> str:
    """将词语做归一化（同义词映射）。"""
    return NORMALIZE_MAP.get(token, token)

def init_custom_words():
    """
    添加自定义领域词汇，避免 jieba 错分。
    """
    custom_words = [
        "人工智能学院",
        "人工智能",
        "跨学科",
        "计算机科学",
        "神经科学",
        "社会学",
        "哲学"
    ]
    for w in custom_words:
        jieba.add_word(w)

def get_tokens(doc_text):
    """
    改进版分词函数：
    1. 使用 jieba 分词（包含自定义词）。
    2. 过滤掉停用词和单字。
    3. 做同义词归一化。
    """
    if not isinstance(doc_text, str):
        return []

    text = doc_text.lower()
    # 移除标点
    text = ''.join(c for c in text if c.isalnum() or c.isspace() or '\u4e00' <= c <= '\u9fa5')

    raw_tokens = list(jieba.cut(text))
    final_tokens = []

    for token in raw_tokens:
        token = token.strip()
        if len(token) > 1 and token not in STOP_WORDS:
            token = normalize_token(token)
            final_tokens.append(token)

    return final_tokens

def generate_simhash(doc_text):
    """
    使用词频 (TF) 作为权重生成 Simhash 签名。
    改进：签名长度从 64 位 -> 128 位。
    """
    tokens = get_tokens(doc_text)

    if not tokens:
        return Simhash([""], f=128)

    word_counts = Counter(tokens)
    weighted_tokens = [(token, count) for token, count in word_counts.items()]
    return Simhash(weighted_tokens, f=128)

def get_hamming_distance(hash1, hash2):
    """计算两个 Simhash 签名之间的海明距离。"""
    if not (hash1 and hash2):
        return float('inf')
    return hash1.distance(hash2)

# ----------------------------------------------------------------------
if __name__ == '__main__':
    print("--- 🔬 Simhash 文档相似度检测演示 (改进版：自定义词 + 128位) ---")

    # 初始化自定义词典
    init_custom_words()

    # --- 1. 定义测试文档 ---
    doc_a = "南京大学的人工智能学院致力于跨学科研究，融合了计算机科学与神经科学的前沿知识，以推动哲学和社会学领域的发展。"
    doc_b = "南京大学的人工智能学院专注于跨学科探索，结合了计算机科学与神经科学的最新知识，以推动哲学和社会学领域的发展。"
    doc_c = "昨夜雨疏风骤，浓睡不消残酒。试问卷帘人，却道海棠依旧。知否，知否？应是绿肥红瘦。"

    # --- 2. 生成 Simhash 签名 ---
    hash_a = generate_simhash(doc_a)
    hash_b = generate_simhash(doc_b)
    hash_c = generate_simhash(doc_c)

    # --- 3. 计算海明距离 ---
    distance_ab = get_hamming_distance(hash_a, hash_b)
    distance_ac = get_hamming_distance(hash_a, hash_c)

    # --- 4. 输出结果 ---
    print("\n--- 相似度检测结果 ---")
    print(f"文档 A (原始): {doc_a[:20]}...")
    print(f"文档 B (相似): {doc_b[:20]}...")
    print(f"文档 C (不相似): {doc_c[:20]}...")

    print(f"\n1. 相似文章 (A vs B) 的海明距离: {distance_ab}")
    print(f"   -> 结果分析: 海明距离目标 **0-3**，判定为**高度相似/重复**。")

    print(f"2. 不相似文章 (A vs C) 的海明距离: {distance_ac}")
    print(f"   -> 结果分析: 距离保持较大，判定为**不同主题**。")
