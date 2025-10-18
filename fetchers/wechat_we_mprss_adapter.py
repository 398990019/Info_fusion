from __future__ import annotations

from typing import Any, Dict, List

from .i_wechat_fetcher import IWeChatFetcher


class WechatWeMPRSSAdapter(IWeChatFetcher):
    """基于 We-MP-RSS（RSS + 可鉴权 API）的默认实现。

    兼容当前项目的行为：内部直接复用 `wechat_pubaccount_fetcher.fetch_articles_from_rss()`，
    以最小改动接入接口抽象。
    """

    def list_articles(self) -> List[Dict[str, Any]]:
        from wechat_pubaccount_fetcher import fetch_articles_from_rss

        return fetch_articles_from_rss()


__all__ = ["WechatWeMPRSSAdapter"]
