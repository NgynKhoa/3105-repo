#!/usr/bin/env python3
"""Local-only admin tool để quản lý các repo 3105 thay vì sửa YAML tay.

Cách chạy:
    pip install -r admin/requirements.txt
    python admin/app.py
Mở trình duyệt: http://localhost:5000
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import pathlib
import re
import sys
import threading
import webbrowser
from typing import Any

import yaml
from flask import Flask, abort, jsonify, render_template, request, send_from_directory


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

# Một số regex dùng để validate input.
IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


app = Flask(__name__, template_folder="templates", static_folder="static")


# ---------------------------------------------------------------------------
# Helper: làm việc với repo trên đĩa
# ---------------------------------------------------------------------------

# Screenshots mặc định lưu trong YAML gốc (để khôi phục anchor *screens khi save)
DEFAULT_SCREENSHOTS = [
    "assets/preview-first.png",
    "assets/preview-second.png",
    "assets/preview-third.png",
    "assets/preview-four.png",  # Lưu ý: "four" chứ không phải "fourth"!
]


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


def save_yaml(path: pathlib.Path, data: dict[str, Any]) -> None:
    """Ghi YAML không dùng anchor `&os_rules`/`&screens`.

    Lý do: anchor YAML khi convert sang JSON không tự expand,
    mà app 3105 đọc JSON sẽ không hiểu `*screens` hay `*os_rules`,
    dẫn đến crash. Mỗi package sẽ được ghi `screenshots:` và
    `supportedOS:` đầy đủ để tương thích tuyệt đối với schema JSON
    của app 3105.
    """
    lines: list[str] = []
    lines.append("# ==========================================")
    lines.append("# THÔNG TIN CHUNG CỦA REPO")
    lines.append("# ==========================================")
    lines.append("")

    # Thông tin repo
    for key in ("schemaVersion", "identifier", "name", "accentColor"):
        if key in data:
            value = data[key]
            lines.append(f"{key}: {_yaml_scalar(value)}")
    if "description" in data:
        lines.append(f"description: {_yaml_scalar(data['description'])}")
    if "icon" in data:
        lines.append(f"icon: {data['icon']}")
    lines.append("")

    lines.append("# ==========================================")
    lines.append("# DANH SÁCH PACKAGES")
    lines.append("# ==========================================")
    lines.append("")
    lines.append("packages:")
    packages = data.get("packages") or []
    for pkg in packages:
        lines.extend(_render_package_yaml(pkg))
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _yaml_scalar(value: Any, force_quoted: bool = False) -> str:
    """Quote chuỗi nếu có ký tự đặc biệt hoặc force_quoted=True.

    force_quoted dùng cho password/identifier/version để luôn giữ kiểu string.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Chuỗi số (password) hoặc force_quoted → bắt buộc quote
        if force_quoted or value.isdigit() or any(ch in value for ch in [":", "#", "&", "*", "!", "|", ">", "%", "@", "`", '"', "'", "\n"]):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value
    return str(value)


