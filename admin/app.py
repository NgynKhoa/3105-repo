#!/usr/bin/env python3
"""Local-only admin tool để quản lý các repo 3105 thay vì sửa YAML tay.

Cách chạy:
    pip install -r admin/requirements.txt
    python admin/app.py
Mở trình duyệt: http://127.0.0.1:5050

Biến môi trường:
    PORT               Cổng HTTP (mặc định 5050)
    AUTO_OPEN_BROWSER  Tự mở trình duyệt khi khởi động (mặc định "1",
                       đặt "0" để tắt — hữu ích khi chạy trong container/CI)
"""

from __future__ import annotations

import hashlib
import sys
import pathlib

# Thêm thư mục admin/ vào sys.path để `import fe_checklist` hoạt động
# bất kể user chạy `python admin/app.py` hay `python -m admin.app`.
_ADMIN_DIR = pathlib.Path(__file__).resolve().parent
if str(_ADMIN_DIR) not in sys.path:
    sys.path.insert(0, str(_ADMIN_DIR))

import json
import os
import pathlib
import re
import shutil
import sys
import threading
import uuid
import webbrowser
import datetime
from typing import Any

import yaml
from flask import Flask, abort, jsonify, render_template, request, send_from_directory, session

# Load .env file (nếu có) — đọc trước khi import Config
# Try python-dotenv first, fallback to manual parser
_env_loaded = False
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        _load_dotenv(_env_path, override=False)
        _env_loaded = True
        print(f"[env] Loaded .env via python-dotenv from {_env_path}")
except ImportError:
    # Fallback: manual parser (simple KEY=VALUE format)
    _env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        try:
            for _line in _env_path.read_text(encoding="utf-8").splitlines():
                _line = _line.strip()
                if not _line or _line.startswith("#"):
                    continue
                if "=" not in _line:
                    continue
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip()
                # Strip surrounding quotes
                if (_v.startswith('"') and _v.endswith('"')) or (_v.startswith("'") and _v.endswith("'")):
                    _v = _v[1:-1]
                if _k and _k not in os.environ:  # process env wins
                    os.environ[_k] = _v
            _env_loaded = True
            print(f"[env] Loaded .env manually (no python-dotenv) from {_env_path}")
        except Exception as _e:
            print(f"[env] Failed to load .env: {_e}")

if not _env_loaded:
    print("[env] No .env loaded; relying on process env vars")

# Import config + auth blueprint
from .config import Config
from .auth import auth_bp, login_required, owner_required, is_authenticated
from .auth import get_owned_repos as auth_get_owned_repos
from .github_write import write_file as gh_write_file, _validate_inputs
from .admin_settings import register_admin_settings_routes
from .github_release import (
    create_or_get_release, upload_release_asset,
    find_release_for_package,
)
from .github_raw import register_raw_routes
from .fetch_repo_json import register_fetch_repo_json


# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORIES_DIR = ROOT / "repositories"
SOURCES_FILE = ROOT / "sources.json"

# Danh sách iOS rule dùng chung - tái sử dụng cho mọi package.
# Nếu cần thay đổi OS, sửa ở đây và restart tool.
DEFAULT_OS_RULES: list[dict[str, Any]] = [
    {"minimum": "17.0", "maximum": "18.7.1"},
    {"minimum": "26.0", "maximum": "26.6.1"},
    {
        "minimum": "27.0",
        "maximum": "27.0",
        "builds": ["24A5355q", "24A5370h", "24A5380h", "24A5390f"],
    },
]

# Screenshots mặc định dùng chung — nếu repo có bộ ảnh khác thì anchor
# sẽ được sinh tự động theo danh sách được phát hiện.
DEFAULT_SCREENSHOTS: list[str] = [
    "assets/preview/preview-first.png",
    "assets/preview/preview-second.png",
    "assets/preview/preview-third.png",
    "assets/preview/preview-fourth.png",
]

# Anchor name sẽ được dùng trong YAML
ANCHOR_OS_RULES = "os_rules"
ANCHOR_SCREENS = "screens"

# Danh sách category gợi ý cho dropdown.
CATEGORY_OPTIONS = [
    "Customization",
    "Enhancement",
    "Wallpaper",
    "Dialer",
    "Display",
    "Utility",
    "Game",
]

# Regex dùng để validate identifier (package và repo đều dùng chung).
IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")

app = Flask(__name__, template_folder="templates", static_folder="static")
# Giới hạn upload: 95MB mỗi file
# Lưu ý: GitHub hard-blocks push nếu file >= 100MB, nên để dưới 100MB
app.config["MAX_CONTENT_LENGTH"] = 95 * 1024 * 1024

# ============================================================================
# Flask session config + OAuth blueprint
# ============================================================================
# SECRET_KEY dùng để ký session cookie (HttpOnly + SameSite=Lax).
# Nếu chưa set trong .env → tạo ephemeral key (chỉ OK cho dev, không persist).
app.config["SECRET_KEY"] = Config.ensure_flask_secret()
app.config["SESSION_COOKIE_NAME"] = Config.SESSION_COOKIE_NAME
app.config["SESSION_COOKIE_HTTPONLY"] = Config.SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SAMESITE"] = Config.SESSION_COOKIE_SAMESITE
app.config["SESSION_COOKIE_SECURE"] = Config.SESSION_COOKIE_SECURE
app.config["SESSION_COOKIE_MAX_AGE"] = Config.SESSION_COOKIE_MAX_AGE
app.config["PERMANENT_SESSION_LIFETIME"] = Config.SESSION_COOKIE_MAX_AGE

app.register_blueprint(auth_bp)
register_admin_settings_routes(app)
register_raw_routes(app)
register_fetch_repo_json(app)

# In cảnh báo cấu hình (nếu có) ngay lúc boot
for _issue in Config.validate_for_runtime():
    print(f"[config] ⚠ {_issue}", flush=True)
print(
    f"[config] OAuth GitHub: "
    f"{'ENABLED' if Config.is_oauth_configured() else 'DISABLED — set GITHUB_CLIENT_ID/SECRET in .env'}",
    flush=True,
)


# ---------------------------------------------------------------------------
# Helper: làm việc với repo trên đĩa
# ---------------------------------------------------------------------------

def _safe_repo_name(name: str) -> str:
    """Đảm bảo tên repo không chứa ký tự lạ để tránh path traversal."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
        abort(400, description=f"Invalid repo name: {name!r}")
    return name


def list_repositories() -> list[str]:
    """Liệt kê các repo con dưới thư mục `repositories/`."""
    if not REPOSITORIES_DIR.is_dir():
        return []
    return sorted(p.name for p in REPOSITORIES_DIR.iterdir() if p.is_dir())


def repo_paths(repo: str) -> dict[str, pathlib.Path]:
    p = REPOSITORIES_DIR / _safe_repo_name(repo)
    if not p.is_dir():
        abort(404, description=f"Repository not found: {repo}")
    return {
        "root": p,
        "yml": p / "repo.yml",
        "json": p / "repo.json",
        "assets": p / "assets",
        "packages": p / "packages",
    }


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    """Đọc YAML, trả về dict rỗng nếu file chưa tồn tại."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


# ---------------------------------------------------------------------------
# Helper: phát hiện anchor dùng chung
# ---------------------------------------------------------------------------

def _normalize_os(rules: Any) -> list[dict[str, Any]] | None:
    """Trả về list rule nếu khớp DEFAULT_OS_RULES, ngược lại None.

    Hỗ trợ trường hợp YAML parse được nhưng thiếu field optional.
    """
    if not isinstance(rules, list) or len(rules) != len(DEFAULT_OS_RULES):
        return None
    for got, want in zip(rules, DEFAULT_OS_RULES):
        if not isinstance(got, dict):
            return None
        if got.get("minimum") != want["minimum"]:
            return None
        if got.get("maximum") != want["maximum"]:
            return None
        if list(got.get("builds") or []) != list(want.get("builds") or []):
            return None
    return [dict(rule) for rule in rules]


