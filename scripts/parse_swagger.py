from pathlib import Path
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "openapi_authenticated.json"


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        raise SystemExit("openapi_authenticated.json 不存在，请先运行受权请求获取最新 schema")

    text = SCHEMA_PATH.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - 仅供快速排查
        raise SystemExit(f"无法解析 openapi schema: {exc}") from exc


def iter_paths(schema: dict):
    paths = schema.get("paths", {})
    for path, methods in sorted(paths.items()):
        for method, meta in methods.items():
            yield method.upper(), path, meta.get("summary", "")


def main() -> None:
    schema = load_schema()
    print("已解析 OpenAPI schema，列出前 30 个端点：\n")
    for idx, (method, path, summary) in enumerate(iter_paths(schema)):
        print(f"{method:6} {path} - {summary}")
        if idx >= 29:
            break

    login_schema = schema.get("components", {}).get("schemas", {}).get("Body_login_api_v1_wx_auth_login_post")
    if login_schema:
        fields = login_schema.get("properties", {})
        required = set(login_schema.get("required", []))
        print("\n登录接口字段：")
        for name, config in fields.items():
            req = "(必填)" if name in required else ""
            type_desc = config.get("type") or config.get("anyOf", [{}])[0].get("type", "-")
            print(f" - {name}: {type_desc} {req}")


if __name__ == "__main__":
    main()
