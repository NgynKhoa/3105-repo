"""
auth.py — OAuth GitHub + session management + repo ownership discovery.

Module này cung cấp:
  - Blueprint `auth_bp` với routes:
      GET  /auth/github/login        → bắt đầu OAuth
      GET  /auth/github/callback     → GitHub redirect về (state verify + exchange code)
      GET  /auth/me                  → trả về thông tin user hiện tại (JSON)
      POST /auth/logout              → xoá session
  - `@login_required` decorator cho các endpoint yêu cầu đăng nhập
  - `@owner_required(slug)` decorator cho các endpoint cần quyền admin repo
  - `repo_discovery.scan_user_repos(token)` — scan repos của user, tìm repo có
    repo.json ở root, trả về list[RepoCandidate]

Bảo mật:
  - Access token KHÔNG BAO GIỜ trả về client. Chỉ set trong session server-side.
  - Session cookie HttpOnly + SameSite=Lax + Signed (Flask default với SECRET_KEY).
  - State parameter (CSRF) generated via secrets.token_urlsafe, lưu session,
    verify trước khi exchange code. State chỉ dùng 1 lần (consume trong callback).
  - Token exchange dùng Authorization header (không URL param) — chống log leak.
  - Rate-limit: GitHub OAuth API có rate limit 5000/h với user token, 60/h với
    unauthenticated. Discovery cache 5 phút/repo để tránh spam.

Repo discovery flow (chi tiết trong repo_discovery.py):
  1. GET /users/{username}/repos?per_page=100&type=owner (filter chỉ repo
     do user sở hữu, không bao gồm fork — fork có thể có repo.json nhưng
     admin thật là owner gốc).
  2. Với mỗi repo, thử GET contents ở nhiều path: repo.json, .3105/repo.json,
     config/repo.json, src/repo.json. Repo đầu tiên có file hợp lệ → candidate.
  3. Parse file → Schema: {slug, identifier, name, owner_github, created_at}.
     Cache kết quả 5 phút (in-memory + disk .oauth_cache/).
"""
from __future__ import annotations

import functools
import json
import os
import secrets
import time
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Any, Callable

import requests
from flask import (
    Blueprint, current_app, jsonify, redirect, request, session, url_for
)

from .config import Config

# -----------------------------------------------------------------------------
# Blueprint
# -----------------------------------------------------------------------------

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# -----------------------------------------------------------------------------
# Session keys (constants — typo-proof)
# -----------------------------------------------------------------------------

_SESSION_TOKEN = "gh_token"           # str — GitHub OAuth access token
_SESSION_USER = "gh_user"             # dict — {login, id, name, avatar_url}
_SESSION_OAUTH_STATE = "gh_oauth_state"   # str — CSRF state (1 lần dùng)
_SESSION_OWNED_REPOS = "gh_owned_repos"   # list[dict] — repo discovery cache


@dataclass
class GitHubUser:
    """Thông tin user sau khi OAuth thành công."""
    login: str
    id: int
    name: str | None = None
    avatar_url: str | None = None
    email: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# -----------------------------------------------------------------------------
# OAuth routes
# -----------------------------------------------------------------------------

@auth_bp.route("/github/login")
def github_login():
    """Bắt đầu OAuth flow — redirect user sang GitHub authorize page.

    Flow:
      1. Generate state ngẫu nhiên → lưu session.
      2. Build GitHub authorize URL với client_id, redirect_uri, scope, state.
      3. Redirect user sang GitHub.
    """
    if not Config.is_oauth_configured():
        return jsonify({
            "ok": False,
            "error": "OAuth chưa cấu hình. Set GITHUB_CLIENT_ID và GITHUB_CLIENT_SECRET trong .env",
        }), 503

      # State: chống CSRF, chỉ dùng 1 lần
    state = secrets.token_urlsafe(32)
    session[_SESSION_OAUTH_STATE] = state

    # Lưu query string gốc (vd ?slug=demo&theme=dark) để sau login redirect về đúng trang.
    # Chỉ giữ slug ( quan trọng nhất ), bỏ auth/logout/query params khác.
    from urllib.parse import urlencode, parse_qs
    raw_qs = request.query_string.decode()
    safe_params = {}
    for k, v in parse_qs(raw_qs).items():
        # Chỉ giữ các param an toàn (slug là quan trọng nhất)
        if k not in ('auth', 'logout', 'code', 'state') and v:
            safe_params[k] = v[0]
    session['oauth_return_params'] = safe_params

    params = {
        "client_id": Config.GITHUB_CLIENT_ID,
        "redirect_uri": Config.OAUTH_CALLBACK_URL,
        "scope": Config.OAUTH_SCOPES,
        "state": state,
        "allow_signup": "false",  # chỉ user GitHub đã có sẵn
    }
    authorize_url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return redirect(authorize_url)


