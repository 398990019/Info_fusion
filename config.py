# config.py
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# --- AI Configuration (Qwen) ---
AI_API_KEY = os.getenv('AI_API_KEY')  # 从环境变量获取
AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
AI_MODEL_NAME = os.getenv('AI_MODEL_NAME', 'qwen3-max')

# --- Yuque Configuration ---
YUQUE_TOKEN = os.getenv('YUQUE_TOKEN')  # 从环境变量获取
YUQUE_GROUP = os.getenv('YUQUE_GROUP', 'ph25ri')
YUQUE_BOOK = os.getenv('YUQUE_BOOK', 'ua1c3q')
# 语雀 API Base URL
YUQUE_BASE_URL = "https://www.yuque.com/api/v2"

# --- WeChat Configuration ---
# 微信 RSS Feed URL (假设你的服务运行在 localhost:8001)
WECHAT_RSS_URL = "http://localhost:8001/feed/all.rss"

# --- De-duplication/SimHash Configuration ---
# SimHash 汉明距离阈值：用于判断两篇文章是否重复
# 阈值 4 意味着 128 位签名中最多有 4 位不同，被认为是相似文章。
SIMHASH_THRESHOLD = 15