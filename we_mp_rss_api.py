"""Authenticated client for interacting with the We-MP-RSS HTTP API.

The CLI/service that powers :func:`wechat_pubaccount_fetcher.fetch_articles_from_rss`
exposes a richer HTTP API which requires an access token.  This module wraps the
authentication workflow and common endpoints with a small pythonic facade so the
rest of the project can focus on business logic and leave retries / pagination to
this layer.

Design goals
------------

* Cache tokens until expiry to avoid unnecessary login spam that may trigger
  account lockouts (the upstream service locks after five failed attempts).
* Provide typed-ish structures (TypedDict) so IDEs/static checkers provide
  better hints, yet keep runtime dependencies minimal.
* Expose clear functions for high-level orchestration code: ``login``,
  ``list_articles`` and ``fetch_article_content`` (the latter is optional but
  handy when only metadata is present in the listing endpoint).

This module keeps no global mutable state besides an in-memory token cache per
``Session`` instance.  Callers may instantiate one ``WeMPRSSClient`` per task
run and reuse it for multiple requests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, TypedDict

import requests

from config import (
    WECHAT_API_BASE_URL,
    WECHAT_API_PASSWORD,
    WECHAT_API_USERNAME,
    WECHAT_API_VERIFY_SSL,
)


class AuthError(RuntimeError):
    """Raised when authentication fails or expires."""


class APIError(RuntimeError):
    """Raised when the remote API returns a non-zero `code`."""


class ArticleListItem(TypedDict, total=False):
    id: int
    title: str
    link: str
    cover: str
    publish_time: str
    digest: str
    mp_name: str
    account: str
    author: str
    biz: str
    appmsgid: str
    idx: int
    source_url: str


class ArticleDetail(TypedDict, total=False):
    id: int
    title: str
    content: str
    content_format: str
    publish_time: str
    account: str
    mp_name: str
    mp_nickname: str
    author: str
    link: str
    digest: str


@dataclass
class TokenBucket:
    """Small helper to keep track of bearer tokens and their expiry."""

    access_token: str
    expires_at: float

    def is_valid(self, skew_seconds: float = 10.0) -> bool:
        return time.time() + skew_seconds < self.expires_at


class WeMPRSSClient:
    """Helper class wrapping requests to the authenticated We-MP-RSS API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ) -> None:
        self._base_url = (base_url or WECHAT_API_BASE_URL).rstrip("/")
        self._username = username or WECHAT_API_USERNAME
        self._password = password or WECHAT_API_PASSWORD
        if self._username is None or self._password is None:
            raise AuthError("未配置 WECHAT_API_USERNAME/WECHAT_API_PASSWORD 环境变量")

        self._verify_ssl = WECHAT_API_VERIFY_SSL if verify_ssl is None else verify_ssl
        self._token_bucket: Optional[TokenBucket] = None
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers

    def _build_url(self, segment: str) -> str:
        if not segment.startswith("/"):
            segment = "/" + segment
        return f"{self._base_url}{segment}"

    def _ensure_token(self) -> str:
        if self._token_bucket and self._token_bucket.is_valid():
            return self._token_bucket.access_token

        self._token_bucket = self._perform_login()
        return self._token_bucket.access_token

    def _perform_login(self) -> TokenBucket:
        token_endpoint = self._build_url("/api/v1/wx/auth/token")
        form = {
            "username": self._username,
            "password": self._password,
        }

        response = self._session.post(
            token_endpoint,
            data=form,
            timeout=15,
            verify=self._verify_ssl,
        )
        if response.status_code == 401:
            raise AuthError("帐号被锁 / 凭据无效: 401")

        if response.status_code >= 400:
            raise AuthError(f"无法登录 We-MP-RSS (status={response.status_code})")

        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - 上游返回 HTML/纯文本
            raise AuthError("登录响应不是 JSON 格式") from exc

        if not isinstance(payload, dict):
            raise AuthError(f"登录响应格式异常: {payload}")

        # We-MP-RSS 旧版返回 {code: 0, data: {...}}，新版返回 OAuth 风格
        if payload.get("code") not in (None, 0):
            msg = (
                payload.get("message")
                or payload.get("msg")
                or payload.get("detail")
                or payload.get("error")
                or str(payload.get("code"))
            )
            raise AuthError(f"登录失败: {msg} · 响应: {payload}")

        token: Optional[str] = None
        expires_in: Optional[float] = None

        if "data" in payload and isinstance(payload["data"], dict):
            data = payload["data"]
            token = data.get("access_token")
            expires_in = data.get("expires_in")
        else:
            token = payload.get("access_token")
            expires_in = payload.get("expires_in")

        if isinstance(expires_in, str):
            try:
                expires_in = float(expires_in)
            except ValueError:
                expires_in = None

        if not token or not isinstance(expires_in, (int, float)):
            detail = payload.get("detail")
            if isinstance(detail, dict):
                message = detail.get("message") or detail.get("error")
                raise AuthError(f"登录失败: {message} · 响应: {payload}")
            raise AuthError("登录响应缺少 access_token 或 expires_in 字段")

        expires_at = time.time() + float(expires_in)
        return TokenBucket(access_token=token, expires_at=expires_at)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> dict:
        token = self._ensure_token()
        response = self._session.request(
            method,
            self._build_url(path),
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            verify=self._verify_ssl,
        )

        if response.status_code == 401:
            # 尝试一次刷新 token
            self._token_bucket = None
            token = self._ensure_token()
            response = self._session.request(
                method,
                self._build_url(path),
                params=params,
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
                verify=self._verify_ssl,
            )

        if response.status_code >= 400:
            raise APIError(f"We-MP-RSS API 请求失败 ({response.status_code})")

        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover
            raise APIError("We-MP-RSS API 响应不是 JSON") from exc

        if not isinstance(payload, dict):
            return payload

        # 新旧两套 API 的兼容处理
        if payload.get("code") not in (None, 0):
            detail = payload.get("detail")
            message = (
                payload.get("message")
                or payload.get("msg")
                or (detail.get("message") if isinstance(detail, dict) else None)
                or payload.get("error")
                or str(payload.get("code"))
            )
            raise APIError(message or "未知错误")

        if "data" in payload and isinstance(payload["data"], dict):
            return payload["data"]

        return payload

    # ------------------------------------------------------------------
    # Public methods

    def list_articles(
        self,
        *,
        mp_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        params = {
            "page": page,
            "pageSize": page_size,
        }
        if mp_name:
            params["mpName"] = mp_name

        return self._request("GET", "/api/v1/wx/articles", params=params)

    def iter_articles(
        self,
        *,
        mp_name: Optional[str] = None,
        page_size: int = 20,
        max_pages: Optional[int] = None,
    ) -> Iterator[ArticleListItem]:
        page = 1
        seen_ids: set[str] = set()

        while True:
            data = self.list_articles(mp_name=mp_name, page=page, page_size=page_size)
            items = data.get("list") or []
            if not items:
                break

            new_items = 0
            for item in items:
                unique_token = (
                    item.get("id")
                    or item.get("appmsgid")
                    or item.get("link")
                    or item.get("title")
                )
                token_str = str(unique_token) if unique_token is not None else None
                if token_str and token_str in seen_ids:
                    continue
                if token_str:
                    seen_ids.add(token_str)
                new_items += 1
                yield item  # type: ignore[misc]

            if max_pages is not None and page >= max_pages:
                break
            if new_items == 0 or len(items) < page_size:
                break

            page += 1

    def fetch_article_content(self, article_id: int) -> ArticleDetail:
        return self._request("GET", f"/api/v1/wx/articles/{article_id}")


def fetch_article_content(article_id: int) -> ArticleDetail:
    """Module-level helper for quick use."""

    client = WeMPRSSClient()
    return client.fetch_article_content(article_id)


def iter_articles(**kwargs) -> Iterable[ArticleListItem]:
    client = WeMPRSSClient()
    return client.iter_articles(**kwargs)
