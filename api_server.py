# api_server.py
from datetime import datetime, timezone
import json
import os
from typing import Any

from email.utils import parsedate_to_datetime
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import requests
from config import (
    WECHAT_RSS_URL,
    WECHAT_API_BASE_URL,
    WECHAT_API_USERNAME,
    WECHAT_API_PASSWORD,
)
from urllib.parse import unquote

# 延迟导入耗时/有副作用的流程，避免仅导入服务时即初始化 LLM 客户端


def _normalize_text(value):
    if isinstance(value, str):
        return value.lower()
    if value is None:
        return ''
    return str(value).lower()

_WECHAT_SOURCE_ALIASES = {'wechat', '微信公众号', 'weixin', 'wx', 'mp', '公众号'}


def _normalize_source(article: dict) -> str:
    raw_source = (article.get('source') or '').strip()
    platform = (article.get('platform') or '').strip().lower()
    link = (article.get('link') or article.get('url') or '').lower()

    if raw_source:
        if raw_source.strip().lower() in _WECHAT_SOURCE_ALIASES:
            return '微信公众号'
        return raw_source

    if platform in _WECHAT_SOURCE_ALIASES or 'mp.weixin.qq.com' in link:
        return '微信公众号'
    if platform == 'yuque':
        return '语雀'

    return '未知来源'


def _build_source_tree(articles: list[dict]) -> list[dict]:
    totals: dict[str, int] = {}
    wechat_children: dict[str, int] = {}

    for article in articles:
        source_label = _normalize_source(article)
        totals[source_label] = totals.get(source_label, 0) + 1

        platform = (article.get('platform') or '').strip()
        if platform == '微信公众号':
            mp_name = (article.get('source') or '').strip() or '公众号未命名'
            wechat_children[mp_name] = wechat_children.get(mp_name, 0) + 1

    tree: list[dict] = []
    for label, count in totals.items():
        if label == '微信公众号':
            children = [
                {'label': name, 'count': child_count}
                for name, child_count in sorted(wechat_children.items(), key=lambda item: item[0])
            ]
            tree.append({'label': label, 'count': count, 'children': children})
        else:
            tree.append({'label': label, 'count': count})

    # Ensure consistent ordering: keep 微信公众号 first, others alphabetically
    tree.sort(key=lambda node: (0 if node['label'] == '微信公众号' else 1, node['label']))
    return tree