def _render_package_yaml(pkg: dict[str, Any]) -> list[str]:
    """Render một package ra danh sách các dòng YAML."""
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
    if pkg.get("password") is not None:
        # Password luôn phải là string để tránh trường hợp YAML gốc ghi số không quote.
        lines.append(f'    password: {_yaml_scalar(str(pkg["password"]), force_quoted=True)}')

    # Category + tags
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

    # Screenshots - luôn liệt kê đầy đủ để JSON sau khi convert
    # không phụ thuộc anchor (tránh crash app 3105).
    screenshots = pkg.get("screenshots") or []
    if screenshots:
        lines.append("    screenshots:")
        for shot in screenshots:
            lines.append(f"      - {shot}")

    if pkg.get("download"):
        lines.append(f"    download: {pkg['download']}")
    if pkg.get("sha256"):
        lines.append(f"    sha256: {pkg['sha256']}")
    if pkg.get("size") is not None:
        lines.append(f"    size: {pkg['size']}")

    # supportedOS - luôn ghi đầy đủ để JSON sau khi convert
    # không phụ thuộc anchor (tránh crash app 3105).
    os_rules = pkg.get("supportedOS") or DEFAULT_OS_RULES
    lines.append("    supportedOS:")
    for rule in os_rules:
        lines.append(f"      - minimum: \"{rule['minimum']}\"")
        lines.append(f"        maximum: \"{rule['maximum']}\"")
        if rule.get("builds"):
            lines.append(f"        builds: {json.dumps(rule['builds'], ensure_ascii=False)}")

    lines.append(f"    featured: {str(bool(pkg.get('featured', False))).lower()}")
    lines.append(f"    isPrivate: {str(bool(pkg.get('isPrivate', False))).lower()}")

    if pkg.get("description"):
        lines.append(f"    description: |")
        for line in str(pkg["description"]).splitlines() or [""]:
            lines.append(f"      {line}")

    if pkg.get("changelog"):
        lines.append(f"    changelog: |")
        for line in str(pkg["changelog"]).splitlines() or [""]:
            lines.append(f"      {line}")

    return lines


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
    """Trả về đường dẫn tương đối so với repo root."""
    if not directory.is_dir():
        return []
    result: list[str] = []
    for f in sorted(directory.rglob("*")):
        if f.is_file() and f.suffix.lower() in exts:
            rel = f.relative_to(REPOSITORIES_DIR.parent).as_posix()
            # rel sẽ là: repositories/demo/assets/...
            # nhưng frontend cần path tương đối so với repo root -> bỏ phần "repositories/<repo>/"
            parts = rel.split("/")
            if len(parts) >= 3:
                result.append("/".join(parts[2:]))
    return result


# ---------------------------------------------------------------------------
# Routes - trang web
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    # Đưa biến Python xuống JS dưới dạng window.* để frontend dùng được.
    bootstrap_js = (
        f"window.CATEGORIES = {json.dumps(CATEGORY_OPTIONS)};\n"
        f"window.DEFAULT_OS_RULES = {json.dumps(DEFAULT_OS_RULES)};\n"
    )
    return render_template(
        "index.html",
        bootstrap_js=bootstrap_js,
    )


@app.route("/admin/static/<path:filename>")
def admin_static(filename: str):
    return send_from_directory(app.static_folder, filename)


@app.get("/repo-asset")
def repo_asset():
    """Phục vụ ảnh asset (icon/banner/screenshot) từ repo để hiển thị thumbnail.

    Không cần thiết nếu bạn mở web qua GitHub Pages — nhưng chạy local thì tiện.
    """
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
# API
# ---------------------------------------------------------------------------

@app.get("/api/repositories")
def api_repositories():
    """Liệt kê tất cả repo con + đọc từ sources.json nếu có."""
    repos = list_repositories()
    sources: list[str] = []
    if SOURCES_FILE.is_file():
        try:
            data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
            sources = data.get("sources", [])
        except Exception:
            pass
    return jsonify({"repositories": repos, "sources": sources})


@app.get("/api/repo/<repo>/packages")
def api_list_packages(repo: str):
    paths = repo_paths(repo)
    data = load_yaml(paths["yml"])
    raw_packages = data.get("packages") or []
    # Chuẩn hoá: phát hiện package có đang dùng default OS / default screens
    # để khi ghi lại sẽ dùng anchor *os_rules / *screens cho gọn.
    shared_screens = data.get("shared_screens") or DEFAULT_SCREENSHOTS
    for pkg in raw_packages:
        pkg["__use_default_os"] = _is_default_os(pkg.get("supportedOS"))
        pkg["__use_default_screens"] = (
            isinstance(pkg.get("screenshots"), list)
            and pkg["screenshots"] == shared_screens
        )
    return jsonify({
        "repo": repo,
        "repoMeta": {
            k: data[k]
            for k in ("schemaVersion", "identifier", "name", "description", "icon", "accentColor")
            if k in data
        },
        "packages": raw_packages,
        "sharedScreens": shared_screens,
    })


