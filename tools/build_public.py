#!/usr/bin/env python3
"""Build phiên bản public (read-only) của Front Repo để deploy lên GitHub Pages.

Input:
  - admin/templates/index.html       (template Front Repo)
  - admin/static/app.js             (JS Front Repo)
  - admin/static/css/*              (CSS bundle nếu có, hoặc trong index.html)
  - repositories/demo/repo.yml      (default repo data)
  - repositories/demo/assets/*      (icon, banner, screenshot, dialer, hdr_120, ...)

Output (vào public/):
  - index.html                      (render template với bootstrap data baked-in)
  - static/*                        (mirror từ admin/static/*)
  - repo.json                       (snapshot từ repo.yml)
  - assets/                         (mirror assets/ của demo repo)
  - 404.html, .nojekyll             (copy từ public/)

Cơ chế "static-data":
  - index.html gốc fetch /api/repo/{repo}/packages + /api/blog/posts + /api/repositories
  - Build script render template với `bootstrap_js` chứa data JSON inline
  - File static/data.js sẽ override các fetch() để trả từ repo.json thay vì API

Chạy:
  python tools/build_public.py            # build mặc định repo demo
  python tools/build_public.py --repo demo --clean
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Thiếu PyYAML. Cài: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
ADMIN = ROOT / "admin"
REPOS = ROOT / "repositories"

# Cache version cho public build — bump khi Front Repo thay đổi để bust browser cache.
# KHÔNG cần sync với admin cache_version; 2 hệ thống hoàn toàn độc lập.
_CACHE_VERSION = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[build-public] {msg}", flush=True)


def copy_tree(src: Path, dst: Path, excludes: tuple[str, ...] = (".DS_Store",)) -> int:
    """Mirror src → dst (chỉ file). Trả về số file copy."""
    if not src.exists():
        return 0
    n = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if any(part in excludes for part in rel.parts):
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        n += 1
    return n


def render_index_html(repo_slug: str, repo_data: dict[str, Any]) -> str:
    """Render admin/templates/index.html với bootstrap data baked-in.

    Inject 1 <script> ngay sau <head>:
      - window.PUBLIC_REPO_DATA = { ... }   ← snapshot repo.yml
      - window.PUBLIC_REPO_SLUG = "demo"
    """
    src = ADMIN / "templates" / "index.html"
    content = src.read_text(encoding="utf-8")

    # Loại bỏ phần render_template của Flask — `{{ bootstrap_js | safe }}` sẽ
    # không có data runtime. Thay bằng inline JSON.
    #
    # QUAN TRỌNG: repo.yml có nhiều field multi-line (vd `description:` block
    # scalar trong YAML) → PyYAML trả về string chứa LITERAL newlines.
    # JSON không cho phép raw newline trong string — phải escape `\\n`.
    # Dùng `json.dumps(..., ensure_ascii=False)` rồi wrap toàn bộ payload
    # trong 1 JS template literal? KHÔNG — sẽ phá escape.
    # Cách an toàn: build bootstrap bằng cách gán từng field qua JSON.stringify
    # của chính browser khi chạy. Ở đây dump JSON đúng chuẩn rồi wrap script.
    repo_json = json.dumps(repo_data, ensure_ascii=False)
    # Sanitize: đảm bảo JSON.dump đã escape \\n, \\r, \\" etc đúng.
    # Test: nếu JSON vẫn chứa raw newline bên trong string → fix bằng cách
    # parse lại và re-dump.
    try:
        json.loads(repo_json)
    except json.JSONDecodeError:
        # Fallback: dùng PyYAML → JSON round-trip qua `force_string`
        import re as _re
        repo_json = _re.sub(r'(?<=": ")([^"\\]*?(?:\\.[^"\\]*?)*?)(?="[,}\]])',
                            lambda m: m.group(0).replace('\n', '\\n').replace('\r', '\\r'),
                            repo_json)

    bootstrap = (
        f"window.PUBLIC_REPO_SLUG = {json.dumps(repo_slug)};\n"
        f"window.PUBLIC_REPO_DATA = {repo_json};\n"
        f"window.PUBLIC_MODE = true;  // dùng data tĩnh thay vì fetch /api/*\n"
    )
    # Replace cụm {{ bootstrap_js | safe }} (Flask template) bằng script tag.
    # QUAN TRỌNG: phải dùng lambda callback thay vì string replacement — vì
    # re.sub mặc định interpret backslash escapes (\1, \n, ...) trong
    # replacement string, làm `\\n` (escaped backslash-n) trong JSON bị
    # unescape thành real newline → phá vỡ cú pháp JSON.
    content = re.sub(
        r"<script>\{\{\s*bootstrap_js\s*\|\s*safe\s*\}\}</script>",
        lambda _m: f"<script>{bootstrap}</script>",
        content,
    )
    # Nếu không match (template không còn placeholder), vẫn inject trước </head>
    if "window.PUBLIC_REPO_DATA" not in content:
        content = content.replace(
            "</head>",
            f"<script>{bootstrap}</script>\n</head>",
            1,
        )
    return content


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(repo_slug: str = "demo", clean: bool = True) -> int:
    if clean and PUBLIC.exists():
        # Xoá mọi thứ trừ README + .nojekyll + 404.html
        for f in PUBLIC.iterdir():
            if f.name in {"README.md", ".nojekyll", "404.html"}:
                continue
            if f.is_dir():
                shutil.rmtree(f)
            else:
                f.unlink()

    PUBLIC.mkdir(parents=True, exist_ok=True)

    # 1) Load repo.yml
    repo_yml = REPOS / repo_slug / "repo.yml"
    if not repo_yml.exists():
        log(f"❌ Không tìm thấy {repo_yml}")
        return 1
    repo_data = yaml.safe_load(repo_yml.read_text(encoding="utf-8")) or {}
    log(f"✓ Load {repo_yml.name} (keys: {list(repo_data.keys())})")

    # 2) Render index.html
    html = render_index_html(repo_slug, repo_data)
    # Patch hardcoded /admin/static/* → /static/* (chỉ áp dụng cho public build).
    # Dùng relative path `./static/` thay vì absolute `/static/` vì GitHub Pages
    # thường serve ở subpath (vd /3105-repo/) — absolute path sẽ 404.
    html = re.sub(r"/admin/static/", lambda _m: "./static/", html)
    # Bump cache version để browser không cache HTML cũ
    html = re.sub(r"app\.js\?v=\d+", lambda _m: "app.js?v=" + str(_CACHE_VERSION), html)
    # Đảm bảo bootstrap (window.PUBLIC_MODE = true) chạy TRƯỚC app.js,
    # vì app.js gọi api() ngay tại top-level và check window.PUBLIC_MODE.
    # Trong template gốc có thể app.js đặt trước bootstrap → fix bằng regex.
    pattern = re.compile(
        r'(<script src="\./static/app\.js\?v=\d+"></script>)\s*(<!--\s*Bootstrap.*?-->\s*)?'
        r'(<script>window\.PUBLIC[^<]+</script>)',
        re.DOTALL,
    )
    html = pattern.sub(lambda _m: _m.group(3) + "\n" + _m.group(1), html)
    # Inject <base> để mọi URL tương đối resolve đúng khi deploy ở subpath
    # (vd GitHub Pages /3105-repo/). Lấy path từ window.location.
    # KHÔNG dùng <base href="./"> vì sẽ làm relative như ./static/ ăn theo URL.
    # Dùng base href = "./" nhưng CHỈ áp dụng cho URL bắt đầu bằng "/" → cần
    # đổi thành relative. Đơn giản nhất: dùng base href trỏ đến thư mục hiện tại.
    if "<base" not in html.lower():
        html = html.replace(
            "<head>",
            '<head>\n  <base href="./">',
            1,
        )
    # Patch URL tuyệt đối trong HTML markup thành relative để hoạt động đúng
    # khi deploy ở subpath (vd GitHub Pages /3105-repo/).
    #  - /static/...    → ./static/...
    #  - /assets/...    → ./assets/...
    # KHÔNG patch /dashboard, /blog (admin routes, không public).
    def _to_relative(match):
        prefix = match.group(1)
        path = match.group(2)
        return f'{prefix}./{path}'
    # Chỉ patch path BẮT ĐẦU bằng /static/ hoặc /assets/ trong markup
    html = re.sub(r'(href="|src=")/(static|assets)/', _to_relative, html)
    # Patch JS template literal `/repo-asset?repo=...&path=...` → relative
    # `<img src="/repo-asset?...">` trong dynamicFit render packages.
    # Public build đã mirror assets/ của repo vào public/assets/ → đổi path
    # sang `./assets/<basename>` cho trực tiếp, không qua Flask endpoint.
    # pkg.icon có thể là path tương đối ("assets/icon/test.png") hoặc chỉ
    # basename ("test.png") → lấy basename qua split('/').pop().
    html = html.replace(
        '<img src="/repo-asset?repo=${encodeURIComponent(currentRepo)}&path=${encodeURIComponent(pkg.icon)}"',
        '<img src="${"./assets/" + encodeURIComponent((pkg.icon || "").split("/").pop())}"',
    )
    # Ghi file bằng bytes mode để newline JSON đã escape KHÔNG bị convert
    # thành platform newline (Windows = \r\n làm vỡ JSON string).
    (PUBLIC / "index.html").write_bytes(html.encode("utf-8"))
    log(f"✓ Render index.html ({len(html):,} bytes, cache v={_CACHE_VERSION})")

    # 3) Copy static files (admin/static → public/static) rồi patch app.js
    # để mọi URL `/repo-asset?repo=...&path=...` → `./assets/<basename>`.
    # pkg.icon có thể là path đầy đủ ("assets/icon/test.png") hoặc basename.
    n = copy_tree(ADMIN / "static", PUBLIC / "static")
    appjs = PUBLIC / "static" / "app.js"
    if appjs.exists():
        text = appjs.read_text(encoding="utf-8")
        before = text.count("/repo-asset")
        # Match cả 2 dạng:
        #   /repo-asset?repo=${encodeURIComponent(repo)}&path=${encodeURIComponent(iconPath)}
        #   /repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}
        text = re.sub(
            r'<img src="/repo-asset\?repo=\$\{encodeURIComponent\(([^)]+)\)\}&path=\$\{encodeURIComponent\(([^)]+)\)\}"',
            lambda m: f'<img src="${{"./assets/" + encodeURIComponent((({m.group(2)} || "").split("/").pop()))}}"',
            text,
        )
        text = re.sub(
            r'<img src="/repo-asset\?repo=\$\{(state\.currentRepo)\}&path=\$\{encodeURIComponent\(([^)]+)\)\}"',
            lambda m: f'<img src="${{"./assets/" + encodeURIComponent((({m.group(2)} || "").split("/").pop()))}}"',
            text,
        )
        # Cuối cùng, nếu vẫn còn /repo-asset (chỗ state.currentRepo không wrap encodeURIComponent
        # và đã được convert thành object) → fallback dùng state.currentRepo?.name || "demo"
        text = text.replace(
            '<img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(path)}"',
            '<img src="${"./assets/" + encodeURIComponent((path || "").split("/").pop())}"',
        )
        text = text.replace(
            '<img src="/repo-asset?repo=${state.currentRepo}&path=${encodeURIComponent(pkg.icon)}"',
            '<img src="${"./assets/" + encodeURIComponent((pkg.icon || "").split("/").pop())}"',
        )
        # Fallback cho mọi URL /repo-asset còn sót
        text = re.sub(
            r'<img src="/repo-asset\?[^"]*"',
            '<img src="${"./assets/" + encodeURIComponent(icon.split("/").pop())}"',
            text,
        )
        after = text.count("/repo-asset")
        appjs.write_text(text, encoding="utf-8")
        log(f"✓ Mirror admin/static → public/static ({n} files, "
            f"patched app.js: {before}→{after} /repo-asset URLs)")
    else:
        log(f"✓ Mirror admin/static → public/static ({n} files)")

    # 4) Snapshot repo.json
    (PUBLIC / "repo.json").write_text(
        json.dumps({"slug": repo_slug, "data": repo_data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"✓ Snapshot repo.json ({len(repo_data.get('packages', []))} packages, "
        f"{len(repo_data.get('blog', []))} blog posts)")

    # 5) Mirror assets — copy toàn bộ folder assets/ của repo (kể cả file không
    # được reference trong repo.yml, vì YAML có thể sai path nhưng file vẫn dùng
    # được qua /repo-asset endpoint tương ứng).
    src_assets = REPOS / repo_slug / "assets"
    dst_assets = PUBLIC / "assets"
    copied = 0
    if src_assets.exists():
        for f in src_assets.rglob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue
            rel = f.relative_to(src_assets)
            d = dst_assets / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            copied += 1
    log(f"✓ Mirror referenced assets ({copied} files copied từ {src_assets.name}/)")

    log("✅ Build xong. Test: cd public && python -m http.server 8000")
    return 0


def _collect_referenced_assets(repo: dict[str, Any]) -> set[str]:
    """Quét repo.yml, lấy tất cả path asset (icon, banner, screenshots, ...)."""
    out: set[str] = set()
    repo_icon = repo.get("icon")
    if isinstance(repo_icon, str) and "/" in repo_icon:
        out.add(repo_icon)
    screenshots = repo.get("screenshots") or []
    if isinstance(screenshots, list):
        for s in screenshots:
            if isinstance(s, str) and "/" in s:
                out.add(s)
    for pkg in repo.get("packages") or []:
        if not isinstance(pkg, dict):
            continue
        for k in ("icon", "banner", "preview", "screenshots"):
            v = pkg.get(k)
            if isinstance(v, str) and "/" in v:
                out.add(v)
            elif isinstance(v, list):
                for s in v:
                    if isinstance(s, str) and "/" in s:
                        out.add(s)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Build public/ read-only site cho GitHub Pages")
    p.add_argument("--repo", default="demo", help="slug repo trong repositories/ (default: demo)")
    p.add_argument("--no-clean", action="store_true", help="Không xoá public/ trước khi build")
    args = p.parse_args()
    return build(repo_slug=args.repo, clean=not args.no_clean)


if __name__ == "__main__":
    sys.exit(main())