app = FastAPI(title="Info Fusion API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- 加载环境变量 & 统一响应工具 ---------
load_dotenv()


def ok(
    data: Any,
    code: int = 200,
    msg: str = "success",
    meta: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {"code": code, "msg": msg, "data": data}
    if meta:
        payload["meta"] = meta
    return JSONResponse(
        content=payload,
        status_code=200 if 200 <= code < 300 else code,
        headers=headers or None,
    )


def fail(code: int, msg: str) -> JSONResponse:
    return JSONResponse(content={"code": code, "msg": msg, "data": None}, status_code=code)


# --------- 鉴权（可选：当 API_TOKEN 存在时启用） ---------
API_TOKEN = os.getenv("API_TOKEN")


def verify_token(authorization: str | None = Header(default=None)):
    if not API_TOKEN:
        return  # 未配置则不启用鉴权
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


# --------- DTO（对外契约，snake_case 输出） ---------
class DocListItemDTO(BaseModel):
    id: str
    title: str
    author: str | None = None
    source: str = Field(description="yuque|wechat|qq|web")
    created_at: str | None = None
    updated_at: str | None = None


class DocDetailDTO(BaseModel):
    id: str
    title: str
    content: str | None = None
    tags: list[str] = []
    source: str = Field(description="yuque|wechat|qq|web")
    created_at: str | None = None


# --------- 工具函数（映射与时间格式） ---------
def _iso8601(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_published_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _canonical_source(article: dict) -> str:
    raw = (article.get("source") or article.get("platform") or "").lower()
    link = (article.get("link") or article.get("url") or "").lower()
    if any(k in raw for k in ["语雀", "yuque"]):
        return "yuque"
    if any(k in raw for k in ["wechat", "weixin", "微信公众号", "公众号", "wx", "mp"]):
        return "wechat"
    if "mp.weixin.qq.com" in link:
        return "wechat"
    return "web"


def _article_id(article: dict) -> str:
    return article.get("link") or article.get("url") or article.get("title") or ""


def _id_variants(value: str | None) -> set[str]:
    """生成用于匹配的 ID 变体：
    - 原始值（URL 解码后）
    - 去掉 fragment (#...) 后
    - 再去掉 query (?...) 后
    """
    v = unquote(value or "").strip()
    if not v:
        return {""}
    no_frag = v.split('#', 1)[0]
    no_query = no_frag.split('?', 1)[0]
    return {v, no_frag, no_query}


def _first_author(article: dict) -> str | None:
    author = article.get("author")
    if isinstance(author, str):
        # 兼容 "作者未注明 · 微信公众号" 的格式
        return author.split("·")[0].strip()
    if isinstance(author, list) and author:
        return str(author[0])
    return None


def _extract_tags(article: dict) -> list[str]:
    tags: list[str] = []
    if isinstance(article.get("key_points"), list):
        tags.extend([str(x) for x in article.get("key_points") if x is not None])
    llm = article.get("llm_result")
    if isinstance(llm, dict) and isinstance(llm.get("key_points"), list):
        tags.extend([str(x) for x in llm.get("key_points") if x is not None])
    # 去重保持顺序
    seen = set()
    uniq: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _load_articles_from_file() -> list[dict[str, Any]]:
    if not os.path.exists("final_knowledge_base.json"):
        return []
    with open("final_knowledge_base.json", "r", encoding="utf-8") as f:
        return json.load(f)


# --------- 健康检查：We-MP-RSS RSS 与（可选）认证 API ---------
def _probe_rss(timeout: int = 5) -> dict[str, Any]:
    url = WECHAT_RSS_URL
    result: dict[str, Any] = {"url": url}
    if not url:
        result.update({"ok": False, "error": "WECHAT_RSS_URL 未配置"})
        return result
    try:
        resp = requests.get(url, timeout=timeout)
        result["status"] = resp.status_code
        if resp.status_code == 200 and (b"<rss" in resp.content or b"<channel" in resp.content):
            result["ok"] = True
        else:
            result["ok"] = False
            result["error"] = "RSS 非 200 或内容异常"
    except requests.RequestException as exc:  # noqa: BLE001
        result.update({"ok": False, "error": str(exc)})
    return result


def _probe_api_auth_and_list(timeout: int = 5) -> dict[str, Any]:
    base = (WECHAT_API_BASE_URL or "").rstrip("/")
    user = WECHAT_API_USERNAME
    pwd = WECHAT_API_PASSWORD
    result: dict[str, Any] = {"base": base, "ok": None}
    if not base:
        result.update({"ok": False, "error": "WECHAT_API_BASE_URL 未配置"})
        return result
    if not user or not pwd:
        result.update({"ok": None, "note": "未配置用户名/密码，跳过深度检查"})
        return result

    token_url = f"{base}/api/v1/wx/auth/token"
    list_url = f"{base}/api/v1/wx/articles?page=1&pageSize=1"
    try:
        # 获取 token
        token_resp = requests.post(
            token_url,
            data={"username": user, "password": pwd},
            timeout=timeout,
        )
        result["token_status"] = token_resp.status_code
        payload = token_resp.json() if token_resp.headers.get("content-type", "").startswith("application/json") else {}
        code = payload.get("code")
        if token_resp.status_code == 200 and (code in (None, 0)):
            data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
            token = data.get("access_token") if isinstance(data, dict) else None
            if not token:
                result.update({"ok": False, "error": "token 响应缺少 access_token"})
                return result
        else:
            detail = payload.get("detail") or payload.get("message") or payload
            result.update({"ok": False, "error": f"获取 token 失败: {detail}"})
            return result

        # 拉一条列表
        lst_resp = requests.get(list_url, headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
        result["list_status"] = lst_resp.status_code
        lst_payload = lst_resp.json() if lst_resp.headers.get("content-type", "").startswith("application/json") else {}
        lcode = lst_payload.get("code")
        if lst_resp.status_code == 200 and (lcode in (None, 0)):
            result["ok"] = True
            if isinstance(lst_payload.get("data"), dict):
                result["sample_total"] = lst_payload["data"].get("total")
        else:
            result.update({"ok": False, "error": lst_payload.get("detail") or lst_payload})
    except requests.RequestException as exc:  # noqa: BLE001
        result.update({"ok": False, "error": str(exc)})
    return result


# --------- v1 标准接口：文档列表与详情（只读） ---------
@app.get("/api/v1/docs", dependencies=[Depends(verify_token)])
def list_docs(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
):
    try:
        raw = _load_articles_from_file()
        items: list[DocListItemDTO] = []
        for art in raw:
            created = _parse_published_time(art.get("published_time"))
            updated_iso = art.get("processed_at") or _iso8601(created)
            dto = DocListItemDTO(
                id=_article_id(art),
                title=art.get("title") or "",
                author=_first_author(art),
                source=_canonical_source(art),
                created_at=_iso8601(created),
                updated_at=updated_iso if updated_iso and "T" in updated_iso else _iso8601(created),
            )
            items.append(dto)

        total = len(items)
        start = (page - 1) * size
        end = start + size
        data_slice = [i.model_dump() for i in items[start:end]]
        meta = {"page": page, "size": size, "total": total, "has_more": end < total}
        # ETag 简易实现：基于文件 mtime、size、total
        etag: str | None = None
        try:
            if os.path.exists("final_knowledge_base.json"):
                stat = os.stat("final_knowledge_base.json")
                etag = f'W/"{int(stat.st_mtime)}-{stat.st_size}-{total}"'
        except Exception:  # noqa: BLE001 - 非关键路径容错
            etag = None

        if etag and if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})

        return ok(data_slice, meta=meta, headers=({"ETag": etag} if etag else None))
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        return fail(500, f"server error: {exc}")


@app.get("/healthz")
def healthz(deep: bool = Query(default=False, description="是否进行深度检查（包含认证 API）")) -> JSONResponse:
    """轻量健康检查：默认仅探测 RSS；deep=1 时再探测认证 API。

    注意：深度检查会尝试登录上游 We-MP-RSS，频繁调用可能触发上游的登录限制。
    建议在定时或手动排障时使用 deep=1，常规探活用默认模式即可。
    """
    rss = _probe_rss()
    data: dict[str, Any] = {"rss": rss}
    if deep:
        api = _probe_api_auth_and_list()
        data["api"] = api
        overall_ok = bool(rss.get("ok") and api.get("ok"))
    else:
        overall_ok = bool(rss.get("ok"))
    return ok({"status": "ok" if overall_ok else "degraded", **data})


@app.get("/api/v1/docs/{doc_id:path}", dependencies=[Depends(verify_token)])
def get_doc_detail(doc_id: str) -> JSONResponse:
    try:
        raw = _load_articles_from_file()
        found: dict[str, Any] | None = None
        cand_set = _id_variants(doc_id)
        for art in raw:
            art_ids = _id_variants(_article_id(art))
            if cand_set & art_ids:
                found = art
                break
        if not found:
            return fail(404, "not found")

        created = _parse_published_time(found.get("published_time"))
        content = found.get("content") or ""
        dto = DocDetailDTO(
            id=_article_id(found),
            title=found.get("title") or "",
            content=content,
            tags=_extract_tags(found),
            source=_canonical_source(found),
            created_at=_iso8601(created),
        )
        return ok(dto.model_dump())
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        return fail(500, f"server error: {exc}")


@app.get("/api/v1/doc", dependencies=[Depends(verify_token)])
def get_doc_detail_by_query(id: str = Query(default=..., description="文档 ID，通常为文章链接（需要进行 URL 编码）")) -> JSONResponse:
    """详情的备选接口：通过 query 参数 id 传入，适合包含 ? 的完整 URL。"""
    try:
        raw = _load_articles_from_file()
        cand_set = _id_variants(id)
        for art in raw:
            if cand_set & _id_variants(_article_id(art)):
                created = _parse_published_time(art.get("published_time"))
                dto = DocDetailDTO(
                    id=_article_id(art),
                    title=art.get("title") or "",
                    content=art.get("content") or "",
                    tags=_extract_tags(art),
                    source=_canonical_source(art),
                    created_at=_iso8601(created),
                )
                return ok(dto.model_dump())
        return fail(404, "not found")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        return fail(500, f"server error: {exc}")


@app.get("/api/v1/search", dependencies=[Depends(verify_token)])
def v1_search(q: str = Query(default="", alias="q")) -> JSONResponse:
    query = (q or "").strip().lower()
    if not query:
        return fail(400, "query required")

    try:
        raw = _load_articles_from_file()
        results: list[DocListItemDTO] = []
        for art in raw:
            title = _normalize_text(art.get("title"))
            content = _normalize_text(art.get("content"))
            author = _normalize_text(art.get("author"))
            summary_candidates: list[Any] = []
            if isinstance(art.get("key_points"), list):
                summary_candidates.extend(art["key_points"])
            llm_result = art.get("llm_result")
            if isinstance(llm_result, dict):
                summary_candidates.extend([
                    llm_result.get("deep_summary"),
                    llm_result.get("deep_summary_with_link"),
                    llm_result.get("open_question"),
                ])
                if isinstance(llm_result.get("key_points"), list):
                    summary_candidates.extend(llm_result["key_points"])
            combined = " ".join(_normalize_text(x) for x in summary_candidates if x is not None)

            if (query in title) or (query in content) or (query in combined) or (query in author):
                created = _parse_published_time(art.get("published_time"))
                updated_iso = art.get("processed_at") or _iso8601(created)
                results.append(
                    DocListItemDTO(
                        id=_article_id(art),
                        title=art.get("title") or "",
                        author=_first_author(art),
                        source=_canonical_source(art),
                        created_at=_iso8601(created),
                        updated_at=updated_iso if updated_iso and "T" in updated_iso else _iso8601(created),
                    )
                )

        data = [r.model_dump() for r in results]
        meta = {"page": 1, "size": len(data), "total": len(data), "has_more": False}
        return ok(data, meta=meta)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        return fail(500, f"server error: {exc}")


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=302)


# --------- 运营工具：清缓存并可选触发 We-MP-RSS 刷新 ---------
@app.post("/ops/wechat/reload", dependencies=[Depends(verify_token)])
def ops_wechat_reload(
    refresh: bool = Query(default=False, description="是否调用 We-MP-RSS 刷新订阅（可能较慢）"),
    deep: bool = Query(default=False, description="返回健康检查结果（deep=1 包含登录+列表探测）"),
) -> JSONResponse:
    """清理与微信相关的进程级缓存，确保切换账号后立即生效。

    包括：
    - 清空 wechat_pubaccount_fetcher 的 LRU 缓存（公众号名称映射、API 索引）
    - 重置一次性刷新开关，使得后续抓取可再次触发 We-MP-RSS 主动刷新
    - 可选：立即调用一次刷新任务（可能耗时）
    """
    try:
        import importlib
        wf = importlib.import_module("wechat_pubaccount_fetcher")

        cleared: list[str] = []
        for fn_name in ("_load_article_source_map", "_load_api_article_index"):
            fn = getattr(wf, fn_name, None)
            if fn is not None and hasattr(fn, "cache_clear"):
                try:
                    fn.cache_clear()  # type: ignore[attr-defined]
                    cleared.append(fn_name)
                except Exception:
                    pass

        if hasattr(wf, "_refresh_attempted"):
            try:
                setattr(wf, "_refresh_attempted", False)
            except Exception:
                pass

        info: dict[str, Any] = {"cleared": cleared}

        if refresh:
            try:
                # 触发一次刷新（内部会调用 we_mp_rss_sync.refresh_wechat_articles）
                trigger = getattr(wf, "_trigger_we_rss_refresh_once", None)
                if trigger is not None:
                    trigger()
                    info["refresh"] = "dispatched"
                else:
                    info["refresh"] = "no-trigger"
            except Exception as exc:  # noqa: BLE001
                info["refresh_error"] = str(exc)

        if deep:
            # 返回健康检查，便于确认新账号配置已生效
            rss = _probe_rss()
            api = _probe_api_auth_and_list()
            info["healthz"] = {"rss": rss, "api": api}

        return ok(info)
    except Exception as exc:  # noqa: BLE001
        return fail(500, f"reload failed: {exc}")



@app.get("/api/articles")
def get_articles() -> JSONResponse:
    """获取处理后的文章数据"""
    try:
        articles: list[dict[str, Any]] = []
        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)

        filtered_articles: list[dict[str, Any]] = []
        if os.path.exists('filtered_articles.json'):
            with open('filtered_articles.json', 'r', encoding='utf-8') as f:
                filtered_articles = json.load(f)

        if articles:
            payload = {
                'success': True,
                'data': articles,
                'count': len(articles),
                'last_updated': datetime.now().isoformat(),
                'filtered': filtered_articles,
                'filtered_count': len(filtered_articles)
            }
        else:
            payload = {
                'success': False,
                'message': '数据文件不存在或为空',
                'data': [],
                'filtered': filtered_articles,
                'filtered_count': len(filtered_articles)
            }
        return JSONResponse(content=payload)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            content={
                'success': False,
                'message': f'读取数据时出错: {exc}',
                'data': []
            },
            status_code=500
        )


