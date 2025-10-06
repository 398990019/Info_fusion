# config.py
import os
from typing import Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def _env_flag(name: str, default: str = 'false') -> bool:
    """将环境变量解析为布尔值，支持多种常见写法。"""

    value = os.getenv(name, default)
    if value is None:
        return False
    value = value.split('#', 1)[0].strip().lower()
    if not value:
        return False
    return value in {'1', 'true', 'yes', 'on'}


def _env_int(name: str, default: int) -> int:
    """解析整数环境变量，无法解析时返回默认值。"""

    value = os.getenv(name)
    if value is None:
        return default
    try:
        cleaned = value.split('#', 1)[0].strip()
        return int(cleaned)
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: Optional[str] = None, *, strip: bool = True) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    cleaned = value.split('#', 1)[0]
    if strip:
        cleaned = cleaned.strip()
    if not cleaned:
        return default
    return cleaned

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
WECHAT_RSS_URL = _env_str('WECHAT_RSS_URL', "http://localhost:8001/feed/all.rss")

# 是否在抓取前主动触发 We-MP-RSS 刷新
WECHAT_FORCE_REFRESH = _env_flag('WECHAT_FORCE_REFRESH', 'true')

# 可选：显式指定 We-MP-RSS 项目目录（未设置时自动探测）
WECHAT_RSS_ROOT = os.getenv('WECHAT_RSS_ROOT')

# --- We-MP-RSS Authenticated API ---
WECHAT_API_BASE_URL = _env_str('WECHAT_API_BASE_URL', 'http://localhost:8001')
WECHAT_API_USERNAME = _env_str('WECHAT_API_USERNAME')
WECHAT_API_PASSWORD = _env_str('WECHAT_API_PASSWORD')
WECHAT_API_VERIFY_SSL = _env_flag('WECHAT_API_VERIFY_SSL', 'false')
WECHAT_API_PAGE_SIZE = _env_int('WECHAT_API_PAGE_SIZE', 100)
WECHAT_API_MAX_PAGES = _env_int('WECHAT_API_MAX_PAGES', 0)
WECHAT_API_INCLUDE_CONTENT_FOR_NEW = _env_flag('WECHAT_API_INCLUDE_CONTENT_FOR_NEW', 'true')

# --- De-duplication/SimHash Configuration ---
# SimHash 汉明距离阈值：用于判断两篇文章是否重复
# 阈值 4 意味着 128 位签名中最多有 4 位不同，被认为是相似文章。
SIMHASH_THRESHOLD = 15