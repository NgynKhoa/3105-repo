"""Module đồng bộ trạng thái local admin lên GitHub Pages real-time.

Luồng hoạt động:
    1. Admin bấm "Sync lên GitHub Pages" (hoặc auto-poll mỗi 30s)
    2. POST /api/sync/diff  → tính khác biệt giữa local state và GitHub state
    3. UI hiển thị modal diff preview
    4. User confirm → POST /api/sync/push → gọi gh_write_file cho từng file
    5. Sau khi push → workflow build-public.yml tự động deploy Pages

Endpoints đăng ký qua `register_sync_routes(app)`.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests

# File lưu trạng thái sync local (hash + last commit SHA + history)
SYNC_STATE_FILE_NAME = ".3105/sync_state.json"

# Các file/folder đồng bộ từ local → GitHub Pages.
# LƯU Ý: chỉ sync những thứ GitHub Pages build-public.py đọc.
SYNC_INCLUDE_PATHS = [
    "repositories/demo/repo.yml",      # Source-of-truth: layout, theme, packages
    ".3105/admin-settings.json",        # Theme + rain + dark mode
    "admin/templates/index.html",       # HTML shell (nếu admin đã sửa)
    "admin/templates/_blog_posts.json", # Blog content
    "assets/blog",                      # Blog images
]

# Files KHÔNG sync (chỉ là admin tool, không cần trên Pages)
SYNC_EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    "node_modules",
    "flask.log",
    "flask.err",
    "admin.err",
    "admin.log",
    "server.log",
    "server.err.log",
    "cookies.txt",
    "test_*.png",
    "test_*.py",
    ".env",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_blob_sha(content: bytes) -> str:
    """Tính Git blob SHA-1 cho 1 file (giống cách GitHub tính).

    Normalize CRLF → LF để khớp với cách Git lưu file (core.autocrlf trên
    Windows sẽ convert CRLF thành LF khi commit).

    Công thức: sha1("blob " + size + "\0" + content_normalized)
    """
    import hashlib as _h
    # Normalize line endings: thay CRLF -> LF để khớp với content trên GitHub
    normalized = content.replace(b"\r\n", b"\n")
    header = f"blob {len(normalized)}\0".encode("ascii")
    return _h.sha1(header + normalized).hexdigest()[:16]


def _git_blob_sha_text(text: str) -> str:
    return _git_blob_sha(text.encode("utf-8"))


def _sha256_of_text(text: str) -> str:
    """DEPRECATED — chỉ dùng để log, không dùng để so sánh với GitHub."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _should_exclude(path: pathlib.Path) -> bool:
    """Return True nếu path nằm trong danh sách exclude."""
    name = path.name
    for pat in SYNC_EXCLUDE_PATTERNS:
        if pat.startswith("test_*") and name.startswith("test_"):
            return True
        if name == pat:
            return True
    return False


def collect_local_files(root: pathlib.Path) -> list[dict[str, Any]]:
    """Thu thập tất cả file cần sync từ local.

    Returns list[dict] với keys: path, size, sha (Git blob SHA-1 16-char prefix).
    """
    files: list[dict[str, Any]] = []
    for include_path in SYNC_INCLUDE_PATHS:
        full = root / include_path
        if not full.exists():
            continue
        if full.is_file():
            rel = include_path
            try:
                content = full.read_bytes()
                files.append({
                    "path": rel.replace("\\", "/"),
                    "size": len(content),
                    "sha": _git_blob_sha(content),
                })
            except Exception:
                continue
        elif full.is_dir():
            for p in full.rglob("*"):
                if p.is_file() and not _should_exclude(p):
                    rel = str(p.relative_to(root)).replace("\\", "/")
                    try:
                        content = p.read_bytes()
                        files.append({
                            "path": rel,
                            "size": len(content),
                            "sha": _git_blob_sha(content),
                        })
                    except Exception:
                        continue
    return files