@app.get("/api/stats")
def get_stats() -> JSONResponse:
    """获取统计信息"""
    try:
        stats: dict[str, Any] = {
            'total_articles': 0,
            'sources': {},
            'domains': {},
            'last_processed': None
        }

        filtered_articles_count = 0

        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)

            stats['total_articles'] = len(articles)
            stats['source_tree'] = _build_source_tree(articles)

            for article in articles:
                source = _normalize_source(article)
                stats['sources'][source] = stats['sources'].get(source, 0) + 1

                processed_at = article.get('processed_at')
                if processed_at and (
                    stats['last_processed'] is None or processed_at > stats['last_processed']
                ):
                    stats['last_processed'] = processed_at

        if os.path.exists('filtered_articles.json'):
            with open('filtered_articles.json', 'r', encoding='utf-8') as f:
                filtered_articles = json.load(f)
                filtered_articles_count = len(filtered_articles)

        return JSONResponse(content={
            'success': True,
            'data': {**stats, 'filtered_count': filtered_articles_count}
        })
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            content={'success': False, 'message': f'获取统计信息时出错: {exc}'},
            status_code=500
        )


@app.post("/api/refresh")
def refresh_data() -> JSONResponse:
    """触发后端重新聚合并运行 AI 处理"""
    try:
        # 避免导入 api_server 时立刻初始化 LLM 客户端
        from main import run_full_pipeline  # noqa: WPS433
        processed_articles = run_full_pipeline()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f'刷新数据时出错: {exc}') from exc

    return JSONResponse(content={
        'success': True,
        'message': '数据已重新聚合并处理完毕',
        'count': len(processed_articles)
    })