@auth_bp.route("/github/callback")
def github_callback():
    """GitHub redirect user về đây sau khi authorize.

    Flow:
      1. Verify `state` khớp với session → chống CSRF.
      2. Lấy `code` từ query string.
      3. Exchange code → access_token (POST /login/oauth/access_token).
      4. Lấy user info từ access_token (GET /user).
      5. Lưu token + user vào session.
      6. Redirect về Front Repo với ?auth=ok query.
    """
    # Verify state
    expected_state = session.pop(_SESSION_OAUTH_STATE, None)
    received_state = request.args.get("state", "")
    if not expected_state or not secrets.compare_digest(expected_state, received_state):
        return _oauth_error_page("State mismatch — có thể là CSRF attack. Vui lòng thử lại.")

    code = request.args.get("code")
    error = request.args.get("error")
    if error:
        return _oauth_error_page(f"GitHub trả về lỗi: {error}")

    if not code:
        return _oauth_error_page("Thiếu authorization code từ GitHub.")

    # Exchange code → access_token
    try:
        token_resp = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": Config.GITHUB_CLIENT_ID,
                "client_secret": Config.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": Config.OAUTH_CALLBACK_URL,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except requests.RequestException as e:
        return _oauth_error_page(f"Không kết nối được GitHub: {e}")

    access_token = token_data.get("access_token")
    if not access_token:
        err_desc = token_data.get("error_description", "Unknown error")
        return _oauth_error_page(f"GitHub không cấp access_token: {err_desc}")

    # Lấy user info
    user, err = _fetch_github_user(access_token)
    if err or user is None:
        return _oauth_error_page(f"Không lấy được thông tin user: {err}")

    # Lưu session
    session[_SESSION_TOKEN] = access_token
    session[_SESSION_USER] = user.to_dict()
    # Clear stale discovery cache (user vừa login có thể có repo mới)
    session.pop(_SESSION_OWNED_REPOS, None)

    # Redirect về Front Repo — sử dụng URL an toàn (chỉ path, không host)
    # để tránh open redirect nếu OAUTH_CALLBACK_URL bị spoof.
    # Đồng thời restore query params đã lưu trước login (vd ?slug=demo).
    base = Config.FRONTEND_BASE_URL.rstrip("/")
    safe_params = session.pop('oauth_return_params', {})
    qs = ("?" + urllib.parse.urlencode(safe_params)) if safe_params else ""
    auth_qs = f"auth=ok&user={urllib.parse.quote(user.login)}"
    return redirect(f"{base}/{qs}{('&' if qs else '?')}{auth_qs}")


