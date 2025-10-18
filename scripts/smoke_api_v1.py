from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


def main() -> int:
    # 确保可以导入 api_server 模块
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    import api_server  # noqa: WPS433

    # 关闭鉴权以便本地冒烟
    api_server.API_TOKEN = None  # type: ignore[attr-defined]

    client = TestClient(api_server.app)

    # 1) 根路径重定向
    r = client.get("/", allow_redirects=False)
    print("ROOT", r.status_code, r.headers.get("location"))

    # 2) 列表 + ETag/304
    r = client.get("/api/v1/docs")
    print("LIST", r.status_code)
    etag = r.headers.get("ETag")
    print("ETAG", etag)
    if etag:
        r2 = client.get("/api/v1/docs", headers={"If-None-Match": etag})
        print("LIST_304", r2.status_code)
    else:
        print("LIST_304 skipped (no ETag)")

    # 3) 搜索
    r = client.get("/api/v1/search", params={"q": "test"})
    print("SEARCH", r.status_code)
    try:
        body = r.json()
        print("SEARCH_META", body.get("meta"))
    except Exception:  # noqa: BLE001
        pass

    # 4) 详情备选（预计 404）
    r = client.get("/api/v1/doc", params={"id": "https://example.com/not-exist"})
    print("DETAIL_BY_QUERY", r.status_code)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
