"""
config.py — Load config từ .env (không commit lên git) + defaults an toàn.

Triết lý bảo mật:
  - KHÔNG hardcode secret trong source code (secret phải ở .env).
  - Nếu thiếu secret → fail-fast lúc startup, không chạy với giá trị rỗng.
  - Cho phép dev override qua biến môi trường (VD export GITHUB_CLIENT_ID=...).

Load order (ưu tiên cao → thấp):
  1. Biến môi trường process
  2. File .env (cùng thư mục với admin/app.py)
  3. Default an toàn (chỉ cho non-secret values)
"""
from __future__ import annotations

import os
import pathlib
import secrets
from typing import Any


def _load_dotenv(path: pathlib.Path) -> None:
    """Minimal .env loader — không phụ thuộc thư viện python-dotenv.

    Format:
        KEY=value
        KEY="quoted value with spaces"
        # comment
    Hỗ trợ:
      - Dòng trống / comment (#)
      - Quote đơn/đôi
      - Escape \\ trong quote
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        # Không override biến môi trường đã có (ưu tiên env process hơn file)
        os.environ.setdefault(key, value)


# Load .env từ thư mục gốc repo (parent của admin/)
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_load_dotenv(_REPO_ROOT / ".env")


class Config:
    """Centralized config — đọc 1 lần lúc import."""

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.environ.get("GITHUB_CLIENT_ID", "").strip()
    GITHUB_CLIENT_SECRET: str = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
    OAUTH_CALLBACK_URL: str = os.environ.get(
        "OAUTH_CALLBACK_URL",
        "http://localhost:5050/auth/github/callback",
    ).strip()
    GITHUB_API_BASE: str = os.environ.get(
        "GITHUB_API_BASE", "https://api.github.com"
    ).strip()
    # Personal Access Token cho READ-ONLY requests (tăng rate limit từ 60/hr lên 5000/hr).
    # Set trong .env: GITHUB_PAT=ghp_xxxx
    # Dùng cho các public API: /api/public/admin-settings, /api/fetch-repo-json,
    # /api/public/raw-asset, /api/public/release — KHÔNG cần user OAuth login.
    GITHUB_PAT: str = os.environ.get("GITHUB_PAT", "").strip()
    OAUTH_SCOPES: str = "read:user public_repo"
    # - read:user: lấy username, avatar, email
    # - public_repo: push vào repo public (theo lựa chọn user)
    # KHÔNG bao gồm scope `repo` để tránh truy cập private repo mà user
    # không lường trước được. Nếu cần private repo → mở rộng sau.

    # Flask
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "").strip()
    FRONTEND_BASE_URL: str = os.environ.get(
        "FRONTEND_BASE_URL", "http://localhost:5050"
    ).strip()

    # Cache
    REPO_DISCOVERY_CACHE_TTL: int = int(os.environ.get("REPO_DISCOVERY_CACHE_TTL", "300"))

    # Cookie
    SESSION_COOKIE_NAME: str = "oauth_session"
    SESSION_COOKIE_HTTPONLY: bool = True   # JS không đọc được → chống XSS
    SESSION_COOKIE_SAMESITE: str = "Lax"  # chống CSRF cho top-level nav
    SESSION_COOKIE_SECURE: bool = False   # True nếu deploy HTTPS
    SESSION_COOKIE_MAX_AGE: int = 7 * 24 * 60 * 60  # 7 ngày

    @classmethod
    def is_oauth_configured(cls) -> bool:
        """True nếu GitHub OAuth đã setup (Client ID + Secret không rỗng)."""
        return bool(cls.GITHUB_CLIENT_ID) and bool(cls.GITHUB_CLIENT_SECRET)

    @classmethod
    def ensure_flask_secret(cls) -> str:
        """Trả về SECRET_KEY, tạo ephemeral nếu chưa có.

        Cảnh báo: ephemeral key sẽ reset session mỗi lần restart server.
        Chỉ dùng cho dev. Production phải set SECRET_KEY trong .env.
        """
        if cls.SECRET_KEY:
            return cls.SECRET_KEY
        key = secrets.token_urlsafe(32)
        cls.SECRET_KEY = key
        return key

    @classmethod
    def validate_for_runtime(cls) -> list[str]:
        """Trả về danh sách vấn đề cấu hình (rỗng = OK).

        Dùng để in ra console lúc Flask boot:
            for err in Config.validate_for_runtime():
                print(f"[config] ⚠ {err}")
        """
        issues: list[str] = []
        if not cls.is_oauth_configured():
            issues.append(
                "GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET chưa set → "
                "OAuth sẽ không hoạt động. Copy .env.example → .env và điền."
            )
        if not cls.SECRET_KEY:
            issues.append(
                "SECRET_KEY chưa set → session không persist qua restart. "
                "Generate: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if cls.SESSION_COOKIE_SECURE and cls.FRONTEND_BASE_URL.startswith("http://"):
            issues.append(
                "SESSION_COOKIE_SECURE=true nhưng FRONTEND_BASE_URL dùng http:// "
                "→ browser sẽ không gửi cookie. Bật HTTPS hoặc tắt SECURE."
            )
        return issues
