from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IWeChatFetcher(ABC):
    """微信公众号抓取接口契约。

    设计目标：
    - 保持与现有输出结构兼容（list[dict]，字段包含 title/link/published_time/content/source/author/platform 等）。
    - 后续可扩展为返回统一模型，但当前阶段不改变对下游的影响。
    """

    @abstractmethod
    def list_articles(self) -> List[Dict[str, Any]]:
        """列出可用于处理的文章列表（包含必要正文）。

        返回：
            - List[dict]: 与现有 `fetch_articles_from_rss()` 相同结构的字典列表。
        可能抛出：
            - 网络错误、解析错误等具体异常由实现抛出，上层自行处理。
        """

    # 预留：按需补充更细粒度方法（例如按 ID 取详情），当前阶段先不暴露。


__all__ = ["IWeChatFetcher"]