def detect_anchor_groups(
    raw_packages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]] | None, list[str] | None]:
    """Tìm danh sách OS / screenshots xuất hiện trong >= 50% package.

    Trả về (os_rules_for_anchor, screenshots_for_anchor). Nếu không đủ phổ biến,
    trả về (None, None) — lúc đó tool sẽ ghi đầy đủ cho từng package.

    Ngưỡng 50% giúp: 1 package "lạc" không phá vỡ anchor; 2/3 anchor vẫn tạo được.
    """
    if not raw_packages:
        return None, None

    # OS rules
    os_counts: dict[str, int] = {}
    os_payloads: dict[str, list[dict[str, Any]]] = {}
    for pkg in raw_packages:
        rules = pkg.get("supportedOS")
        if not isinstance(rules, list):
            continue
        key = json.dumps(rules, sort_keys=True, ensure_ascii=False)
        os_counts[key] = os_counts.get(key, 0) + 1
        os_payloads[key] = rules

    threshold = max(1, len(raw_packages) // 2)
    common_os: list[dict[str, Any]] | None = None
    for key, count in os_counts.items():
        if count >= threshold and _normalize_os(json.loads(key)) is not None:
            common_os = json.loads(key)
            break

    # Screenshots
    screen_counts: dict[str, int] = {}
    screen_payloads: dict[str, list[str]] = {}
    for pkg in raw_packages:
        shots = pkg.get("screenshots")
        if not isinstance(shots, list) or not shots:
            continue
        key = json.dumps(shots, ensure_ascii=False)
        screen_counts[key] = screen_counts.get(key, 0) + 1
        screen_payloads[key] = shots

    common_screens: list[str] | None = None
    for key, count in screen_counts.items():
        if count >= threshold:
            common_screens = screen_payloads[key]
            break

    return common_os, common_screens


# ---------------------------------------------------------------------------
# Helper: ghi YAML với anchor
# ---------------------------------------------------------------------------

def _yaml_scalar(value: Any, force_quoted: bool = False) -> str:
    """Quote chuỗi nếu có ký tự đặc biệt hoặc force_quoted=True.

    force_quoted dùng cho password/identifier/version để luôn giữ kiểu string.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Chuỗi số (password) hoặc force_quoted → bắt buộc quote
        needs_quote = force_quoted or value.isdigit()
        if not needs_quote:
            needs_quote = any(
                ch in value for ch in [":", "#", "&", "*", "!", "|", ">", "%", "@", "`", '"', "'", "\n"]
            )
        if needs_quote:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value
    return str(value)


def _render_block(parent_indent: str, key: str, text: str | None, lines: list[str]) -> None:
    """Ghi một YAML literal block (`|`) cho field `key` ở indent cha.

    `parent_indent` là indent của block cha (vd: "    " cho key trong list item).
    Block literal phải có indent nội dung > indent key. Ta dùng:
      - key:        parent_indent + key
      - dấu `|`:    cùng cột với key
      - nội dung:   parent_indent + 2 spaces (sâu hơn key 2 spaces)

    Nếu text rỗng / None → bỏ qua.
    Nếu text chỉ có 1 dòng → ghi flow scalar để YAML gọn.
    """
    if text is None:
        return
    text = str(text)
    lines_in_text = text.splitlines()
    if not lines_in_text:
        return
    if len(lines_in_text) == 1:
        lines.append(f"{parent_indent}{key}: {_yaml_scalar(text)}")
        return
    block_indent = parent_indent + "  "
    lines.append(f"{parent_indent}{key}: |")
    for line in lines_in_text:
        lines.append(f"{block_indent}{line}")


def _render_package_yaml(
    pkg: dict[str, Any],
    *,
    use_anchor_os: bool,
    use_anchor_screens: bool,
    anchor_os: str = ANCHOR_OS_RULES,
    anchor_screens: str = ANCHOR_SCREENS,
) -> list[str]:
    """Render một package ra danh sách các dòng YAML.

    Khi `use_anchor_*` True, field tương ứng sẽ ghi `*anchor_name` thay vì
    liệt kê đầy đủ — giữ file YAML gọn và dễ đọc.
    """
    lines: list[str] = []
    identifier = pkg.get("identifier", "unknown")
    lines.append(f"  # ----- {identifier} -----")
    lines.append(f"  - identifier: {_yaml_scalar(pkg.get('identifier', ''))}")
    lines.append(f"    name: {_yaml_scalar(pkg.get('name', ''))}")
    if pkg.get("author"):
        lines.append(f"    author: {_yaml_scalar(pkg['author'])}")
    if pkg.get("version"):
        lines.append(f"    version: {_yaml_scalar(pkg['version'])}")
    if pkg.get("summary"):
        lines.append(f"    summary: {_yaml_scalar(pkg['summary'])}")
    if pkg.get("password") is not None and str(pkg["password"]) != "":
        # Password luôn phải là string để tránh trường hợp YAML gốc ghi số không quote.
        lines.append(f'    password: {_yaml_scalar(str(pkg["password"]), force_quoted=True)}')

    if pkg.get("category"):
        lines.append(f"    category: {_yaml_scalar(pkg['category'])}")
    tags = pkg.get("tags") or []
    if tags:
        lines.append(f"    tags: [{', '.join(str(t) for t in tags)}]")

    if pkg.get("publishedAt"):
        lines.append(f"    publishedAt: {_yaml_scalar(pkg['publishedAt'])}")
    if pkg.get("kind"):
        lines.append(f"    kind: {_yaml_scalar(pkg['kind'])}")

    if pkg.get("icon"):
        lines.append(f"    icon: {pkg['icon']}")
    if pkg.get("banner"):
        lines.append(f"    banner: {pkg['banner']}")

    # Screenshots: anchor hoặc liệt kê
    screenshots = pkg.get("screenshots") or []
    if screenshots:
        if use_anchor_screens:
            lines.append(f"    screenshots: *{anchor_screens}")
        else:
            lines.append("    screenshots:")
            for shot in screenshots:
                lines.append(f"      - {shot}")

    if pkg.get("download"):
        lines.append(f"    download: {pkg['download']}")
    if pkg.get("sha256"):
        lines.append(f"    sha256: {pkg['sha256']}")
    if pkg.get("size") is not None:
        lines.append(f"    size: {pkg['size']}")

    # supportedOS: nếu use_anchor_os thì dùng anchor; nếu không thì ghi DEFAULT_OS_RULES
    # để đảm bảo file YAML luôn có OS hợp lệ, không phụ thuộc vào supportedOS
    # có thể rỗng/sai trong dữ liệu gửi lên.
    # Fix bug trước đây: nếu supportedOS chỉ có 1 rule với minimum="17" & maximum="0"
    # (giá trị default rỗng từ form khi user chưa nhập), file YAML bị ghi sai.
    if use_anchor_os:
        os_rules = DEFAULT_OS_RULES
    else:
        pkg_os = pkg.get("supportedOS")
        is_broken_single = (
            isinstance(pkg_os, list)
            and len(pkg_os) == 1
            and isinstance(pkg_os[0], dict)
            and pkg_os[0].get("minimum") in ("17", "17.0")
            and pkg_os[0].get("maximum") in ("0", "0.0")
        )
        if is_broken_single:
            os_rules = DEFAULT_OS_RULES
        else:
            os_rules = pkg_os or DEFAULT_OS_RULES
    if use_anchor_os:
        lines.append(f"    supportedOS: *{anchor_os}")
    else:
        lines.append("    supportedOS:")
        for rule in os_rules:
            lines.append(f"      - minimum: \"{rule['minimum']}\"")
            lines.append(f"        maximum: \"{rule['maximum']}\"")
            if rule.get("builds"):
                lines.append(f"        builds: {json.dumps(rule['builds'], ensure_ascii=False)}")

    lines.append(f"    featured: {str(bool(pkg.get('featured', False))).lower()}")
    lines.append(f"    isPrivate: {str(bool(pkg.get('isPrivate', False))).lower()}")

    # description / changelog: chỉ ghi nếu có nội dung
    _render_block("    ", "description", pkg.get("description"), lines)
    _render_block("    ", "changelog", pkg.get("changelog"), lines)

    return lines


def save_yaml(
    path: pathlib.Path,
    data: dict[str, Any],
    *,
    packages_meta: list[dict[str, Any]] | None = None,
) -> None:
    """Ghi YAML với anchor `&os_rules` / `&screens` khi có thể.

    `packages_meta` là danh sách các cờ cùng index với `data["packages"]`,
    chứa các key:
      - use_anchor_os (bool): True nếu package này dùng anchor *os_rules
      - use_anchor_screens (bool): True nếu dùng anchor *screens
      - shared_os (list, optional): danh sách OS rule chung để anchor
      - shared_screens (list, optional): danh sách screenshot chung để anchor
    """
    lines: list[str] = []

    # Không tạo anchor ở root YAML (sẽ sinh key `shared_os` / `shared_screens`
    # trong JSON sau khi build → lỗi schema app 3105).
    # Mỗi package sẽ được ghi screenshots / supportedOS đầy đủ.

    # ---- THÔNG TIN CHUNG ----
    lines.append("# ==========================================")
    lines.append("# THÔNG TIN CHUNG CỦA REPO")
    lines.append("# ==========================================")
    lines.append("")

    for key in ("schemaVersion", "identifier", "name"):
        if key in data and data[key] is not None:
            lines.append(f"{key}: {_yaml_scalar(data[key])}")
    if "description" in data and data["description"]:
        lines.append(f"description: {_yaml_scalar(data['description'])}")
    if "icon" in data:
        lines.append(f"icon: {data['icon']}")
    if "accentColor" in data:
        lines.append(f"accentColor: {_yaml_scalar(data['accentColor'])}")
    lines.append("")

    # ---- ANCHORS cho shared screenshots / supportedOS ----
    # Định nghĩa anchor ở root YAML dưới key hidden (prefix `_`) để app 3105 không đọc.
    packages = data.get("packages") or []
    shared_screens = None
    shared_os = None
    if packages_meta and len(packages_meta) == len(packages):
        any_screens = any(bool(m.get("use_anchor_screens")) for m in packages_meta)
        any_os = any(bool(m.get("use_anchor_os")) for m in packages_meta)
        if any_screens:
            shared_screens = DEFAULT_SCREENSHOTS
        if any_os:
            shared_os = DEFAULT_OS_RULES

    if shared_screens is not None:
        lines.append(f"_shared_screens: &{ANCHOR_SCREENS}")
        for s in shared_screens:
            lines.append(f"  - {s}")
        lines.append("")
    if shared_os is not None:
        lines.append(f"_shared_os_rules: &{ANCHOR_OS_RULES}")
        for rule in shared_os:
            lines.append(f"  - minimum: \"{rule['minimum']}\"")
            lines.append(f"    maximum: \"{rule['maximum']}\"")
        lines.append("")

    # ---- DANH SÁCH PACKAGES ----
    lines.append("# ==========================================")
    lines.append("# DANH SÁCH PACKAGES")
    lines.append("# ==========================================")
    lines.append("")
    lines.append("packages:")
    for idx, pkg in enumerate(packages):
        # Luôn ghi đầy đủ screenshots + supportedOS cho mỗi package
        # để JSON xuất ra không phụ thuộc anchor ở root.
        meta = packages_meta[idx] if packages_meta and idx < len(packages_meta) else {}
        lines.extend(
            _render_package_yaml(
                pkg,
                use_anchor_os=bool(meta.get("use_anchor_os")),
                use_anchor_screens=bool(meta.get("use_anchor_screens")),
            )
        )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Helper: SHA-256 + size
# ---------------------------------------------------------------------------

def hash_file(path: pathlib.Path) -> tuple[str, int]:
    """Trả về (sha256_hex, size_bytes) của file trên đĩa."""
    if not path.is_file():
        abort(404, description=f"File not found: {path}")
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest().upper(), size


# ---------------------------------------------------------------------------
# Helper: scan asset & package files
# ---------------------------------------------------------------------------

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic"}
PACKAGE_EXT = {".3105", ".3105pass", ".tendies"}


def scan_files(directory: pathlib.Path, exts: set[str]) -> list[str]:
    """Trả về đường dẫn tương đối so với repo root (vd: assets/foo.png)."""
    if not directory.is_dir():
        return []
    result: list[str] = []
    repo_root = REPOSITORIES_DIR.parent  # = ROOT
    for f in sorted(directory.rglob("*")):
        if f.is_file() and f.suffix.lower() in exts:
            rel = f.relative_to(repo_root).as_posix()
            # rel là "repositories/<repo>/assets/..." — bỏ 2 phần đầu
            parts = rel.split("/")
            if len(parts) >= 3:
                result.append("/".join(parts[2:]))
    return result


# ---------------------------------------------------------------------------
# Routes - trang web
# ---------------------------------------------------------------------------

@app.after_request
def add_no_cache_headers(response):
    # Trang HTML cần luôn fresh — đặc biệt Front Repo có dynamic-fit JS
    # chạy renderPackages/Blog với MAX_PKG/MAX_BLOG mới, nếu browser cache
    # phiên bản cũ sẽ thấy sai số item/trang.
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


@app.route("/")
def index():
    import os as _os
    bootstrap_js = (
        f"window.CATEGORIES = {json.dumps(CATEGORY_OPTIONS)};\n"
        f"window.DEFAULT_OS_RULES = {json.dumps(DEFAULT_OS_RULES)};\n"
        f"window.DEFAULT_SCREENSHOTS = {json.dumps(DEFAULT_SCREENSHOTS)};\n"
        # Inject owner + repo cho local dev — anonymous user cần biết
        # để fetch raw-asset / admin-settings từ GitHub.
        f"window.PUBLIC_REPO_OWNER_GITHUB = {_os.environ.get('GITHUB_DEFAULT_OWNER', 'NgynKhoa')!r};\n"
        f"window.PUBLIC_REPO_NAME = {_os.environ.get('GITHUB_REPO_NAME', '3105-repo')!r};\n"
    )
    return render_template(
        "index.html",
        bootstrap_js=bootstrap_js,
        cache_version=45,
    )


@app.route("/blog")
@app.route("/blog/<int:post_id>")
def blog_page(post_id: int = None):
    """Trang Blog - hiển thị danh sách hoặc bài viết cụ thể."""
    return render_template("blog.html", post_id=post_id)


@app.route("/blog-post/<int:post_id>")
def blog_post_page(post_id: int = None):
    """Trang Blog post riêng - mở trong tab mới."""
    return render_template("blog.html", post_id=post_id, standalone=True)


@app.route("/dashboard")
def dashboard():
    """Trang Admin Dashboard."""
    return render_template("dashboard.html", cache_version=45)


# ===================== SCAN FRONT REPO (PLAYWRIGHT) =====================
@app.route("/api/scan-front-repo")
def api_scan_front_repo():
    """Dùng Playwright scan trang Front repo, trả về JSON các khung lớn + vị trí tương đối.
    Mỗi khung: { key, selector, tag, id, classes, title, x, y, w, h, type }
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return jsonify({"ok": False, "error": f"playwright không khả dụng: {e}"}), 500

    url = request.args.get("url") or request.host_url.rstrip("/")
    viewport_w = int(request.args.get("vw") or 1280)
    viewport_h = int(request.args.get("vh") or 900)

    # Selector cho các khung lớn: header/main/aside/footer + .box + các id cố định
    SELECTORS = [
        # (key hint, selector)
        ("masthead", "#masthead"),
        ("hello-banner", "#helloBanner"),
        ("meta", "section.box:first-of-type"),
        ("packages", "#packagesBox"),
        ("blog-section", "#blog-section"),
        ("stars", "#stars"),
        ("music-player", "#music-player"),
        ("moon-widget", "#moon-widget"),
        ("hint-box", "section.hint-box"),
    ]

    # Các box generic nếu có
    GENERIC_BOX_SELECTOR = "section.box, div.box"

    boxes = []
    seen_keys = set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": viewport_w, "height": viewport_h})
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1200)

            # Trích xuất title + content text cho từng phần tử
            EXTRACT_SCRIPT = '''
                (sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return null;
                    // Tìm tiêu đề: h1/h2/h3 đầu tiên, hoặc class section-title, hoặc text ngắn nhất
                    let title = '';
                    const titleEl = el.querySelector('h1, h2, h3, .section-title, .pkg-header .section-title, .star-title');
                    if (titleEl) title = titleEl.textContent.trim();
                    // Lấy text content (skip script/style)
                    const clone = el.cloneNode(true);
                    clone.querySelectorAll('script, style, svg, button').forEach(n => n.remove());
                    let text = clone.textContent || '';
                    text = text.replace(/\\s+/g, ' ').trim().substring(0, 300);
                    // Lấy ảnh
                    const imgs = Array.from(el.querySelectorAll('img')).map(i => ({
                        src: i.src,
                        alt: i.alt || '',
                        w: i.naturalWidth || i.width,
                        h: i.naturalHeight || i.height,
                    }));
                    // Lấy icon/emoji đầu tiên
                    const firstIcon = (titleEl?.textContent || '').match(/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}]/u)?.[0] || '';
                    return {
                        title: title || '',
                        text: text,
                        imgs: imgs,
                        icon: firstIcon,
                        childCount: el.children.length,
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        className: el.className || '',
                    };
                }
            '''

            # Lấy vị trí các selector ưu tiên
            for hint, sel in SELECTORS:
                try:
                    el = page.locator(sel).first
                    if el.count() == 0:
                        continue
                    box = el.bounding_box()
                    if not box:
                        continue
                    info = page.evaluate(EXTRACT_SCRIPT, sel) or {}
                    # Title từ inner text hoặc từ heading
                    inner_text = el.inner_text()[:80].replace("\n", " ").strip()
                    title = info.get('title') or inner_text or hint
                    text_content = info.get('text', '')[:200]
                    boxes.append({
                        "key": hint,
                        "selector": sel,
                        "title": title,
                        "text": text_content,
                        "icon": info.get('icon', ''),
                        "imgs": info.get('imgs', []),
                        "childCount": info.get('childCount', 0),
                        "tag": info.get('tag', ''),
                        "elemId": info.get('id', ''),
                        "className": info.get('className', ''),
                        "x": round(box["x"]),
                        "y": round(box["y"]),
                        "w": round(box["width"]),
                        "h": round(box["height"]),
                        "type": "content",
                        "isReal": True,
                    })
                    seen_keys.add(hint)
                except Exception:
                    continue

            # Bổ sung các box generic chưa có trong danh sách
            try:
                gen = page.locator(GENERIC_BOX_SELECTOR).all()
                idx = 1
                for el in gen:
                    try:
                        bb = el.bounding_box()
                        if not bb:
                            continue
                        # Skip nếu đã có trong danh sách (cùng x,y)
                        already = any(abs(b["x"] - round(bb["x"])) < 2 and abs(b["y"] - round(bb["y"])) < 2 and abs(b["w"] - round(bb["width"])) < 2 for b in boxes)
                        if already:
                            continue
                        if bb["width"] < 40 or bb["height"] < 30:
                            continue
                        # Bỏ các box nằm ngoài viewport
                        if bb["y"] > viewport_h + 200:
                            continue
                        # Lấy selector cho element này
                        elem_id = el.evaluate("e => e.id")
                        elem_class = el.evaluate("e => e.className")
                        if elem_id:
                            sel_for_box = '#' + elem_id
                        elif elem_class:
                            # Lấy class đầu tiên
                            first_cls = elem_class.split()[0]
                            sel_for_box = '.' + first_cls
                        else:
                            sel_for_box = GENERIC_BOX_SELECTOR
                        info = page.evaluate(EXTRACT_SCRIPT, sel_for_box) or {}
                        inner_text = el.inner_text()[:60].replace("\n", " ").strip() or f"box-{idx}"
                        title = info.get('title') or inner_text
                        bkey = f"auto-box-{idx}"
                        boxes.append({
                            "key": bkey,
                            "selector": sel_for_box,
                            "title": title,
                            "text": info.get('text', '')[:200],
                            "icon": info.get('icon', ''),
                            "imgs": info.get('imgs', []),
                            "childCount": info.get('childCount', 0),
                            "tag": info.get('tag', ''),
                            "elemId": elem_id or '',
                            "className": elem_class or '',
                            "x": round(bb["x"]),
                            "y": round(bb["y"]),
                            "w": round(bb["width"]),
                            "h": round(bb["height"]),
                            "type": "content",
                            "isReal": True,
                        })
                        idx += 1
                    except Exception:
                        continue
            except Exception:
                pass

            browser.close()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "url": url, "viewport": {"w": viewport_w, "h": viewport_h}, "boxes": boxes})


