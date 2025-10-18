from __future__ import annotations

from typing import Final

from .i_wechat_fetcher import IWeChatFetcher
from .wechat_we_mprss_adapter import WechatWeMPRSSAdapter

# 预留：可通过环境变量/配置切换实现，例如 "wmr"、"httpx"、"mock" 等
DEFAULT_IMPL: Final[str] = "wmr"


def create_wechat_fetcher(impl: str | None = None) -> IWeChatFetcher:
    """创建 WeChat 抓取器实例。

    当前阶段：无条件返回 WechatWeMPRSSAdapter，保持现状；
    后续将读取 config.WECHAT_FETCHER_IMPL 做切换。
    """

    if impl is None:
        try:
            # 延迟导入，避免循环依赖
            from config import WECHAT_FETCHER_IMPL as _impl_from_cfg  # type: ignore
        except Exception:
            _impl_from_cfg = None
        _impl = (_impl_from_cfg or DEFAULT_IMPL).lower()
    else:
        _impl = impl.lower()
    match _impl:
        case "wmr" | "we-mp-rss" | "default":
            return WechatWeMPRSSAdapter()
        case _:
            # 未知实现，回退默认
            return WechatWeMPRSSAdapter()


__all__ = ["create_wechat_fetcher"]