@app.get("/api/search")
def search_articles(q: str = Query(default="", alias="q")) -> JSONResponse:
    """搜索文章"""
    query = (q or "").lower()

    if not query:
        return JSONResponse(content={
            'success': False,
            'message': '搜索关键词不能为空',
            'data': []
        }, status_code=400)

    try:
        if not os.path.exists('final_knowledge_base.json'):
            return JSONResponse(content={
                'success': False,
                'message': '数据文件不存在',
                'data': []
            }, status_code=404)

        with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)

        results = []
        for article in articles:
            title = _normalize_text(article.get('title'))
            content = _normalize_text(article.get('content'))
            author = _normalize_text(article.get('author'))
            summary_candidates: list[Any] = [
                article.get('deep_summary'),
                article.get('deep_summary_with_link'),
                article.get('open_question')
            ]
            if isinstance(article.get('key_points'), list):
                summary_candidates.extend(article['key_points'])

            llm_result = article.get('llm_result')
            if isinstance(llm_result, dict):
                summary_candidates.extend([
                    llm_result.get('deep_summary'),
                    llm_result.get('deep_summary_with_link'),
                    llm_result.get('open_question')
                ])
                if isinstance(llm_result.get('key_points'), list):
                    summary_candidates.extend(llm_result['key_points'])

            combined_summary = ' '.join(
                _normalize_text(item) for item in summary_candidates if item is not None
            )

            if (
                query in title
                or query in content
                or query in combined_summary
                or query in author
            ):
                results.append(article)

        return JSONResponse(content={
            'success': True,
            'data': results,
            'count': len(results),
            'query': query
        })
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(content={
            'success': False,
            'message': f'搜索时出错: {exc}',
            'data': []
        }, status_code=500)


@app.get("/api/source-tree")
def get_source_tree() -> JSONResponse:
    """返回分层的数据源结构，供前端构建折叠视图"""
    try:
        if not os.path.exists('final_knowledge_base.json'):
            return JSONResponse(content={
                'success': False,
                'message': '数据文件不存在',
                'data': []
            }, status_code=404)

        with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)

        tree = _build_source_tree(articles)
        return JSONResponse(content={'success': True, 'data': tree})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(content={
            'success': False,
            'message': f'获取数据源结构时出错: {exc}',
            'data': []
        }, status_code=500)


if __name__ == '__main__':
    import uvicorn

    print("启动 API 服务器...")
    print("API 地址: http://localhost:5000")
    print("文章列表: http://localhost:5000/api/articles")
    print("统计信息: http://localhost:5000/api/stats")
    print("搜索接口: http://localhost:5000/api/search?q=关键词")

    uvicorn.run("api_server:app", host='0.0.0.0', port=5000, reload=True)