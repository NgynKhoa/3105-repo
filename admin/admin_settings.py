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