def _is_default_os(rules):
    if not isinstance(rules, list) or len(rules) != len(DEFAULT_OS_RULES):
        return False
    for got, want in zip(rules, DEFAULT_OS_RULES):
        if got.get("minimum") != want["minimum"]:
            return False
        if got.get("maximum") != want["maximum"]:
            return False
        if (got.get("builds") or []) != (want.get("builds") or []):
            return False
    return True


@app.get("/api/repo/<repo>/files")
def api_files(repo: str):
    paths = repo_paths(repo)
    return jsonify({
        "assets": scan_files(paths["assets"], IMAGE_EXT),
        "packages": scan_files(paths["packages"], PACKAGE_EXT),
    })


@app.post("/api/repo/<repo>/hash")
def api_hash(repo: str):
    """Tính SHA-256 và size cho file .3105 nằm trong thư mục packages của repo."""
    paths = repo_paths(repo)
    payload = request.get_json(silent=True) or {}
    relative = payload.get("path", "")
    # Chuẩn hoá path
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

    # Validate nhẹ
    for pkg in packages:
        ident = pkg.get("identifier", "")
        if not IDENTIFIER_RE.match(ident):
            abort(400, description=f"Invalid identifier: {ident!r}")
        if not pkg.get("name"):
            abort(400, description=f"Package {ident!r} missing name")
        if not pkg.get("download"):
            abort(400, description=f"Package {ident!r} missing download path")
        if not pkg.get("sha256"):
            abort(400, description=f"Package {ident!r} missing sha256")
        if pkg.get("size") is None:
            abort(400, description=f"Package {ident!r} missing size")

    full_data = {
        "schemaVersion": repo_meta.get("schemaVersion", 1),
        "identifier": repo_meta.get("identifier", f"com.owen.{repo}"),
        "name": repo_meta.get("name", f"{repo.title()} Repository"),
        "description": repo_meta.get("description", ""),
        "icon": repo_meta.get("icon", "assets/repo-icon.png"),
        "accentColor": repo_meta.get("accentColor", "#FF3B30"),
        "__shared_os": DEFAULT_OS_RULES,
        "__shared_screens": [
            "assets/preview-first.png",
            "assets/preview-second.png",
            "assets/preview-third.png",
            "assets/preview-four.png",
        ],
        "packages": packages,
    }
    save_yaml(paths["yml"], full_data)

    return jsonify({
        "ok": True,
        "saved": str(paths["yml"].relative_to(ROOT)),
        "count": len(packages),
        "next": [
            "git add repositories/" + repo + "/repo.yml",
            "git commit -m \"feat(" + repo + "): cập nhật danh sách package\"",
            "git push",
        ],
    })


# ---------------------------------------------------------------------------
# Chạy
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Lấy port từ env nếu có
    port = int(os.environ.get("PORT", 5000))
    # Đặt stdout sang UTF-8 để in được tiếng Việt có dấu trên Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=" * 60)
    print(f"[3105 Repo Builder] dang chay tai: http://localhost:{port}")
    print(f"Thu muc repo goc: {ROOT}")
    print("Nhan Ctrl+C de dung.")
    print("=" * 60)

    # Tự động mở trình duyệt sau 1 giây (chỉ chạy 1 lần khi start).
    # Dùng daemon thread để không chặn server Flask.
    def _open_browser():
        url = f"http://localhost:{port}"
        try:
            webbrowser.open(url)
            print(f"[3105 Repo Builder] da tu mo trinh duyet: {url}")
        except Exception as exc:
            print(f"[3105 Repo Builder] khong the mo trinh duyet tu dong: {exc}")
            print(f"  -> Hay tu mo: {url}")

    threading.Timer(1.0, _open_browser).start()

    app.run(host="127.0.0.1", port=port, debug=False)