@auth_bp.route("/me")
def auth_me():
    """Trả về thông tin user hiện tại (JSON) cho Front Repo.

    Response shape:
      {
        "authenticated": bool,
        "user": {login, name, avatar_url, ...} | null,
        "is_owner_of": str | null,  # slug repo mà user này là owner (nếu có)
        "repos": [RepoCandidate, ...]   # list các repo user có repo.json
      }

    Front Repo dùng `is_owner_of` để apply RBAC (hiện nút Sửa/Xóa, Admin link).
    """
    if not is_authenticated():
        # Anonymous: vẫn trả current_repo từ local repo file (nếu có)
        # để Front Repo biết owner_github cho lookup raw-asset / admin-settings.
        current_slug = request.args.get("slug")
        current_repo_data = None
        if current_slug:
            try:
                # Lazy import tránh circular
                from .repo_discovery import find_repo_file_for_slug
                info = find_repo_file_for_slug(current_slug)
                if info:
                    current_repo_data = {
                        "slug": info.get("slug"),
                        "identifier": info.get("identifier"),
                        "owner_github": info.get("owner_github"),
                        "repo_json_path": info.get("repo_json_path"),
                        "default_branch": info.get("default_branch", "main"),
                    }
            except Exception as e:
                current_app.logger.debug(f"anon current_repo lookup failed: {e}")

        return jsonify({
            "authenticated": False,
            "user": None,
            "is_owner_of": None,
            "repos": [],
            "current_repo": current_repo_data,
            "releases": [],
            "download_paths": [],
            "download_mode": "auto",
        })

    user = session.get(_SESSION_USER) or {}
    repos = get_owned_repos()
    # Tìm repo trùng với slug đang xem (nếu Front Repo truyền slug qua query)
    current_slug = request.args.get("slug")
    is_owner_of = None
    current_repo_data = None
    if current_slug:
        for r in repos:
            if r.get("slug") == current_slug:
                is_owner_of = current_slug
                current_repo_data = r
                break

    return jsonify({
        "authenticated": True,
        "user": user,
        "is_owner_of": is_owner_of,
        "repos": repos,
        "current_repo": current_repo_data,
        # releases[] từ repo.json của repo đang xem (nếu có)
        # Front Repo dùng để map package_id → download_url cho nút Tải xuống.
        "releases": (current_repo_data or {}).get("releases", []),
        # download_paths[] từ repo.json (raw file .3105 trong repo)
        "download_paths": (current_repo_data or {}).get("download_paths", []),
        # download_mode: "raw" | "releases" | "auto"
        "download_mode": (current_repo_data or {}).get("download_mode", "auto"),
        "repo_json_path": (current_repo_data or {}).get("repo_json_path", ""),
    })


@auth_bp.route("/logout", methods=["POST", "GET"])
def auth_logout():
    """Xoá session, redirect về Front Repo."""
    session.pop(_SESSION_TOKEN, None)
    session.pop(_SESSION_USER, None)
    session.pop(_SESSION_OWNED_REPOS, None)
    if request.method == "POST":
        return jsonify({"ok": True})
    base = Config.FRONTEND_BASE_URL.rstrip("/")
    return redirect(f"{base}/?auth=logout")


# -----------------------------------------------------------------------------
# Decorators
# -----------------------------------------------------------------------------

