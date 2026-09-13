"""Client + cache cho Front-End-Checklist MCP server.

MCP endpoint: https://mcp.frontendchecklist.io (JSON-RPC 2.0 / Streamable HTTP).
Cache rules + categories locally trong <ROOT>/admin/.cache/fe-checklist/
để list nhanh và không spam MCP server.
"""

from __future__ import annotations

import json
import os
import pathlib
import threading
import time
import urllib.error
import urllib.request
from typing import Any

CACHE_DIR = pathlib.Path(__file__).resolve().parent / ".cache" / "fe-checklist"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# TTL cho categories + rules
CATEGORIES_TTL = 60 * 60 * 24       # 24h
RULES_TTL = 60 * 60 * 24 * 7        # 7d

MCP_URL = os.environ.get("FE_CHECKLIST_MCP_URL", "https://mcp.frontendchecklist.io")

_lock = threading.Lock()


def _http_post(url: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"MCP unreachable: {exc}") from exc

    # Thử JSON thuần trước; nếu không được thì SSE
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        raise RuntimeError(f"MCP returned non-JSON: {raw[:200]}")


def _tools_call(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Gọi MCP tools/call."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    res = _http_post(MCP_URL, payload)
    if "error" in res:
        raise RuntimeError(f"MCP error: {res['error']}")
    content = (res.get("result") or {}).get("content") or []
    if not content:
        return None
    text = content[0].get("text") if isinstance(content[0], dict) else None
    if text is None:
        return res.get("result")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _cache_get(name: str, max_age: int) -> Any | None:
    p = CACHE_DIR / f"{name}.json"
    if not p.exists():
        return None
    age = time.time() - p.stat().st_mtime
    if age > max_age:
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _cache_set(name: str, data: Any) -> None:
    p = CACHE_DIR / f"{name}.json"
    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_categories(use_cache: bool = True) -> dict[str, Any]:
    """Trả về 11 categories + ruleCount."""
    with _lock:
        if use_cache:
            cached = _cache_get("categories", CATEGORIES_TTL)
            if cached:
                return cached
        data = _tools_call("list_categories", {})
        # MCP trả về JSON string trong content[0].text — _tools_call parse
        # sẵn thành dict. Nếu lỗi trả None.
        if data is None:
            data = {"categories": []}
        if isinstance(data, dict) and "categories" in data:
            _cache_set("categories", data)
        return data


def get_rule(slug: str, use_cache: bool = True) -> dict[str, Any]:
    """Trả về chi tiết 1 rule (HTML/A11y/...)."""
    cache_key = f"rule__{slug}"
    with _lock:
        if use_cache:
            cached = _cache_get(cache_key, RULES_TTL)
            if cached:
                return cached
        data = _tools_call("get_rule", {"slug": slug})
        if data is None:
            data = {"slug": slug, "error": "not found"}
        if isinstance(data, dict):
            _cache_set(cache_key, data)
        return data


def search_rules(query: str, category: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    """Tìm rule theo keyword + optional category. Tự động fetch hết qua cursor."""
    args: dict[str, Any] = {"query": query, "limit": limit}
    if category:
        args["category"] = category
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    # Vòng lặp cursor — MCP trả {rules, nextCursor, totalCount}
    for _ in range(20):  # safety cap
        if cursor:
            args["cursor"] = cursor
        res = _tools_call("search_rules", args)
        if isinstance(res, dict) and "rules" in res:
            out.extend(res["rules"])
            cursor = res.get("nextCursor")
            if not cursor:
                break
        elif isinstance(res, list):
            out.extend(res)
            break
        else:
            break
    return out


def list_all_rules_in_category(category: str) -> dict[str, Any]:
    """Lấy tất cả rules trong 1 category (dùng search_rules với query rộng + pagination)."""
    all_rules: dict[str, dict[str, Any]] = {}
    target = 0
    cats = list_categories()
    target = next(
        (c.get("ruleCount", 0) for c in (cats.get("categories") or []) if c.get("name") == category),
        0,
    )
    for q in ("a", "e", "i", "o", "u", "t", "n", "s", "r", "l", "c"):
        rules = search_rules(q, category=category)
        for r in rules:
            # Filter chỉ rules thuộc category này
            pc = r.get("primaryCategory") or ""
            cats_list = r.get("categories") or []
            if pc != category and category not in cats_list:
                continue
            slug = r.get("slug") or r.get("id")
            if slug and slug not in all_rules:
                all_rules[slug] = r
        if target and len(all_rules) >= target:
            break
    return {"category": category, "count": len(all_rules), "rules": list(all_rules.values())}


def review_code(code: str, language: str = "html") -> dict[str, Any]:
    """Static heuristic check cho HTML/CSS/JS code paste."""
    res = _tools_call("review_code", {"code": code, "language": language})
    return res if isinstance(res, dict) else {"result": res}


def audit_url(url: str) -> dict[str, Any]:
    """Audit 1 public URL."""
    res = _tools_call("audit_url", {"url": url})
    return res if isinstance(res, dict) else {"result": res}


def explain_rule(slug: str) -> dict[str, Any]:
    """Hướng dẫn chi tiết + ví dụ fix cho rule."""
    res = _tools_call("explain_rule", {"slug": slug})
    return res if isinstance(res, dict) else {"result": res}


def fix_rule(slug: str, code: str = "") -> dict[str, Any]:
    """Sinh code fix cho rule."""
    args: dict[str, Any] = {"slug": slug}
    if code:
        args["code"] = code
    res = _tools_call("fix_rule", args)
    return res if isinstance(res, dict) else {"result": res}


def get_workflow(name: str) -> dict[str, Any]:
    """Lấy workflow (launch/a11y/seo/security/perf)."""
    res = _tools_call("get_workflow", {"name": name})
    return res if isinstance(res, dict) else {"result": res}


def get_checklist_rules(category: str) -> dict[str, Any]:
    """Lấy tất cả rules trong 1 category."""
    res = _tools_call("get_checklist_rules", {"category": category})
    return res if isinstance(res, dict) else {"result": res}


def cache_status() -> dict[str, Any]:
    """Liệt kê file cache + tuổi."""
    out = []
    for p in sorted(CACHE_DIR.glob("*.json")):
        st = p.stat()
        out.append({
            "file": p.name,
            "size_kb": round(st.st_size / 1024, 1),
            "age_s": round(time.time() - st.st_mtime, 1),
        })
    return {"dir": str(CACHE_DIR), "files": out}
