"""
admin_settings.py — Lưu settings riêng của admin vào GitHub repo của họ.

Mục đích:
  - Admin (login GitHub + owner of repo) có settings riêng biệt với user thường.
  - Settings được lưu vào file .3105/admin-settings.json trong repo của admin
    (commit lên GitHub → multi-device sync, không mất khi clear localStorage).
  - User thường KHÔNG BAO GIỜ touch file này.

API:
  GET  /api/admin-settings?slug=X     → trả JSON settings (từ GitHub) hoặc {}
  POST /api/admin-settings            → body {slug, settings} → push lên GitHub

Push strategy: dùng github_write.py (PR mode mặc định, hoặc direct mode).
Mặc định admin upload qua web → dùng PR mode cho an toàn (admin merge sau).
"""
from __future__ import annotations

import json
import time
from typing import Any

import requests
from flask import jsonify, request

from .auth import login_required, get_current_token, get_owned_repos as auth_get_owned_repos
from .config import Config
from .github_write import write_file as gh_write_file

ADMIN_SETTINGS_PATH = ".3105/admin-settings.json"
ADMIN_SETTINGS_DEFAULT: dict[str, Any] = {
    "rain_enabled": True,
    "heavy_rain": False,
    "dark_mode": True,
    "theme": "default",
    "transparency": 92,
    "shadow_theme": "default",
}


def _admin_settings_url(full_name: str, path: str) -> str:
    return f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/{path}"


