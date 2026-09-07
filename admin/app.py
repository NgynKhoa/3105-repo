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
import json
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

# Screenshots mặc định dùng chung — nếu repo có bộ ảnh khác thì anchor
# sẽ được sinh tự động theo danh sách được phát hiện.
DEFAULT_SCREENSHOTS: list[str] = [
    "assets/preview-first.png",
    "assets/preview-second.png",
    "assets/preview-third.png",
    "assets/preview-four.png",  # Lưu ý: "four" chứ không phải "fourth"!
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

    # supportedOS: anchor hoặc liệt kê
    os_rules = pkg.get("supportedOS") or DEFAULT_OS_RULES
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

    # ---- DANH SÁCH PACKAGES ----
    lines.append("# ==========================================")
    lines.append("# DANH SÁCH PACKAGES")
    lines.append("# ==========================================")
    lines.append("")
    lines.append("packages:")
    packages = data.get("packages") or []
    for idx, pkg in enumerate(packages):
        # Luôn ghi đầy đủ screenshots + supportedOS cho mỗi package
        # để JSON xuất ra không phụ thuộc anchor ở root.
        lines.extend(
            _render_package_yaml(
                pkg,
                use_anchor_os=False,
                use_anchor_screens=False,
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

@app.route("/")
def index():
    bootstrap_js = (
        f"window.CATEGORIES = {json.dumps(CATEGORY_OPTIONS)};\n"
        f"window.DEFAULT_OS_RULES = {json.dumps(DEFAULT_OS_RULES)};\n"
        f"window.DEFAULT_SCREENSHOTS = {json.dumps(DEFAULT_SCREENSHOTS)};\n"
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
        "next": [
            "git add repositories/" + repo + "/repo.yml",
            "git commit -m \"feat(" + repo + "): cập nhật danh sách package\"",
            "git push",
        ],
    })


@app.post("/api/repo/<repo>/push")
def api_push(repo: str):
    """Chạy git pull → add → commit → push cho repo đang active."""
    paths = repo_paths(repo)

    # Kiểm tra đây có phải git repo không
    git_dir = ROOT / ".git"
    if not git_dir.is_dir():
        abort(400, description="Thư mục này không phải là git repository (không tìm thấy .git ở thư mục gốc project).")

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

    # 3. Kiểm tra có thay đổi không
    code, out = _run("git", "status", "--porcelain")
    if code == 0 and not (out or "").strip():
        return jsonify({
            "ok": True,
            "step": "nothing-to-commit",
            "message": "Không có thay đổi nào để commit.",
        })

    # 4. git commit
    repo_ident = paths["yml"].read_text(encoding="utf-8")
    import yaml as _yaml
    try:
        meta = _yaml.safe_load(repo_ident) or {}
        ident = meta.get("identifier", repo)
    except Exception:
        ident = repo
    commit_msg = f"Update {ident}"
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
        "commit": commit_msg,
    })


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