# ===================== GET FRONT REPO HTML (for iframe clone) =====================
@app.route("/api/get-front-repo-html")
def api_get_front_repo_html():
    """Trả về HTML của index.html để inject vào iframe clone mode."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(template_path):
        return ("index.html not found", 404)
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    # Loại bỏ external <script> nặng gây chậm khi clone (giữ inline scripts để preview hoạt động)
    html = html.replace('<script src="/admin/static/app.js?v=16"></script>', '')
    # Loại bỏ link preload không cần thiết
    return html

# ===================== APPLY LAYOUT TO FRONT REPO =====================
@app.route("/api/apply-layout", methods=["POST"])
def api_apply_layout():
    """Nhận JSON layout từ Boxes editor, lưu vào localStorage key để index.html đọc và áp dụng.
    Mỗi box: { key, selector, title, titlePos, x, y, w, h, type, children, css }
    Response: { ok, boxes_applied, message }
    """
    try:
        # Lấy raw body nếu có
        raw = request.get_data(as_text=True) or ""
        if not raw:
            return jsonify({"ok": False, "error": "Empty body"}), 400
        try:
            data = json.loads(raw)
        except Exception as je:
            return jsonify({"ok": False, "error": f"Invalid JSON: {je}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    if not data or not data.get("boxes"):
        return jsonify({"ok": False, "error": "No boxes provided"}), 400

    boxes = data.get("boxes", [])

    layout_dir = os.path.join(os.path.dirname(__file__), "templates")
    layout_file = os.path.join(layout_dir, "_applied_layout.json")
    layout_data = {"boxes": boxes, "applied_at": str(datetime.datetime.now())}

    try:
        with open(layout_file, "w", encoding="utf-8") as f:
            json.dump(layout_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Cannot write layout file: {e}"}), 500

    return jsonify({
        "ok": True,
        "boxes_applied": len(boxes),
        "message": f"Applied layout to {len(boxes)} boxes. Refresh Front Repo page to see changes.",
        "layout_file": "_applied_layout.json"
    })


# ===================== GET APPLIED LAYOUT (for index.html) =====================
@app.route("/api/get-applied-layout")
def api_get_applied_layout():
    """Trả về layout đã được áp dụng để index.html có thể đọc và apply."""
    layout_file = os.path.join(os.path.dirname(__file__), "templates", "_applied_layout.json")
    if not os.path.exists(layout_file):
        return jsonify({"ok": True, "boxes": []})
    try:
        with open(layout_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "boxes": []}), 500


# ===================== BLOG DATA =====================
BLOG_POSTS = [
    {"id": 1, "icon": "📦", "title": "Cách cài đặt Repository trên ứng dụng 3105", "date": "2 ngày trước",
     "excerpt": "Hướng dẫn chi tiết cách cài đặt và sử dụng Repository trên ứng dụng 3105 Mod Collection...",
     "content": "<h2>Giới thiệu</h2><p>Repository là nơi lưu trữ các gói mod, theme và tiện ích mở rộng cho ứng dụng 3105. Bài viết này sẽ hướng dẫn bạn cách cài đặt Repository một cách dễ dàng.</p><h3>Bước 1: Truy cập ứng dụng</h3><p>Mở ứng dụng 3105 Mod Collection và điều hướng đến mục <strong>Cài đặt</strong>.</p><h3>Bước 2: Thêm Repository</h3><p>Nhấn nút <em>Thêm Repository</em> và nhập đường link Repository của bạn.</p><h3>Bước 3: Xác nhận</h3><p>Sau khi thêm thành công, bạn có thể tải về các gói mod từ Repository.</p>"},
    {"id": 2, "icon": "🛡️", "title": "Bảo mật khi sử dụng Mod - Những lưu ý quan trọng", "date": "5 ngày trước",
     "excerpt": "Tìm hiểu về các biện pháp bảo mật khi sử dụng mod trên thiết bị của bạn...",
     "content": "<h2>Tại sao bảo mật quan trọng?</h2><p>Việc sử dụng mod có thể tiềm ẩn rủi ro bảo mật nếu không cẩn thận.</p><h3>Các lưu ý:</h3><ul><li>Chỉ tải mod từ nguồn đáng tin cậy</li><li>Kiểm tra quyền trước khi cài đặt</li><li>Sao lưu dữ liệu thường xuyên</li></ul>"},
    {"id": 3, "icon": "⚡", "title": "Cập nhật v1.2 - Tính năng mới & cải tiến", "date": "1 tuần trước",
     "excerpt": "Khám phá các tính năng mới trong phiên bản v1.2 của ứng dụng 3105...",
     "content": "<h2>Phiên bản v1.2</h2><p>Phiên bản mới mang đến nhiều cải tiến đáng chú ý.</p><h3>Tính năng mới:</h3><ul><li>Giao diện người dùng được cải thiện</li><li>Tốc độ tải nhanh hơn 50%</li><li>Hỗ trợ nhiều ngôn ngữ mới</li></ul>"},
    {"id": 4, "icon": "🎨", "title": "Hướng dẫn tạo Custom Dialer cho riêng bạn", "date": "2 tuần trước",
     "excerpt": "Cách tạo bộ quay số tùy chỉnh với giao diện và hiệu ứng yêu thích...",
     "content": "<h2>Custom Dialer</h2><p>Tạo bộ quay số riêng biệt với phong cách của bạn.</p><h3>Các bước thực hiện:</h3><ol><li>Chọn hình nền yêu thích</li><li>Tùy chỉnh màu sắc nút bấm</li><li>Thêm hiệu ứng animation</li></ol>"},
    {"id": 5, "icon": "🎮", "title": "So sánh các gói Custom: VNG vs Global vs KR", "date": "3 tuần trước",
     "excerpt": "So sánh chi tiết các gói custom dialer phổ biến nhất hiện nay...",
     "content": "<h2>So sánh các gói Custom</h2><p>Chúng ta cùng so sánh 3 gói dialer phổ biến nhất.</p><table><tr><th>Tính năng</th><th>VNG</th><th>Global</th><th>KR</th></tr><tr><td>Giá</td><td>Miễn phí</td><td>Cao</td><td>Trung bình</td></tr><tr><td>Chất lượng</td><td>Tốt</td><td>Xuất sắc</td><td>Tốt</td></tr></table>"},
    {"id": 6, "icon": "🔧", "title": "Khắc phục lỗi thường gặp khi cập nhật Repository", "date": "1 tháng trước",
     "excerpt": "Các lỗi thường gặp và cách khắc phục nhanh chóng...",
     "content": "<h2>Sửa lỗi Repository</h2><p>Một số lỗi phổ biến và cách khắc phục.</p><h3>Lỗi kết nối:</h3><p>Kiểm tra đường truyền internet và thử lại sau.</p>"},
    {"id": 7, "icon": "💎", "title": "Premium Features có gì mới trong bản cập nhật", "date": "1 tháng trước",
     "excerpt": "Khám phá các tính năng Premium độc quyền dành cho người dùng...",
     "content": "<h2>Tính năng Premium</h2><p>Người dùng Premium được hưởng nhiều đặc quyền.</p><ul><li>Không quảng cáo</li><li>Hỗ trợ ưu tiên</li><li>Tính năng độc quyền</li></ul>"}
]


@app.route("/api/blog/posts")
def api_blog_posts():
    """API trả về danh sách blog posts CÔNG KHAI (đã lọc bỏ hidden).

    Posts có trường `hidden=true` sẽ KHÔNG hiện trong danh sách,
    nhưng vẫn truy cập được qua link trực tiếp `/blog/<id>` hoặc
    `/api/blog/post/<id>`.
    """
    include_hidden = (
        request.args.get("include_hidden") in ("1", "true", "yes")
        and is_authenticated()
    )
    posts = load_blog_posts()
    if not include_hidden:
        posts = [p for p in posts if not p.get("hidden")]
    return jsonify({"posts": posts})


@app.route("/api/blog/post/<int:post_id>")
def api_blog_post(post_id: int):
    """API trả về một bài viết cụ thể.

    Bài viết hidden vẫn trả về 200 nếu truy cập trực tiếp qua id
    (để link riêng vẫn dùng được).
    """
    posts = load_blog_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if post:
        return jsonify(post)
    abort(404, description="Post not found")


@app.route("/api/blog/post/<int:post_id>/hide", methods=["POST"])
@login_required
def api_blog_post_hide(post_id: int):
    """Toggle hidden flag cho một post (chỉ owner / đã đăng nhập)."""
    posts = load_blog_posts()
    post = next((p for p in posts if p["id"] == post_id), None)
    if not post:
        return jsonify({"ok": False, "error": "Post not found"}), 404
    body = request.get_data(as_text=True) or "{}"
    try:
        data = json.loads(body) if body.strip() else {}
    except Exception:
        data = {}
    hidden = bool(data.get("hidden", not post.get("hidden")))
    post["hidden"] = hidden
    save_blog_posts(posts)
    return jsonify({
        "ok": True,
        "id": post_id,
        "hidden": hidden,
        "message": "Đã ẩn bài viết" if hidden else "Đã hiện bài viết",
    })


# ===================== BLOG PERSISTENCE =====================
def _blog_posts_path() -> str:
    """Path tới file JSON lưu blog posts (đặt cạnh templates)."""
    return os.path.join(os.path.dirname(__file__), "templates", "_blog_posts.json")


def load_blog_posts() -> list:
    """Load blog posts từ JSON file. Nếu file không tồn tại → trả về default
    BLOG_POSTS (seed) và TỰ ĐỘNG ghi ra file lần đầu để lần sau không mất.
    """
    path = _blog_posts_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass
    # Fallback: ghi seed ra file rồi return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(BLOG_POSTS, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return BLOG_POSTS


def save_blog_posts(posts: list) -> None:
    """Ghi danh sách blog posts ra file JSON."""
    path = _blog_posts_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


@app.route("/api/blog/save", methods=["POST"])
def api_blog_save():
    """Nhận danh sách blog posts từ Dashboard và lưu vào file JSON.
    Body: { posts: [...] }
    Response: { ok, count, message }
    """
    try:
        raw = request.get_data(as_text=True) or ""
        if not raw:
            return jsonify({"ok": False, "error": "Empty body"}), 400
        try:
            data = json.loads(raw)
        except Exception as je:
            return jsonify({"ok": False, "error": f"Invalid JSON: {je}"}), 400
        posts = data.get("posts") if isinstance(data, dict) else data
        if not isinstance(posts, list):
            return jsonify({"ok": False, "error": "posts must be a list"}), 400
        # Validate nhẹ từng post
        cleaned = []
        for p in posts:
            if not isinstance(p, dict):
                continue
            if not p.get("title"):
                continue
            cleaned.append({
                "id": int(p.get("id") or 0),
                "icon": p.get("icon", "📝"),
                "title": str(p.get("title", "")),
                "date": str(p.get("date", "Vừa cập nhật")),
                "excerpt": str(p.get("excerpt", "")),
                "content": str(p.get("content", "")),
                "image": str(p.get("image", "")),
                "images": [str(u) for u in (p.get("images") or []) if u],
                "hidden": bool(p.get("hidden", False)),
            })
        save_blog_posts(cleaned)
        return jsonify({"ok": True, "count": len(cleaned), "message": f"Đã lưu {len(cleaned)} bài viết"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/blog/image-upload", methods=["POST"])
def api_blog_image_upload():
    """Upload ảnh cho Blog post (cover hoặc gallery).

    Form fields:
      - mode: 'cover' | 'gallery'
      - file: 1 file (cover) hoặc nhiều file (gallery)

    Response: {
      ok: True,
      url: 'assets/blog/<uuid>.png',     # cover
      urls: ['assets/blog/<uuid>.png'],   # gallery
    }
    """
    import uuid as _uuid
    from pathlib import Path
    from werkzeug.utils import secure_filename as _sec

    ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    mode = request.form.get("mode", "cover")
    files = request.files.getlist("file")
    if not files:
        return jsonify({"ok": False, "error": "Không có file nào được chọn"}), 400

    save_dir = ROOT / "assets" / "blog"
    save_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for f in files:
        if not f or not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            return jsonify({"ok": False, "error": f"Định dạng không hỗ trợ: {ext}"}), 400
        try:
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
        except Exception:
            size = 0
        if size and size > MAX_SIZE:
            return jsonify({"ok": False, "error": f"File quá lớn (tối đa 5MB). File: {f.filename}"}), 400

        unique_name = f"{_uuid.uuid4().hex[:12]}{ext}"
        out_path = save_dir / unique_name
        try:
            f.save(str(out_path))
            saved.append(f"assets/blog/{unique_name}")
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Không ghi được file: {exc}"}), 500

    if not saved:
        return jsonify({"ok": False, "error": "Không có file hợp lệ nào"}), 400

    # Trả URL public để browser load được
    base = request.host_url.rstrip("/")
    public_urls = [f"{base}/assets/blog/{pathlib.Path(s).name}" for s in saved]
    if mode == "cover":
        return jsonify({"ok": True, "url": public_urls[0], "path": saved[0]})
    return jsonify({"ok": True, "urls": public_urls, "paths": saved})


# ---------------------------------------------------------------------------
# Front-End-Checklist MCP integration
# ---------------------------------------------------------------------------
import fe_checklist as _fe


@app.route("/fe-checklist")
def fe_checklist_page():
    """Trang browse + audit Front-End Checklist."""
    return render_template("fe_checklist.html")


@app.get("/api/fe-checklist/categories")
def api_fe_categories():
    try:
        data = _fe.list_categories()
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.get("/api/fe-checklist/rules")
def api_fe_rules():
    """Trả về tất cả rules của 1 category."""
    category = request.args.get("category", "").strip()
    if not category:
        return jsonify({"ok": False, "error": "Missing category"}), 400
    try:
        data = _fe.list_all_rules_in_category(category)
        return jsonify({"ok": True, "category": category, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.get("/api/fe-checklist/rule/<slug>")
def api_fe_rule(slug: str):
    """Chi tiết 1 rule theo slug."""
    try:
        data = _fe.get_rule(slug)
        return jsonify({"ok": True, "slug": slug, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.get("/api/fe-checklist/search")
def api_fe_search():
    """Tìm rule theo query."""
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip() or None
    if not q:
        return jsonify({"ok": False, "error": "Missing q"}), 400
    try:
        rules = _fe.search_rules(q, category)
        return jsonify({"ok": True, "q": q, "rules": rules})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.post("/api/fe-checklist/review-code")
def api_fe_review_code():
    """Static review HTML/CSS/JS code paste."""
    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "")
    language = payload.get("language", "html")
    if not code.strip():
        return jsonify({"ok": False, "error": "Missing code"}), 400
    if len(code) > 200_000:
        return jsonify({"ok": False, "error": "code > 200KB"}), 413
    try:
        data = _fe.review_code(code, language)
        return jsonify({"ok": True, "language": language, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.post("/api/fe-checklist/audit-url")
def api_fe_audit_url():
    """Audit 1 public URL."""
    payload = request.get_json(silent=True) or {}
    url = payload.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"ok": False, "error": "URL phải bắt đầu bằng http(s)://"}), 400
    try:
        data = _fe.audit_url(url)
        return jsonify({"ok": True, "url": url, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.post("/api/fe-checklist/fix-rule")
def api_fe_fix_rule():
    """Sinh code fix cho rule."""
    payload = request.get_json(silent=True) or {}
    slug = payload.get("slug", "").strip()
    code = payload.get("code", "")
    if not slug:
        return jsonify({"ok": False, "error": "Missing slug"}), 400
    try:
        data = _fe.fix_rule(slug, code)
        return jsonify({"ok": True, "slug": slug, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.get("/api/fe-checklist/workflow/<name>")
def api_fe_workflow(name: str):
    try:
        data = _fe.get_workflow(name)
        return jsonify({"ok": True, "name": name, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.get("/api/fe-checklist/cache-status")
def api_fe_cache_status():
    return jsonify({"ok": True, "data": _fe.cache_status()})


@app.route("/admin/static/<path:filename>")
def admin_static(filename: str):
    return send_from_directory(app.static_folder, filename)


@app.route("/assets/<path:filename>")
def serve_assets(filename: str):
    """Phục vụ file tĩnh từ thư mục assets/ ở repo root (rain.mp3, test_tone.mp3, ...).
    Dùng cho music player + các file media không nằm trong assets/<repo>/..."""
    safe = pathlib.Path(filename).name  # chống path traversal
    asset_path = ROOT / "assets" / safe
    if not asset_path.is_file():
        abort(404, description=f"Asset not found: {filename}")
    return send_from_directory(str(asset_path.parent), asset_path.name)


@app.get("/repo-asset")
def repo_asset():
    """Phục vụ ảnh asset (icon/banner/screenshot) từ repo để hiển thị thumbnail."""
    repo = _safe_repo_name(request.args.get("repo", ""))
    rel = request.args.get("path", "").replace("\\", "/").lstrip("/")
    if not rel:
        abort(400, description="Missing path")
    paths = repo_paths(repo)
    asset_dir = paths["assets"].resolve()
    target = (paths["root"] / rel).resolve()
    try:
        target.relative_to(asset_dir)
    except ValueError:
        abort(403, description="Path nằm ngoài thư mục assets/")
    if not target.is_file():
        abort(404, description=f"File not found: {rel}")
    return send_from_directory(str(target.parent), target.name)


# ---------------------------------------------------------------------------
# Background Image API
# ---------------------------------------------------------------------------
BG_UPLOAD_DIR = pathlib.Path(__file__).parent / "backgrounds"


@app.post("/api/backgrounds/upload")
def api_upload_background():
    """Upload ảnh nền. Chấp nhận .jpg, .jpeg, .png, .gif, .webp. Max 10MB."""
    BG_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file = request.files.get("image")
    if not file or not file.filename:
        abort(400, description="No image file provided")
    import re, secrets
    orig = pathlib.Path(file.filename).name
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", orig)
    ext = pathlib.Path(safe).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        abort(400, description="Unsupported extension. Chấp nhận: .jpg, .jpeg, .png, .gif, .webp")
    # Sniff magic bytes để chắc chắn là ảnh (không phụ thuộc python-magic)
    head = file.read(12)
    file.seek(0)
    # JPEG: FF D8 FF  | PNG: 89 50 4E 47  | GIF: 47 49 46 38  | WebP: 52 49 46 46 ?? 57 45 42 50
    if head.startswith(b"\xff\xd8\xff"):
        actual_ext = ".jpg"
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        actual_ext = ".png"
    elif head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        actual_ext = ".gif"
    elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        actual_ext = ".webp"
    else:
        abort(400, description="File không phải ảnh hợp lệ (chỉ JPG/PNG/GIF/WebP)")
    # Prefer detected extension
    ext = actual_ext
    # Generate unique filename to avoid collisions
    name = f"{secrets.token_hex(6)}{ext}"
    path = BG_UPLOAD_DIR / name
    file.save(str(path))
    # Return URL for the image
    return jsonify({
        "ok": True,
        "filename": name,
        "url": f"/api/backgrounds/{name}",
        "size": path.stat().st_size,
    })


@app.get("/api/backgrounds")
def api_list_backgrounds():
    """Liệt kê tất cả ảnh nền đã upload."""
    BG_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(BG_UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        if f.is_file():
            result.append({
                "filename": f.name,
                "url": f"/api/backgrounds/{f.name}",
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
            })
    return jsonify(result)


@app.get("/api/backgrounds/<filename>")
def api_serve_background(filename: str):
    """Phục vụ ảnh nền đã upload."""
    path = BG_UPLOAD_DIR / filename
    if not path.is_file():
        abort(404, description="Background not found")
    return send_from_directory(str(BG_UPLOAD_DIR), filename)


# ---------------------------------------------------------------------------
# Blog image serving
# ---------------------------------------------------------------------------

BLOG_UPLOAD_DIR = ROOT / "assets" / "blog"


@app.get("/assets/blog/<filename>")
def api_serve_blog_image(filename: str):
    """Phục vụ ảnh blog đã upload (cover/gallery)."""
    safe = pathlib.Path(filename).name  # chống path traversal
    if safe != filename or "/" in safe or ".." in safe:
        abort(404, description="Invalid filename")
    path = BLOG_UPLOAD_DIR / safe
    if not path.is_file():
        abort(404, description="Blog image not found")
    return send_from_directory(str(BLOG_UPLOAD_DIR), safe)


@app.delete("/api/backgrounds/<filename>")
def api_delete_background(filename: str):
    """Xóa ảnh nền."""
    path = BG_UPLOAD_DIR / filename
    if not path.is_file():
        abort(404, description="Background not found")
    path.unlink()
    return jsonify({"ok": True, "deleted": filename})


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/api/repositories")
def api_repositories():
    """Liệt kê tất cả repo local + merge với GitHub-owned (nếu user đã login).

    Luôn trả cả 2:
      - `repositories`: list slug local (như cũ)
      - `sources`: list URL từ sources.json
      - `github_owned`: list dict (slug, full_name, html_url, ...) nếu authenticated
    Front Repo JS dùng `github_owned` để populate dropdown repo + detect ownership.
    """
    repos = list_repositories()
    sources: list[str] = []
    if SOURCES_FILE.is_file():
        try:
            data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
            sources = data.get("sources", [])
        except Exception:
            pass

    github_owned = []
    if is_authenticated():
        try:
            github_owned = auth_get_owned_repos()
        except Exception:
            pass  # discovery failed → return empty

    return jsonify({
        "repositories": repos,
        "sources": sources,
        "github_owned": github_owned,
    })


@app.route("/api/public/admin-settings/<owner>/<repo>")
def api_public_admin_settings(owner: str, repo: str):
    """Public endpoint — fetch `.3105/admin-settings.json` từ repo GitHub.

    Dùng cho anonymous user (không login) để lấy admin defaults:
      - User mở Front Repo lần đầu
      - localStorage empty → fetch admin-settings → fill user namespace
      - Sau đó user chỉnh riêng → KHÔNG bị override bởi admin settings nữa
    """
    import time as _time
    import requests as _req

    cache_key = f"public_admin_settings:{owner}:{repo}"
    cached = app.config.get(cache_key)
    cache_ts = app.config.get(cache_key + ":ts", 0)
    now = _time.time()
    if cached is not None and (now - cache_ts) < 300:
        return jsonify(cached)

    full_name = f"{owner}/{repo}"
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/.3105/admin-settings.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "3105-repo-builder/1.0",
    }
    # Use PAT for read requests to bypass 60/hr rate limit.
    if Config.GITHUB_PAT:
        headers["Authorization"] = f"Bearer {Config.GITHUB_PAT}"
    try:
        resp = _req.get(url, headers=headers, timeout=10)
    except _req.RequestException as e:
        return jsonify({"ok": False, "error": f"GitHub request failed: {e}"}), 502

    if resp.status_code == 404:
        # Không có file → trả default empty, vẫn ok
        result = {"ok": True, "settings": {}, "source": "default"}
        app.config[cache_key] = result
        app.config[cache_key + ":ts"] = now
        return jsonify(result)

    if resp.status_code != 200:
        return jsonify({"ok": False, "error": f"GitHub returned {resp.status_code}"}), 502

    try:
        import base64 as _b64
        import json as _json
        data = resp.json()
        raw = _b64.b64decode(data.get("content", "")).decode("utf-8")
        settings = _json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        return jsonify({"ok": False, "error": f"Invalid JSON: {e}"}), 502

    result = {"ok": True, "settings": settings, "source": "github"}
    app.config[cache_key] = result
    app.config[cache_key + ":ts"] = now
    return jsonify(result)


@app.route("/api/public/release/<owner>/<repo>/<path:package_id>")
def api_public_release_lookup(owner: str, repo: str, package_id: str):
    """Public endpoint — tìm download URL cho package từ GitHub Releases.

    Không cần auth (vì GitHub Releases API public cho repo public).
    Dùng cho Front Repo của user thường (không login) → tìm nút Tải xuống.

    Args:
      owner: GitHub username
      repo: repo name
      package_id: vd "com.example.pkg1"

    Returns: {
      "ok": True,
      "download_url": "https://github.com/.../releases/download/...",
      "version": "1.2.0",
      "tag": "v1.2.0",
      "size_bytes": 12345,
      "sha256": "abc...",
      "asset_name": "pkg-1.2.0.3105",
    }
    """
    import time as _time
    import requests as _req

    cache_key = f"public_release:{owner}:{repo}:{package_id}"
    cached = app.config.get(cache_key)
    cache_ts = app.config.get(cache_key + ":ts", 0)
    now = _time.time()
    if cached and (now - cache_ts) < 300:  # cache 5 phút
        return jsonify(cached)

    full_name = f"{owner}/{repo}"
    base_headers = {"Accept": "application/vnd.github+json", "User-Agent": "3105-repo-builder/1.0"}

    # Strategy 1: tìm trong repo.json (chính xác nhất, không cần token)
    # Thử nhiều path candidates
    try:
        from .repo_discovery import REPO_JSON_PATHS
        for path in REPO_JSON_PATHS:
            url = f"https://api.github.com/repos/{full_name}/contents/{path}"
            resp = _req.get(url, headers=base_headers, timeout=10)
            if resp.status_code != 200:
                continue
            import base64 as _b64
            data = resp.json()
            content_raw = _b64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
            if path.endswith((".yml", ".yaml")):
                import yaml as _y
                content = _y.safe_load(content_raw)
            else:
                content = json.loads(content_raw)
            for rel in content.get("releases", []):
                if rel.get("package_id") == package_id:
                    result = {
                        "ok": True,
                        "source": "repo.json",
                        "download_url": rel.get("download_url"),
                        "version": rel.get("version"),
                        "tag": rel.get("tag"),
                        "size_bytes": rel.get("size_bytes"),
                        "sha256": rel.get("sha256"),
                        "asset_name": rel.get("asset_name"),
                    }
                    app.config[cache_key] = result
                    app.config[cache_key + ":ts"] = now
                    return jsonify(result)
    except Exception as e:
        app.logger.debug(f"repo.json lookup failed: {e}")

    # Strategy 2: list GitHub Releases, match by filename (fallback)
    try:
        url = f"https://api.github.com/repos/{full_name}/releases?per_page=30"
        resp = _req.get(url, headers=base_headers, timeout=10)
        if resp.status_code == 200:
            releases = resp.json()
            for release in releases:
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if package_id in name:
                        result = {
                            "ok": True,
                            "source": "github_releases_fallback",
                            "download_url": asset.get("browser_download_url"),
                            "version": release.get("tag_name", "").lstrip("v"),
                            "tag": release.get("tag_name"),
                            "size_bytes": asset.get("size", 0),
                            "sha256": "",
                            "asset_name": name,
                        }
                        app.config[cache_key] = result
                        app.config[cache_key + ":ts"] = now
                        return jsonify(result)
    except Exception as e:
        app.logger.debug(f"releases fallback failed: {e}")

    return jsonify({"ok": False, "error": f"Không tìm thấy release cho {package_id} trong {full_name}"}), 404


@app.get("/api/repo/<repo>/packages")
def api_list_packages(repo: str):
    paths = repo_paths(repo)
    data = load_yaml(paths["yml"])
    raw_packages = data.get("packages") or []

    # Phát hiện nhóm OS / screenshots phổ biến để tạo anchor
    common_os, common_screens = detect_anchor_groups(raw_packages)
    if common_os is None:
        common_os = DEFAULT_OS_RULES
    if common_screens is None:
        common_screens = DEFAULT_SCREENSHOTS

    # Strip các key nội bộ (bắt đầu bằng __) khỏi package data trả về cho client
    # vì đây chỉ là metadata phục vụ cho save_yaml, không thuộc schema.
    cleaned_packages: list[dict[str, Any]] = []
    packages_meta: list[dict[str, Any]] = []
    for pkg in raw_packages:
        cleaned: dict[str, Any] = {k: v for k, v in pkg.items() if not k.startswith("__")}
        # Anchor OS: khớp đúng DEFAULT_OS_RULES
        pkg_os = pkg.get("supportedOS")
        if _normalize_os(pkg_os) is not None:
            use_default_os = True
        elif isinstance(pkg_os, list) and pkg_os == common_os:
            use_default_os = True
        else:
            use_default_os = False

        # Anchor screens: khớp đúng common_screens
        pkg_screens = pkg.get("screenshots")
        if (
            isinstance(pkg_screens, list)
            and pkg_screens
            and pkg_screens == common_screens
        ):
            use_default_screens = True
        else:
            use_default_screens = False

        cleaned_packages.append(cleaned)
        packages_meta.append({
            "use_anchor_os": use_default_os,
            "use_anchor_screens": use_default_screens,
        })

    return jsonify({
        "repo": repo,
        "repoMeta": {
            k: data[k]
            for k in ("schemaVersion", "identifier", "name", "description", "icon", "accentColor")
            if k in data
        },
        "packages": cleaned_packages,
        "sharedScreens": common_screens,
        "sharedOS": common_os,
        "packagesMeta": packages_meta,
    })


@app.get("/api/repo/<repo>/files")
def api_files(repo: str):
    paths = repo_paths(repo)
    return jsonify({
        "assets": scan_files(paths["assets"], IMAGE_EXT),
        "packages": scan_files(paths["packages"], PACKAGE_EXT),
    })


def _list_subdirs(directory: pathlib.Path, base: pathlib.Path) -> list[dict[str, Any]]:
    """Trả về danh sách thư mục con (relative path) của directory."""
    if not directory.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(directory.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir():
            rel = p.relative_to(base).as_posix()
            children = _list_subdirs(p, base)
            out.append({"path": rel, "name": p.name, "children": children})
    return out


@app.get("/api/repo/<repo>/folders")
def api_folders(repo: str):
    """Trả về cây thư mục con trong assets/ để chọn khi thêm screenshot."""
    paths = repo_paths(repo)
    return jsonify({
        "folders": _list_subdirs(paths["assets"], paths["assets"]),
    })


@app.get("/api/repo/<repo>/folder-files")
def api_folder_files(repo: str):
    """Trả về danh sách ảnh trong một folder cụ thể (relative đến repo root)."""
    paths = repo_paths(repo)
    folder = request.args.get("path", "").replace("\\", "/").lstrip("/")
    target = paths["assets"]
    if folder:
        target = target / folder
    if not target.is_dir():
        abort(404, description=f"Folder not found: {folder}")
    rel_files: list[str] = []
    # root assets/ → chỉ lấy file trực tiếp (không đệ quy), tránh trùng ảnh subfolder
    for f in sorted(target.glob("*") if not folder else target.rglob("*")):
        if f.is_file() and f.suffix.lower() in IMAGE_EXT:
            rel = f.relative_to(paths["root"]).as_posix()
            rel_files.append(rel)
    all_files = scan_files(paths["assets"], IMAGE_EXT)
    return jsonify({
        "files": rel_files,
        "folder": folder,
        "all_count": len(all_files),
    })


@app.post("/api/repo/<repo>/upload")
def api_upload(repo: str):
    """Upload file ảnh hoặc .3105 lên repo.

    - kind=image  → lưu vào assets/<subfolder>/
    - kind=package → lưu vào packages/
    """
    paths = repo_paths(repo)
    kind = request.args.get("kind", "image")
    subfolder = request.args.get("folder", "").strip().replace("\\", "/").strip("/")

    if kind == "image":
        target_dir = paths["assets"]
        if subfolder:
            target_dir = target_dir / subfolder
        allowed_exts = IMAGE_EXT
    elif kind == "package":
        target_dir = paths["packages"]
        allowed_exts = PACKAGE_EXT
    else:
        abort(400, description=f"Unknown upload kind: {kind}")

    target_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        ext = pathlib.Path(f.filename).suffix.lower()
        if ext not in allowed_exts:
            abort(400, description=f"File extension không hợp lệ: {f.filename}")
        safe_name = pathlib.Path(f.filename).name
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
        dest = target_dir / safe_name
        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            i = 2
            while True:
                candidate = target_dir / f"{stem}_{i}{suffix}"
                if not candidate.exists():
                    dest = candidate
                    break
                i += 1
        f.save(str(dest))
        rel = dest.relative_to(paths["root"]).as_posix()
        saved.append(rel)
    return jsonify({"ok": True, "saved": saved})


@app.route("/api/repo/<repo>/file", methods=["DELETE"])
def api_delete_file(repo: str):
    """Xoá file hoặc thư mục (assets/ hoặc packages/)."""
    paths = repo_paths(repo)
    path_arg = request.args.get("path", "").strip().replace("\\", "/").strip("/")
    kind = request.args.get("kind", "image")  # "image" | "package"
    if not path_arg:
        abort(400, description="Missing path")
    if ".." in path_arg:
        abort(403, description="Path traversal not allowed")

    if kind == "package":
        target_dir = paths["packages"]
        prefix = "packages/"
    else:
        target_dir = paths["assets"]
        prefix = "assets/"

    # Strip the dir prefix from path_arg so we can safely join with target_dir
    if path_arg.startswith(prefix):
        path_arg = path_arg[len(prefix):]
    target = target_dir / path_arg

    # An toàn: chỉ xóa bên trong repo
    safe_root = target_dir.resolve()
    if not target.resolve().is_relative_to(safe_root):
        abort(403, description="Cannot delete outside repo directory")

    if target.is_dir():
        shutil.rmtree(target)
        return jsonify({"ok": True, "deleted": path_arg, "type": "directory"})
    elif target.is_file():
        target.unlink()
        return jsonify({"ok": True, "deleted": path_arg, "type": "file"})
    else:
        abort(404, description="Path not found")


@app.post("/api/repo/<repo>/mkdir")
def api_mkdir(repo: str):
    """Tạo thư mục con trong assets/."""
    paths = repo_paths(repo)
    payload = request.get_json(silent=True) or {}
    folder = (payload.get("folder") or "").strip().replace("\\", "/").strip("/")
    if not folder:
        abort(400, description="Missing folder")
    if ".." in folder.split("/"):
        abort(400, description="Invalid folder path")
    target = paths["assets"] / folder
    if target.exists():
        abort(409, description=f"Folder đã tồn tại: {folder}")
    target.mkdir(parents=True, exist_ok=False)
    return jsonify({"ok": True, "folder": folder})


@app.post("/api/repo/<repo>/hash")
def api_hash(repo: str):
    """Tính SHA-256 và size cho file .3105 nằm trong thư mục packages của repo."""
    paths = repo_paths(repo)
    payload = request.get_json(silent=True) or {}
    relative = payload.get("path", "")
    relative = relative.replace("\\", "/").lstrip("/")
    if relative.startswith("packages/"):
        relative = relative[len("packages/"):]
    if not relative:
        abort(400, description="Missing path")
    file_path = paths["packages"] / relative
    sha, size = hash_file(file_path)
    return jsonify({
        "path": f"packages/{relative}",
        "sha256": sha,
        "size": size,
    })


@app.post("/api/repo/<repo>/save")
def api_save(repo: str):
    """Ghi lại repo.yml với danh sách packages từ frontend gửi lên."""
    paths = repo_paths(repo)
    payload = request.get_json(silent=True) or {}

    packages = payload.get("packages") or []
    repo_meta = payload.get("repoMeta") or {}
    packages_meta = payload.get("packagesMeta") or []

    # Validate repoMeta
    repo_id = repo_meta.get("identifier", "")
    if repo_id and not IDENTIFIER_RE.match(repo_id):
        abort(400, description=f"Invalid repo identifier: {repo_id!r}")
    if repo_meta.get("accentColor") and not re.fullmatch(r"#[0-9A-Fa-f]{3,8}", str(repo_meta["accentColor"])):
        abort(400, description=f"Invalid accentColor: {repo_meta['accentColor']!r}")

    # Validate nhẹ từng package
    seen_ids: set[str] = set()
    for pkg in packages:
        ident = pkg.get("identifier", "")
        if not IDENTIFIER_RE.match(ident):
            abort(400, description=f"Invalid identifier: {ident!r}")
        if ident in seen_ids:
            abort(400, description=f"Duplicate identifier: {ident!r}")
        seen_ids.add(ident)
        if not pkg.get("name"):
            abort(400, description=f"Package {ident!r} missing name")
        if not pkg.get("download"):
            abort(400, description=f"Package {ident!r} missing download path")
        if not pkg.get("sha256"):
            abort(400, description=f"Package {ident!r} missing sha256")
        if pkg.get("size") is None:
            abort(400, description=f"Package {ident!r} missing size")
        # sha256 phải là hex 64 ký tự
        sha_clean = re.sub(r"\s+", "", str(pkg.get("sha256", "")))
        if not re.fullmatch(r"[0-9A-Fa-f]{64}", sha_clean):
            abort(400, description=f"Package {ident!r} has invalid sha256")

    # Quyết định anchor chung cho cả file dựa trên packages_meta
    shared_os = DEFAULT_OS_RULES
    shared_screens = DEFAULT_SCREENSHOTS
    use_anchor_os_any = False
    use_anchor_screens_any = False
    cleaned_meta: list[dict[str, Any]] = []
    for idx, meta in enumerate(packages_meta):
        use_os = bool(meta.get("use_anchor_os"))
        use_screens = bool(meta.get("use_anchor_screens"))
        if use_os:
            use_anchor_os_any = True
        if use_screens:
            use_anchor_screens_any = True
        # Đính kèm payload anchor vào meta để save_yaml biết dùng cái gì
        cleaned_meta.append({
            "use_anchor_os": use_os,
            "use_anchor_screens": use_screens,
            "shared_os": shared_os,
            "shared_screens": shared_screens,
        })

    full_data = {
        "schemaVersion": repo_meta.get("schemaVersion", 1),
        "identifier": repo_meta.get("identifier", f"com.owen.{repo}"),
        "name": repo_meta.get("name", f"{repo.title()} Repository"),
        "description": repo_meta.get("description", ""),
        "icon": repo_meta.get("icon", "assets/repo-icon.png"),
        "accentColor": repo_meta.get("accentColor", "#FF3B30"),
        "packages": packages,
    }

    save_yaml(paths["yml"], full_data, packages_meta=cleaned_meta)

    return jsonify({
        "ok": True,
        "saved": str(paths["yml"].relative_to(ROOT)),
        "count": len(packages),
        "anchors": {
            "os": use_anchor_os_any,
            "screens": use_anchor_screens_any,
        },
    })


@app.post("/api/repo/<repo>/push")
def api_push(repo: str):
    """Chạy git pull → add → commit → push cho repo đang active.

    Body JSON: {"commit_msg": "..."}  (tuỳ chọn, sẽ dùng default nếu thiếu)
    """
    paths = repo_paths(repo)

    # Kiểm tra đây có phải git repo không
    git_dir = ROOT / ".git"
    if not git_dir.is_dir():
        abort(400, description="Thư mục này không phải là git repository (không tìm thấy .git ở thư mục gốc project).")

    payload = request.get_json(silent=True) or {}
    commit_msg = (payload.get("commit_msg") or "").strip()
    if not commit_msg:
        # Fallback: dùng identifier repo
        try:
            data = load_yaml(paths["yml"])
            ident = data.get("identifier", repo)
        except Exception:
            ident = repo
        commit_msg = f"Update {ident}"

    def _run(*cmd: str) -> tuple[int, str]:
        import subprocess
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout + result.stderr

    # 1. git pull origin main
    code, out = _run("git", "pull", "origin", "main")
    pull_out = (out or "").strip()
    if code != 0:
        return jsonify({
            "ok": False,
            "step": "pull",
            "message": f"git pull thất bại (exit {code})",
            "detail": pull_out[:500],
        })

    # 2. git add -A
    code, out = _run("git", "add", "-A")
    if code != 0:
        return jsonify({
            "ok": False,
            "step": "add",
            "message": f"git add thất bại (exit {code})",
            "detail": (out or "").strip()[:500],
        })

    # 3. git status (báo cáo trạng thái, KHÔNG return ngay - cho phép empty commit để lưu message)
    code, out = _run("git", "status")
    status_out = (out or "").strip()
    has_changes = bool(status_out)

    # 3.5. Nếu không có thay đổi nào → báo về luôn
    if not has_changes:
        return jsonify({
            "ok": True,
            "step": "nothing-to-commit",
            "message": "Không có thay đổi nào để commit/push.",
            "pull": pull_out[:200],
            "status": status_out[:500],
            "commit": commit_msg,
        })

    # 4. git commit
    code, out = _run("git", "commit", "-m", commit_msg)
    commit_out = (out or "").strip()
    if code != 0:
        return jsonify({
            "ok": False,
            "step": "commit",
            "message": f"git commit thất bại (exit {code})",
            "detail": commit_out[:500],
        })

    # 5. git push origin main
    code, out = _run("git", "push", "origin", "main")
    push_out = (out or "").strip()
    if code != 0:
        return jsonify({
            "ok": False,
            "step": "push",
            "message": f"git push thất bại (exit {code})",
            "detail": push_out[:500],
        })

    return jsonify({
        "ok": True,
        "step": "done",
        "message": f"Đã push thành công. Commit: {commit_msg}",
        "pull": pull_out[:200],
        "status": status_out[:500],
        "commit": commit_out[:200],
        "push": push_out[:200],
    })


# ============================================================================
# OAuth-aware write API: ghi file vào GitHub repo qua Contents API
# ============================================================================
# Hai mode: "pr" (tạo Pull Request, an toàn) | "direct" (push thẳng).
# Verify ownership qua @owner_required → chỉ user có repo.json mới ghi được.

@app.route("/api/github/write", methods=["POST"])
@login_required
def api_github_write():
    """Ghi file vào GitHub repo của owner.

    Body JSON:
      {
        "slug": "demo",                      # repo slug (required)
        "path": "repo.yml",                  # file path trong repo (required)
        "content": "...",                    # UTF-8 text (required)
        "message": "fix: ...",               # commit message (required)
        "mode": "pr" | "direct",             # default "pr"
      }

    Response:
      {
        "ok": true,
        "mode": "pr" | "direct",
        "branch": "3105-edit-abc123",
        "commit_sha": "...",
        "commit_url": "https://github.com/...",
        "pr_url": "https://github.com/.../pull/42",
        "pr_number": 42,
      }
    """
    data = request.get_json(silent=True) or {}
    slug = (data.get("slug") or "").strip()
    path = (data.get("path") or "").strip().lstrip("/")
    content = data.get("content") or ""
    message = (data.get("message") or "").strip()
    mode = (data.get("mode") or "pr").strip()

    # Validate input
    err = _validate_inputs(slug, path, content, message)
    if err:
        return jsonify({"ok": False, "error": err}), 400
    if mode not in ("pr", "direct"):
        return jsonify({"ok": False, "error": "mode phải là 'pr' hoặc 'direct'"}), 400

    # Verify ownership
    owned = auth_get_owned_repos()
    target = next((r for r in owned if r.get("slug") == slug), None)
    if not target:
        return jsonify({
            "ok": False,
            "error": f"Bạn không phải owner của repo slug={slug!r}, hoặc repo không có repo.json",
        }), 403

    # Write to GitHub
    from .auth import get_current_token
    token = get_current_token()
    if not token:
        return jsonify({"ok": False, "error": "Session không có GitHub token"}), 401

    try:
        result = gh_write_file(
            token=token,
            full_name=target["full_name"],
            path=path,
            content=content,
            commit_message=message,
            mode=mode,
        )
        return jsonify({"ok": True, **result})
    except FileNotFoundError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 502
    except Exception as e:
        app.logger.exception("github_write failed")
        return jsonify({"ok": False, "error": f"Lỗi không mong đợi: {e}"}), 500


# ============================================================================
# GitHub Releases API: admin upload .3105 file → release trên GitHub
# ============================================================================
# Flow:
#   1. Admin POST multipart với file + package_id + version + commit message
#   2. Server verify ownership
#   3. Tạo GitHub Release (hoặc lấy release nếu tag đã tồn tại)
#   4. Upload asset (.3105) lên release
#   5. Update repo.json với release URL (push lên GitHub)
#   6. Trả về download_url cho Front Repo hiển thị nút Tải xuống
#
# Auto-detect fallback: GET /api/github/releases/{slug} → list releases của repo

@app.route("/api/github/release", methods=["POST"])
@login_required
def api_github_release_upload():
    """Upload 1 .3105 file lên GitHub Release.

    Multipart form data:
      - slug: str (required)
      - package_id: str (required) — vd "com.example.pkg1"
      - version: str (required) — vd "1.2.0" (sẽ tạo tag "v1.2.0")
      - asset_name: str (optional) — mặc định "{package_id}-{version}.3105"
      - file: file upload (required) — file .3105 binary
      - mode: "pr" | "direct" (default "pr") — cho việc update repo.json
      - notes: str (optional) — release notes

    Returns: {
      "ok": True,
      "release": {tag, html_url, ...},
      "asset": {name, size, browser_download_url, sha256},
      "download_url": "...",  // cho Front Repo dùng
      "repo_json_updated": True,
      "pr_url": "..." | null,
    }
    """
    slug = (request.form.get("slug") or "").strip()
    package_id = (request.form.get("package_id") or "").strip()
    version = (request.form.get("version") or "").strip()
    asset_name = (request.form.get("asset_name") or "").strip()
    mode = (request.form.get("mode") or "pr").strip()
    notes = (request.form.get("notes") or "").strip()

    if not slug or not package_id or not version:
        return jsonify({"ok": False, "error": "Thiếu slug, package_id hoặc version"}), 400
    if mode not in ("pr", "direct"):
        return jsonify({"ok": False, "error": "mode không hợp lệ"}), 400

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "Thiếu file"}), 400

    # Asset name default
    if not asset_name:
        # Sanitize package_id cho filename (vd "com.example.pkg" → "com.example.pkg")
        safe_pkg = package_id.replace("/", "_").replace("\\", "_")
        asset_name = f"{safe_pkg}-{version}.3105"
    if not asset_name.endswith(".3105"):
        asset_name = asset_name + ".3105"

    # Verify ownership
    owned = auth_get_owned_repos()
    target = next((r for r in owned if r.get("slug") == slug), None)
    if not target:
        return jsonify({"ok": False, "error": "Bạn không phải owner"}), 403

    from .auth import get_current_token
    token = get_current_token()
    if not token:
        return jsonify({"ok": False, "error": "Session không có token"}), 401

    # Read file bytes
    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"ok": False, "error": "File rỗng"}), 400
    # Hard cap: 95MB (GitHub limit ~100MB cho asset)
    if len(file_bytes) > 95 * 1024 * 1024:
        return jsonify({"ok": False, "error": "File quá lớn (>95MB)"}), 400

    # Tag name = v{version}
    tag_name = version if version.startswith("v") else f"v{version}"

    # 1. Tạo release
    try:
        release = create_or_get_release(
            token=token,
            full_name=target["full_name"],
            tag_name=tag_name,
            target_branch=target.get("default_branch", "main"),
            name=f"Release {tag_name}",
            body=notes or f"Release {tag_name} cho package {package_id}",
            draft=False,
            prerelease=False,
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": f"Tag không hợp lệ: {e}"}), 400
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    # 2. Upload asset
    try:
        asset = upload_release_asset(
            token=token,
            full_name=target["full_name"],
            release_id=release["id"],
            asset_name=asset_name,
            asset_bytes=file_bytes,
        )
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    # 3. Update repo.json với release URL mới
    repo_json_updated = False
    pr_url = None
    try:
        import base64, json as _json
        # Fetch current repo.json
        from .repo_discovery import _get_file_contents  # private helper, OK
        content, sha = _get_file_contents(token, target["full_name"], target["repo_json_path"])
        releases = content.get("releases", [])
        # Remove existing entry cho cùng package_id + tag (update)
        releases = [r for r in releases if not (
            r.get("package_id") == package_id and r.get("tag") == tag_name
        )]
        releases.append({
            "package_id": package_id,
            "version": version,
            "tag": tag_name,
            "asset_name": asset_name,
            "download_url": asset["browser_download_url"],
            "size_bytes": asset["size"],
            "sha256": asset["sha256"],
        })
        content["releases"] = releases
        new_content = _json.dumps(content, indent=2, ensure_ascii=False)

        # Ghi lại (PR hoặc direct)
        write_result = gh_write_file(
            token=token,
            full_name=target["full_name"],
            path=target["repo_json_path"],
            content=new_content,
            commit_message=f"chore(release): add {asset_name} for {package_id}@{version}",
            mode=mode,
        )
        repo_json_updated = True
        pr_url = write_result.get("pr_url")
    except Exception as e:
        # Không fail toàn bộ flow — chỉ log warning
        app.logger.warning(f"repo.json update failed: {e}")

    return jsonify({
        "ok": True,
        "release": {
            "id": release.get("id"),
            "tag": release.get("tag_name"),
            "html_url": release.get("html_url"),
        },
        "asset": asset,
        "download_url": asset["browser_download_url"],
        "repo_json_updated": repo_json_updated,
        "pr_url": pr_url,
    })


@app.route("/api/github/releases/<slug>")
@login_required
def api_github_releases_list(slug: str):
    """List tất cả releases của repo (cho admin xem).

    Cũng merge với releases[] trong repo.json (nếu có) để biết asset nào
    map với package nào.
    """
    owned = auth_get_owned_repos()
    target = next((r for r in owned if r.get("slug") == slug), None)
    if not target:
        return jsonify({"ok": False, "error": "Bạn không phải owner"}), 403

    from .auth import get_current_token
    token = get_current_token()
    if not token:
        return jsonify({"ok": False, "error": "Session không có token"}), 401

    from .github_release import list_releases
    releases = list_releases(token, target["full_name"])
    return jsonify({
        "ok": True,
        "slug": slug,
        "releases": releases,
        "repo_json_releases": target.get("releases", []),
    })


@app.route("/api/github/release-url/<slug>/<path:package_id>")
def api_github_release_url(slug: str, package_id: str):
    """Public endpoint (không cần auth) — trả download_url cho package.

    Strategy:
      1. Lấy repo.json từ GitHub (công khai, không cần token nếu repo public)
      2. Tìm trong releases[] của repo.json match package_id
      3. Nếu không có → fallback: list releases trên GitHub → match by filename

    Cache: 5 phút.
    """
    import time
    from .repo_discovery import _get_file_contents
    from .github_release import find_release_for_package

    cache_key = f"release_url:{slug}:{package_id}"
    cached = app.config.get(cache_key)
    cache_ts = app.config.get(cache_key + ":ts", 0)
    now = time.time()
    if cached and (now - cache_ts) < 300:
        return jsonify(cached)

    # Không có auth → dùng unauthenticated GitHub API (60 req/h, OK cho cache 5')
    import requests as _req
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "3105-repo-builder/1.0"}

    # Tìm repo theo slug
    # TODO: cần biết owner_github để query đúng repo.
    # Cách tốt nhất: search by repo.json content qua GitHub search API.
    # Tạm thời: nếu không có context, return 404.
    return jsonify({
        "ok": False,
        "error": "Cần owner_github để tìm repo. Sử dụng endpoint authenticated /api/github/releases/{slug}",
    }), 400


# ---------------------------------------------------------------------------
# Chạy
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    auto_open = os.environ.get("AUTO_OPEN_BROWSER", "1") not in ("0", "false", "False", "no", "NO")

    # Đặt stdout sang UTF-8 để in được tiếng Việt có dấu trên Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=" * 60)
    print(f"[3105 Repo Builder] dang chay tai: http://127.0.0.1:{port}")
    print(f"Thu muc repo goc: {ROOT}")
    print(f"Auto-open trinh duyet: {'bat' if auto_open else 'tat'}")
    print("Nhan Ctrl+C de dung.")
    print("=" * 60)

    if auto_open:
        def _open_browser():
            url = f"http://127.0.0.1:{port}"
            try:
                webbrowser.open(url)
                print(f"[3105 Repo Builder] da tu mo trinh duyet: {url}")
            except Exception as exc:
                print(f"[3105 Repo Builder] khong the mo trinh duyet tu dong: {exc}")
                print(f"  -> Hay tu mo: {url}")

        threading.Timer(1.0, _open_browser).start()

    # Tắt debug/reloader để không mở trình duyệt 2 lần.
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