def fetch_admin_settings(full_name: str, token: str) -> dict[str, Any]:
    """GET file .3105/admin-settings.json từ GitHub. Trả về {} nếu chưa có."""
    url = _admin_settings_url(full_name, ADMIN_SETTINGS_PATH)
    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
    except requests.RequestException:
        return {}
    if resp.status_code == 404:
        # File chưa tồn tại → trả default
        return dict(ADMIN_SETTINGS_DEFAULT)
    if resp.status_code != 200:
        return dict(ADMIN_SETTINGS_DEFAULT)
    try:
        import base64
        data = resp.json()
        raw = base64.b64decode(data.get("content", "")).decode("utf-8")
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return dict(ADMIN_SETTINGS_DEFAULT)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def register_admin_settings_routes(app):
    """Đăng ký routes /api/admin-settings trên Flask app."""

    @app.get("/api/admin-settings")
    @login_required
    def get_admin_settings():
        slug = request.args.get("slug", "").strip()
        if not slug:
            return jsonify({"ok": False, "error": "Thiếu slug"}), 400

        owned = auth_get_owned_repos()
        target = next((r for r in owned if r.get("slug") == slug), None)
        if not target:
            return jsonify({"ok": False, "error": "Bạn không phải owner"}), 403

        token = get_current_token()
        if not token:
            return jsonify({"ok": False, "error": "Session không có token"}), 401

        settings = fetch_admin_settings(target["full_name"], token)
        return jsonify({
            "ok": True,
            "slug": slug,
            "settings": settings,
            "source": "github",
            "path": ADMIN_SETTINGS_PATH,
        })

    @app.post("/api/admin-settings")
    @login_required
    def save_admin_settings():
        """Body: {slug, settings, mode?} → push lên GitHub."""
        data = request.get_json(silent=True) or {}
        slug = (data.get("slug") or "").strip()
        settings = data.get("settings")
        mode = (data.get("mode") or "pr").strip()

        if not slug or not isinstance(settings, dict):
            return jsonify({"ok": False, "error": "Thiếu slug hoặc settings"}), 400
        if mode not in ("pr", "direct"):
            return jsonify({"ok": False, "error": "mode không hợp lệ"}), 400

        owned = auth_get_owned_repos()
        target = next((r for r in owned if r.get("slug") == slug), None)
        if not target:
            return jsonify({"ok": False, "error": "Bạn không phải owner"}), 403

        token = get_current_token()
        if not token:
            return jsonify({"ok": False, "error": "Session không có token"}), 401

        try:
            content = json.dumps(settings, indent=2, ensure_ascii=False)
            result = gh_write_file(
                token=token,
                full_name=target["full_name"],
                path=ADMIN_SETTINGS_PATH,
                content=content,
                commit_message=f"chore(admin-settings): update settings via 3105 Builder",
                mode=mode,
            )
            return jsonify({"ok": True, **result})
        except Exception as e:
            app.logger.exception("save_admin_settings failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.post("/api/admin-settings-merge")
    @login_required
    def merge_admin_settings():
        """Body: {slug, patch, mode?} → merge `patch` vào file hiện tại rồi push.

        Khác với /api/admin-settings (ghi đè toàn bộ file): endpoint này
        1) fetch file hiện tại từ GitHub,
        2) shallow-merge `patch` (các key trùng sẽ bị ghi đè bởi patch),
        3) ghi full file trở lại.

        Fix cho bug cũ: mỗi lần UI thay đổi 1 setting, code frontend cũ gọi
        POST /api/admin-settings với payload CHỈ chứa 1 key → file trên
        GitHub mất hết các field khác. Endpoint này giữ nguyên các field
        không liên quan.
        """
        data = request.get_json(silent=True) or {}
        slug = (data.get("slug") or "").strip()
        patch = data.get("patch")
        mode = (data.get("mode") or "pr").strip()

        if not slug or not isinstance(patch, dict):
            return jsonify({"ok": False, "error": "Thiếu slug hoặc patch"}), 400
        if mode not in ("pr", "direct"):
            return jsonify({"ok": False, "error": "mode không hợp lệ"}), 400

        owned = auth_get_owned_repos()
        target = next((r for r in owned if r.get("slug") == slug), None)
        if not target:
            return jsonify({"ok": False, "error": "Bạn không phải owner"}), 403

        token = get_current_token()
        if not token:
            return jsonify({"ok": False, "error": "Session không có token"}), 401

        try:
            # Retry logic: nếu GitHub trả 409/422 (SHA conflict do race),
            # refetch rồi merge lại. Tối đa 3 lần.
            for attempt in range(3):
                current = fetch_admin_settings(target["full_name"], token)
                merged = dict(current or {})
                merged.update(patch)
                content = json.dumps(merged, indent=2, ensure_ascii=False)
                try:
                    result = gh_write_file(
                        token=token,
                        full_name=target["full_name"],
                        path=ADMIN_SETTINGS_PATH,
                        content=content,
                        commit_message=f"chore(admin-settings): merge via 3105 Builder",
                        mode=mode,
                    )
                    return jsonify({"ok": True, "settings": merged, **result})
                except RuntimeError as e:
                    err_msg = str(e)
                    # 409 conflict (SHA mismatch) hoặc 422 → refetch + retry
                    if "409" in err_msg or "422" in err_msg or "conflict" in err_msg.lower():
                        app.logger.warning(
                            "merge_admin_settings SHA conflict, retry %d/3", attempt + 1
                        )
                        continue
                    raise  # lỗi khác → bubble up
            return jsonify({"ok": False, "error": "Conflict sau 3 lần retry"}), 409
        except Exception as e:
            app.logger.exception("merge_admin_settings failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.post("/api/admin-settings-restore")
    @login_required
    def restore_admin_settings():
        """Nhận full localStorage dump từ browser → merge vào admin-settings.json → push.

        Body: {slug, localStorage: {key: value, ...}}
        Dùng khi user đã chỉnh Front Repo / Dashboard nhiều thứ trên máy mình
        nhưng chưa sync lên GitHub. Browser console paste:
          fetch('/api/admin-settings-restore',{method:'POST',
            headers:{'Content-Type':'application/json','Accept':'application/json'},
            credentials:'same-origin',
            body:JSON.stringify({slug:'demo',
              localStorage:Object.fromEntries(
                Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)])
              )
            })
          }).then(r=>r.json()).then(d=>d.ok?alert('OK: '+Object.keys(d.settings).length+' keys'):alert('FAIL: '+JSON.stringify(d.error)))
        """
        data = request.get_json(silent=True) or {}
        slug = (data.get("slug") or "").strip()
        ls_data = data.get("localStorage")

        if not slug or not isinstance(ls_data, dict):
            return jsonify({"ok": False, "error": "Thiếu slug hoặc localStorage"}), 400

        owned = auth_get_owned_repos()
        target = next((r for r in owned if r.get("slug") == slug), None)
        if not target:
            return jsonify({"ok": False, "error": "Bạn không phải owner"}), 403

        token = get_current_token()
        if not token:
            return jsonify({"ok": False, "error": "Session không có token"}), 401

        try:
            current = fetch_admin_settings(target["full_name"], token)
        except Exception:
            current = {}

        # Merge: giữ nguyên key cũ, thêm/cập nhật key mới từ localStorage
        merged = dict(current)
        for k, v in ls_data.items():
            # Chỉ merge các key có trong whitelist (tránh spam file)
            # Key format: repo_*, theme, shadowTheme, darkMode, transparency, bgImage,
            # admin_*, mp_*, rain*, dash_*, currentRepo, downloadMode, hideAdminBg
            if not isinstance(k, str):
                continue
            safe_key = k.strip()
            # Bỏ qua các key noise (không phải settings)
            noise_keys = {"currentRepo", "currentRepo_v2", "auth_token", "oauth_token",
                          "user_session", "XSRF_TOKEN", "sidebar_collapsed"}
            if safe_key in noise_keys:
                continue
            # Chỉ giữ key có prefix hợp lệ
            valid_prefixes = (
                "repo_", "admin_", "mp_", "dash_",
                "theme", "shadowTheme", "darkMode", "transparency", "bgImage",
                "rainEnabled", "heavyRain", "rain_volume",
                "downloadMode", "hideAdminBg", "currentRepo",
                "admin_playlist", "admin_nav_links",
            )
            if any(safe_key.startswith(p) for p in valid_prefixes):
                merged[safe_key] = v
            elif safe_key in ("theme", "shadowTheme", "darkMode", "transparency",
                              "rainEnabled", "heavyRain", "rain_volume",
                              "downloadMode", "hideAdminBg"):
                merged[safe_key] = v

        import json as _json, base64 as _base64, requests as _requests
        from .config import Config
        url = f"{Config.GITHUB_API_BASE}/repos/{target['full_name']}/contents/{ADMIN_SETTINGS_PATH}"
        resp = _requests.get(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "3105-repo-builder/1.0",
            "Authorization": f"Bearer {token}",
        }, timeout=15)
        sha = None
        if resp.status_code == 200:
            sha = resp.json().get("sha")
        content_str = _json.dumps(merged, indent=2, ensure_ascii=False)
        commit_body = {
            "message": f"chore(admin-settings): restore {len(merged)} keys from localStorage",
            "branch": target.get("default_branch", "main"),
            "content": _base64.b64encode(content_str.encode("utf-8")).decode("ascii"),
        }
        if sha:
            commit_body["sha"] = sha
        push_resp = _requests.put(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "3105-repo-builder/1.0",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=commit_body, timeout=30)
        if push_resp.status_code in (200, 201):
            return jsonify({"ok": True, "settings": merged,
                            "pushed": len(merged), "commit": push_resp.json().get("commit", {}).get("sha", "")[:8]})
        else:
            return jsonify({"ok": False, "error": push_resp.text[:200]}), 502