def fetch_remote_files(
    full_name: str,
    token: str,
    api_base: str,
    branch: str = "main",
) -> list[dict[str, Any]]:
    """Lấy danh sách file + hash từ GitHub repo để so sánh với local.

    Hai bước:
      1. Dùng Git Trees API (recursive=1) để list file + SHA của files KHÔNG nằm
         trong folder bắt đầu bằng dấu chấm (vd `.3105/`).
      2. Với mỗi include path là file/folder dotfile → dùng Contents API riêng.

    Returns list[dict] giống collect_local_files: path, size, sha256.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "3105-repo-builder/sync",
    }
    include_set = set(SYNC_INCLUDE_PATHS)
    remote: list[dict[str, Any]] = []
    matched_paths: set[str] = set()

    # Bước 1: Trees API (lấy files trong folder thường + assets/blog recursive)
    url = f"{api_base}/repos/{full_name}/git/trees/{branch}?recursive=1"
    try:
        resp = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as exc:
        raise RuntimeError(f"GitHub API error: {exc}") from exc
    if resp.status_code != 200:
        raise RuntimeError(
            f"GitHub returned {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    for item in data.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob":
            continue
        if path in include_set:
            remote.append({
                "path": path,
                "size": item.get("size", 0),
                "sha": (item.get("sha") or "")[:16],
            })
            matched_paths.add(path)
        else:
            for inc in include_set:
                if path.startswith(inc + "/"):
                    remote.append({
                        "path": path,
                        "size": item.get("size", 0),
                        "sha": (item.get("sha") or "")[:16],
                    })
                    matched_paths.add(path)
                    break

    # Bước 2: Contents API cho mỗi include path chưa matched
    for inc_path in SYNC_INCLUDE_PATHS:
        if inc_path in matched_paths:
            continue
        get_url = f"{api_base}/repos/{full_name}/contents/{inc_path}?ref={branch}"
        try:
            r = requests.get(get_url, headers=headers, timeout=15)
        except requests.RequestException:
            continue
        if r.status_code != 200:
            continue
        d = r.json()
        if isinstance(d, dict):
            # Single file
            remote.append({
                "path": d.get("path", inc_path),
                "size": d.get("size", 0),
                "sha": (d.get("sha") or "")[:16],
            })
            matched_paths.add(inc_path)
        elif isinstance(d, list):
            # Folder contents
            for item in d:
                if item.get("type") == "file":
                    remote.append({
                        "path": item["path"],
                        "size": item.get("size", 0),
                        "sha": (item.get("sha") or "")[:16],
                    })

    return remote


def compute_diff(local: list[dict], remote: list[dict]) -> dict[str, Any]:
    """Tính khác biệt giữa local và remote (dựa trên Git blob SHA-1).

    Returns:
        {
          "added":   [files in local not in remote],
          "modified": [files in both but different sha],
          "deleted": [files in remote not in local],
          "unchanged_count": int,
        }
    """
    local_map = {f["path"]: f for f in local}
    remote_map = {f["path"]: f for f in remote}
    added = [local_map[p] for p in local_map if p not in remote_map]
    deleted = [remote_map[p] for p in remote_map if p not in local_map]
    modified = []
    unchanged = 0
    for p, lf in local_map.items():
        if p in remote_map:
            rf = remote_map[p]
            if lf["sha"] != rf["sha"]:
                modified.append({
                    "path": p,
                    "local_sha": lf["sha"],
                    "remote_sha": rf["sha"],
                    "local_size": lf["size"],
                    "remote_size": rf["size"],
                })
            else:
                unchanged += 1
    return {
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "unchanged_count": unchanged,
    }


def read_sync_state(root: pathlib.Path) -> dict[str, Any]:
    """Đọc file state sync, tạo mới nếu chưa có."""
    state_file = root / SYNC_STATE_FILE_NAME
    if not state_file.exists():
        return {
            "last_pushed_at": None,
            "last_commit_sha": None,
            "last_diff": None,
            "history": [],
        }
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {
            "last_pushed_at": None,
            "last_commit_sha": None,
            "last_diff": None,
            "history": [],
        }


def write_sync_state(root: pathlib.Path, state: dict[str, Any]) -> None:
    """Ghi file state (atomic qua .tmp + rename)."""
    state_file = root / SYNC_STATE_FILE_NAME
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(state_file)


def append_history(root: pathlib.Path, entry: dict[str, Any]) -> None:
    """Append 1 entry vào history (giữ tối đa 20 entry)."""
    state = read_sync_state(root)
    history = state.get("history", [])
    history.insert(0, entry)
    state["history"] = history[:20]
    state["last_pushed_at"] = entry.get("pushed_at")
    state["last_commit_sha"] = entry.get("commit_sha")
    state["last_diff"] = entry.get("diff_summary")
    write_sync_state(root, state)


def register_sync_routes(app, ROOT: pathlib.Path, Config) -> None:
    """Đăng ký 4 endpoints sync vào Flask app."""

    def _resolve_target_repo():
        """Tìm repo target (NgynKhoa/3105-repo) — fallback env config."""
        from flask import session, jsonify as _jsonify

        # Try session-based owned repos first (giống các endpoint khác)
        try:
            from .auth import get_owned_repos as auth_get_owned_repos
            owned = auth_get_owned_repos()
            target = next(
                (r for r in owned if r.get("full_name", "").lower() == "ngynkhoa/3105-repo"),
                None,
            )
            if target:
                return target
        except Exception:
            pass

        # Fallback: dùng GITHUB_PAT trực tiếp (chế độ non-OAuth)
        return None

    @app.get("/api/sync/status")
    def sync_status():
        """Trả về trạng thái sync hiện tại: có thay đổi không, last pushed, ... """
        from flask import jsonify
        state = read_sync_state(ROOT)
        local = collect_local_files(ROOT)
        return jsonify({
            "ok": True,
            "last_pushed_at": state.get("last_pushed_at"),
            "last_commit_sha": state.get("last_commit_sha"),
            "local_files_count": len(local),
            "tracked_paths": SYNC_INCLUDE_PATHS,
        })

    @app.post("/api/sync/diff")
    def sync_diff():
        """Tính diff giữa local và GitHub state — không ghi gì cả.

        Body (optional): { "slug": "demo" } — để lookup repo target.
        """
        from flask import jsonify, request as _req
        slug = (_req.get_json(silent=True) or {}).get("slug", "").strip()
        local = collect_local_files(ROOT)

        # Lấy GitHub token
        token = None
        full_name = None
        target = _resolve_target_repo()
        if target:
            full_name = target.get("full_name")
            try:
                from .auth import get_current_token
                token = get_current_token()
            except Exception:
                token = None

        # Fallback: dùng GITHUB_PAT từ env
        if not token:
            token = os.environ.get("GITHUB_PAT") or Config.GITHUB_PAT
            full_name = full_name or "NgynKhoa/3105-repo"

        if not token:
            return jsonify({
                "ok": False,
                "error": "Không có GitHub token. Đăng nhập OAuth hoặc cấu hình GITHUB_PAT.",
            }), 401

        try:
            remote = fetch_remote_files(
                full_name=full_name,
                token=token,
                api_base=Config.GITHUB_API_BASE,
            )
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

        diff = compute_diff(local, remote)
        return jsonify({
            "ok": True,
            "full_name": full_name,
            "local_files_count": len(local),
            "remote_files_count": len(remote),
            "diff": diff,
            "total_changes": len(diff["added"]) + len(diff["modified"]) + len(diff["deleted"]),
        })

    @app.post("/api/sync/push")
    def sync_push():
        """Push tất cả file modified/added lên GitHub (1 commit per file).

        Body (optional): { "slug": "demo", "message": "...", "mode": "direct" }
        """
        from flask import jsonify, request as _req
        body = _req.get_json(silent=True) or {}
        slug = body.get("slug", "").strip()
        message = body.get("message", "chore(sync): update from local admin via 3105 Builder").strip()
        mode = body.get("mode", "direct").strip()  # "direct" để vào main ngay (Pages rebuild ngay)

        if mode not in ("direct", "pr"):
            return jsonify({"ok": False, "error": "mode phải là 'direct' hoặc 'pr'"}), 400

        # Token + target repo
        token = None
        target = _resolve_target_repo()
        if target:
            try:
                from .auth import get_current_token
                token = get_current_token()
            except Exception:
                token = None
        if not token:
            token = os.environ.get("GITHUB_PAT") or Config.GITHUB_PAT
        full_name = target.get("full_name") if target else "NgynKhoa/3105-repo"

        if not token:
            return jsonify({"ok": False, "error": "Không có GitHub token"}), 401

        # Tính diff
        local = collect_local_files(ROOT)
        try:
            remote = fetch_remote_files(full_name, token, Config.GITHUB_API_BASE)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

        diff = compute_diff(local, remote)
        to_push = diff["added"] + diff["modified"]

        if not to_push and not diff["deleted"]:
            return jsonify({
                "ok": True,
                "pushed": 0,
                "message": "Không có thay đổi — local đã đồng bộ với GitHub.",
            })

        # Lazy import để tránh circular
        from .github_write import write_file as gh_write_file
        import base64 as _b64
        import requests as _req

        def _push_one(rel_path: str, content: str) -> dict | None:
            """Push 1 file. Try via gh_write_file (text), fallback raw API (binary)."""
            try:
                return gh_write_file(
                    token=token,
                    full_name=full_name,
                    path=rel_path,
                    content=content,
                    commit_message=message,
                    mode=mode,
                )
            except UnicodeEncodeError:
                # Binary file — content is already base64. Bypass via raw API.
                meta_url = f"{Config.GITHUB_API_BASE}/repos/{full_name}"
                meta = _req.get(meta_url, headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                }, timeout=20).json()
                default_branch = meta.get("default_branch", "main")
                target_branch = default_branch if mode == "direct" else default_branch

                sha_url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/{rel_path}?ref={target_branch}"
                sha_resp = _req.get(sha_url, headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                }, timeout=20)
                existing_sha = sha_resp.json().get("sha") if sha_resp.status_code == 200 else None

                put_body = {
                    "message": message,
                    "content": content,
                    "branch": target_branch,
                }
                if existing_sha:
                    put_body["sha"] = existing_sha
                put_url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/{rel_path}"
                put_resp = _req.put(put_url, headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                }, json=put_body, timeout=60)
                if put_resp.status_code not in (200, 201):
                    raise RuntimeError(f"binary PUT failed: {put_resp.status_code} {put_resp.text[:200]}")
                data = put_resp.json()
                return {
                    "commit_sha": data.get("commit", {}).get("sha"),
                    "pr_url": None,
                }

        pushed_results = []
        errors = []
        for f in to_push:
            file_path = ROOT / f["path"]
            is_binary = f["path"].lower().endswith((
                ".png", ".jpg", ".jpeg", ".gif", ".webp",
                ".ico", ".pdf", ".zip", ".3105", ".mp3", ".mp4",
                ".woff", ".woff2", ".ttf", ".otf",
            ))
            try:
                if is_binary:
                    content = _b64.b64encode(file_path.read_bytes()).decode("ascii")
                else:
                    content = file_path.read_text(encoding="utf-8")
            except Exception as exc:
                errors.append({"path": f["path"], "error": f"read failed: {exc}"})
                continue
            try:
                result = _push_one(f["path"], content)
                if result:
                    pushed_results.append({
                        "path": f["path"],
                        "commit_sha": result.get("commit_sha"),
                        "pr_url": result.get("pr_url"),
                    })
            except Exception as exc:
                errors.append({"path": f["path"], "error": str(exc)})

        # Lưu history
        append_history(ROOT, {
            "pushed_at": _now_iso(),
            "files_pushed": len(pushed_results),
            "files_failed": len(errors),
            "commit_sha": pushed_results[-1]["commit_sha"] if pushed_results else None,
            "diff_summary": {
                "added": len(diff["added"]),
                "modified": len(diff["modified"]),
                "deleted": len(diff["deleted"]),
            },
        })

        return jsonify({
            "ok": len(errors) == 0,
            "pushed": len(pushed_results),
            "errors": errors,
            "results": pushed_results,
            "workflow_note": "Sau khi push, workflow build-public.yml sẽ tự động rebuild GitHub Pages trong ~30-60s.",
        })

    @app.get("/api/sync/log")
    def sync_log():
        """Trả về lịch sử sync (20 entry gần nhất)."""
        from flask import jsonify
        state = read_sync_state(ROOT)
        return jsonify({
            "ok": True,
            "history": state.get("history", []),
        })