def login_required(fn: Callable) -> Callable:
    """Decorator: yêu cầu user đã đăng nhập. Trả 401 JSON nếu không."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"ok": False, "error": "Chưa đăng nhập", "login_url": url_for("auth.github_login", _external=True)}), 401
        return fn(*args, **kwargs)
    return wrapper


def owner_required(slug_param: str = "slug") -> Callable:
    """Decorator: yêu cầu user là owner của repo có slug trong URL.

    Usage:
        @app.route("/api/repo/<slug>/packages", methods=["POST"])
        @owner_required(slug_param="slug")
        def add_package(slug):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            slug = kwargs.get(slug_param)
            if not slug:
                return jsonify({"ok": False, "error": "Thiếu slug"}), 400
            owned = get_owned_repos()
            if not any(r.get("slug") == slug for r in owned):
                return jsonify({"ok": False, "error": f"Bạn không phải owner của repo '{slug}'"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def is_authenticated() -> bool:
    """True nếu session hiện tại có token + user info."""
    return bool(session.get(_SESSION_TOKEN)) and bool(session.get(_SESSION_USER))


def get_current_token() -> str | None:
    """Lấy GitHub access token của user hiện tại. KHÔNG return ra ngoài API JSON."""
    return session.get(_SESSION_TOKEN)


def get_current_user() -> GitHubUser | None:
    """Lấy thông tin user hiện tại (không có token)."""
    data = session.get(_SESSION_USER)
    if not data:
        return None
    return GitHubUser(**data)


def get_owned_repos(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Trả về list repo mà user hiện tại có repo.json (admin candidates).

    Cached trong session + on-disk cache file (TTL = REPO_DISCOVERY_CACHE_TTL).
    Cache key: login của user hiện tại.
    """
    if not is_authenticated():
        return []

    user = get_current_user()
    if not user:
        return []

    cache_key = f"repos:{user.login}"
    cached = session.get(_SESSION_OWNED_REPOS)
    cache_age_key = f"repos_ts:{user.login}"
    cached_ts = session.get(cache_age_key, 0)

    now = time.time()
    if not force_refresh and cached is not None and (now - cached_ts) < Config.REPO_DISCOVERY_CACHE_TTL:
        return cached

    # === Disk cache (persist qua server restart) ===
    # Tránh scan lại 20-30s khi user vừa đăng nhập mà session bị mất do restart.
    if not force_refresh:
        disk_cached, disk_ts = _load_disk_repo_cache(user.login)
        if disk_cached is not None and (now - disk_ts) < Config.REPO_DISCOVERY_CACHE_TTL:
            session[_SESSION_OWNED_REPOS] = disk_cached
            session[cache_age_key] = disk_ts
            return disk_cached

    # Refresh
    from .repo_discovery import scan_user_repos  # local import để tránh circular
    token = get_current_token()
    if not token:
        return []
    try:
        repos = scan_user_repos(token, login=user.login)
        session[_SESSION_OWNED_REPOS] = repos
        session[cache_age_key] = now
        _save_disk_repo_cache(user.login, repos, now)
        return repos
    except Exception as e:
        current_app.logger.warning(f"repo discovery failed for {user.login}: {e}")
        return cached or []


# -----------------------------------------------------------------------------
# Internal
# -----------------------------------------------------------------------------

def _fetch_github_user(token: str) -> tuple[GitHubUser | None, str | None]:
    """GET /user với token → trả về (GitHubUser, error_msg)."""
    try:
        resp = requests.get(
            f"{Config.GITHUB_API_BASE}/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )
        if resp.status_code == 401:
            return None, "Token không hợp lệ hoặc đã hết hạn"
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, str(e)

    data = resp.json()
    return GitHubUser(
        login=data.get("login", ""),
        id=data.get("id", 0),
        name=data.get("name"),
        avatar_url=data.get("avatar_url"),
        email=data.get("email"),
    ), None


# -----------------------------------------------------------------------------
# Disk cache cho repo discovery (persist qua server restart)
# -----------------------------------------------------------------------------
import json as _json_disk
import os
import hashlib

_HASHLIB = hashlib

_DISK_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".oauth_cache")


def _disk_cache_path(login: str) -> str:
    """Trả về path file cache cho user (hash login để safe filename)."""
    os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
    h = hashlib.sha1(login.lower().encode("utf-8")).hexdigest()[:16]
    return os.path.join(_DISK_CACHE_DIR, f"repos_{h}.json")


def _load_disk_repo_cache(login: str):
    """Đọc cache từ disk. Trả về (repos, ts) hoặc (None, 0) nếu không có."""
    path = _disk_cache_path(login)
    if not os.path.exists(path):
        return None, 0
    try:
        with open(path, encoding="utf-8") as f:
            payload = _json_disk.load(f)
        return payload.get("repos"), float(payload.get("ts", 0))
    except Exception:
        return None, 0


def _save_disk_repo_cache(login: str, repos, ts: float) -> None:
    """Lưu cache xuống disk (best-effort, fail silent)."""
    try:
        path = _disk_cache_path(login)
        with open(path, "w", encoding="utf-8") as f:
            _json_disk.dump({"repos": repos, "ts": ts, "login": login}, f)
    except Exception:
        pass


def _oauth_error_page(message: str):
    """Trang HTML đơn giản khi OAuth fail. Frontend có thể đọc ?error= để
    hiển thị toast, nhưng nếu user mở trực tiếp URL callback thì trả HTML
    thân thiện thay vì JSON."""
    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>OAuth Error</title>
  <style>
    body {{
      background: #0a0e1a;
      color: #ff4040;
      font-family: 'Be Vietnam Pro', 'Fira Code', monospace;
      padding: 40px;
      max-width: 600px;
      margin: 0 auto;
    }}
    h1 {{ font-size: 18px; margin-bottom: 16px; }}
    p {{ color: #c0d8cc; line-height: 1.6; }}
    a {{
      display: inline-block;
      margin-top: 16px;
      padding: 8px 16px;
      background: #39ff14;
      color: #0a0e1a;
      text-decoration: none;
      border-radius: 4px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <h1>❌ Đăng nhập GitHub thất bại</h1>
  <p>{message}</p>
  <a href="{Config.FRONTEND_BASE_URL}/">← Quay lại Front Repo</a>
</body>
</html>"""
    return html, 400
