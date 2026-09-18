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
import os
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


def load_admin_settings(repo_slug: str) -> dict:
    """Load .3105/admin-settings.json từ repo (dùng cho build public).

    Returns dict rỗng nếu không tìm thấy (admin chưa từng lưu settings).
    File thực sự nằm ở repo ROOT (.3105/admin-settings.json) theo
    `admin_settings.ADMIN_SETTINGS_PATH` — KHÔNG phải trong repositories/<slug>/.
    """
    p = ROOT / ".3105" / "admin-settings.json"
    if not p.is_file():
        return {}
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_blog_posts() -> list:
    """Load blog posts từ admin/templates/_blog_posts.json.

    File này admin (Flask UI) quản lý qua /admin dashboard — không có trên
    repo.yml → cần đọc riêng và bake vào PUBLIC_REPO_DATA.blog.
    """
    p = ADMIN / "templates" / "_blog_posts.json"
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


# Cache version cho public build — bump khi Front Repo thay đổi để bust browser cache.
# KHÔNG cần sync với admin cache_version; 2 hệ thống hoàn toàn độc lập.
_CACHE_VERSION = 9


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


def render_index_html(repo_slug: str, repo_data: dict[str, Any], owner: bool = False,
                     owner_github: str = "", nav_links: list | None = None,
                     public_playlist: list | None = None,
                     admin_settings: dict | None = None) -> str:
    """Render admin/templates/index.html với bootstrap data baked-in.

    Inject 1 <script> ngay sau <head>:
      - window.PUBLIC_REPO_DATA = { ... }   ← snapshot repo.yml
      - window.PUBLIC_REPO_SLUG = "demo"
      - window.PUBLIC_NAV_LINKS = [...]    ← admin links (tùy chọn)
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

    # Theme-related settings từ .3105/public-defaults.json → bake vào public
    # để user bình thường (không phải admin) cũng thấy theme admin đã chọn.
    #
    # public-defaults.json được tạo bởi bake_defaults.py: filter + camelCase +
    # no duplicates. File này là SOURCE OF TRUTH cho build.
    public_theme = None
    public_defaults_path = ROOT / ".3105" / "public-defaults.json"
    if public_defaults_path.is_file():
        try:
            with public_defaults_path.open(encoding="utf-8") as _f:
                _baked = json.load(_f)
            if isinstance(_baked, dict):
                # Loại bỏ marker internal
                _baked.pop("__bakedDefaults", None)
                public_theme = _baked
                log(f"✓ Load {len(public_theme)} public defaults từ public-defaults.json")
        except (OSError, ValueError) as _e:
            log(f"⚠ public-defaults.json lỗi: {_e}")
    if public_theme is None and isinstance(admin_settings, dict):
        # Fallback: chưa chạy bake_defaults.py → tự trích từ admin-settings
        # (giữ logic cũ để không break nếu ai đó build mà quên bake).
        _github_to_js = {
            "shadow_theme": "shadowTheme", "dark_mode": "darkMode",
            "rain_enabled": "rainEnabled", "heavy_rain": "heavyRain",
            "bg_image": "bgImage", "download_mode": "downloadMode",
            "nav_links": "admin_nav_links",
        }
        _js_keys = (
            "theme", "admin_theme", "shadowTheme", "admin_shadowTheme",
            "darkMode", "dash_darkMode", "dash_theme",
            "transparency", "dash_transparency", "transparency_dark",
            "transparency_light", "bgImage", "hideAdminBg",
            "repo_logoText", "repo_logoFont", "repo_logoFontSize",
            "repo_logoFontWeight", "repo_logoDepth", "repo_logoStroke",
            "repo_logoHoloIntensity", "repo_logoGlowRadius", "repo_logoGlowAlpha",
            "repo_logoBlink", "repo_logoBlinkLetters",
            "repo_logoAccentLetters", "repo_logoAccentColor",
            "repo_box_<boxkey>_height", "repo_box_<boxkey>_width",
            "repo_pkgHeight", "repo_filesHeight", "repo_blogHeight",
            "repo_boxOrder", "repo_hiddenBoxes", "repo_removedBoxes",
            # Box size settings (height + width per box) - injected via flat keys
            "repo_box_masthead_height", "repo_box_masthead_width",
            "repo_box_hello-banner_height", "repo_box_hello-banner_width",
            "repo_box_meta_height", "repo_box_meta_width",
            "repo_box_packages_height", "repo_box_packages_width",
            "repo_box_blog-section_height", "repo_box_blog-section_width",
            "repo_box_stars_height", "repo_box_stars_width",
            "repo_box_music-player_height", "repo_box_music-player_width",
            "repo_box_moon-widget_height", "repo_box_moon-widget_width",
            "repo_box_hint-box_height", "repo_box_hint-box_width",
            "repo_primaryFont", "repo_monoFont", "repo_titleFont",
            "repo_baseFontSize", "repo_titleFontSize",
            "repo_rainEnabled", "rainEnabled", "repo_heavyRain", "heavyRain",
            "repo_rainOpacity", "repo_rainSpeed", "rain_volume",
            "repo_rainAudioLight", "repo_rainAudioHeavy", "admin_rainAudio",
            "admin_playlist", "admin_nav_links",
            "mp_currentIdx", "mp_loop", "mp_volume",
            "repo_blogPosts", "repo_blog_updated",
            "repo_previewLayout", "repo_theme", "repo_shadowTheme",
            "currentRepo",
        )
        _extracted = {}
        for k in _js_keys:
            if k in admin_settings:
                _extracted[k] = admin_settings[k]
        for gh_key, js_key in _github_to_js.items():
            if gh_key in admin_settings:
                _extracted[js_key] = admin_settings[gh_key]
        if _extracted:
            public_theme = _extracted

    # PUBLIC_REPO_OWNER_GITHUB: GitHub username của owner (vd "NgynKhoa")
    # PUBLIC_REPO_NAME: tên GH repo chứa packages (vd "3105-repo")
    # Mặc định lấy từ --owner-github hoặc env GITHUB_DEFAULT_OWNER / GITHUB_REPO_NAME.
    gh_owner = owner_github or os.environ.get("GITHUB_DEFAULT_OWNER", "NgynKhoa")
    gh_repo_name = os.environ.get("GITHUB_REPO_NAME", "3105-repo")

    # Constants dùng bởi app.js (ADMIN UI helpers — category dropdown, OS rules,
    # screenshots). Cũng cần cho Front Repo để Admin Dashboard render đúng.
    # Giá trị phải KHỚP với app.py DEFAULT_* để build = local.
    _CATEGORIES = [
        "Customization", "Enhancement", "Wallpaper", "Dialer",
        "Display", "Utility", "Game",
    ]
    _OS_RULES = [
        {"minimum": "17.0", "maximum": "18.7.1"},
        {"minimum": "26.0", "maximum": "26.6.1"},
        {"minimum": "27.0", "maximum": "27.0",
         "builds": ["24A5355q", "24A5370h", "24A5380h", "24A5390f"]},
    ]
    _SCREENSHOTS = [
        "assets/preview/preview-first.png",
        "assets/preview/preview-second.png",
        "assets/preview/preview-third.png",
        "assets/preview/preview-fourth.png",
    ]

    bootstrap = (
        f"window.CATEGORIES = {json.dumps(_CATEGORIES)};\n"
        f"window.DEFAULT_OS_RULES = {json.dumps(_OS_RULES)};\n"
        f"window.DEFAULT_SCREENSHOTS = {json.dumps(_SCREENSHOTS)};\n"
        f"window.PUBLIC_REPO_SLUG = {json.dumps(repo_slug)};\n"
        f"window.PUBLIC_REPO_DATA = {repo_json};\n"
        f"window.PUBLIC_REPO_OWNER = {json.dumps(bool(owner))};\n"
        f"window.PUBLIC_REPO_OWNER_GITHUB = {json.dumps(gh_owner)};\n"
        f"window.PUBLIC_REPO_NAME = {json.dumps(gh_repo_name)};\n"
        f"window.PUBLIC_REPO_DEFAULT_BRANCH = {json.dumps('main')};\n"
        f"window.PUBLIC_MODE = true;  // dùng data tĩnh thay vì fetch /api/*\n"
        f"window.PUBLIC_NAV_LINKS = {json.dumps(nav_links or [], ensure_ascii=False)};\n"
        # Playlist từ admin-settings.json (cho người dùng ẩn danh xem được trên GH Pages)
        f"window.PUBLIC_PLAYLIST = {json.dumps(public_playlist or [], ensure_ascii=False)};\n"
        # Theme/shadow/bg/dark/transparency từ admin-settings.json → user thấy
        f"window.PUBLIC_ADMIN_THEME = {json.dumps(public_theme or {{}}, ensure_ascii=False)};\n"
        # CRITICAL: ghi TẤT CẢ public_theme key vào localStorage NGAY
        # để TrackPlayer / Music Player / Rain audio đọc localStorage (module-level)
        # mà không cần biết PUBLIC_ADMIN_THEME tồn tại. Anonymous user có
        # localStorage rỗng → script này seed đầy đủ từ bake data.
        f"try {{ var _pat={json.dumps(public_theme or {{}}, ensure_ascii=False)};"
        f"Object.keys(_pat).forEach(function(k){{"
        f"if(localStorage.getItem(k)===null)localStorage.setItem(k,String(_pat[k]));}});"
        f"}} catch(e){{}}\n"
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

def build(repo_slug: str = "demo", clean: bool = True, owner: bool = False,
         owner_github: str = "") -> int:
    # Resolve GitHub owner/repo mặc định để bake vào PUBLIC_REPO_OWNER_GITHUB
    # + PUBLIC_REPO_NAME — tránh Strategy 4 fallback sai khi admin chạy build
    # mà KHÔNG truyền --owner-github (CI auto-build từ workflow cũng vậy).
    gh_owner = owner_github or os.environ.get("GITHUB_DEFAULT_OWNER", "NgynKhoa")
    gh_repo_name = os.environ.get("GITHUB_REPO_NAME", "3105-repo")
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

    # 1b) Load admin settings (chứa nav_links nếu admin đã cấu hình)
    admin_settings = load_admin_settings(repo_slug)
    nav_links = admin_settings.get("nav_links") if isinstance(admin_settings, dict) else None
    if isinstance(nav_links, list) and nav_links:
        log(f"✓ Load {len(nav_links)} nav_links từ admin-settings.json")
    else:
        nav_links = None  # dùng default trong index.html

    # 1c) Load playlist (cho Now Playing trên GH Pages)
    public_playlist = None
    if isinstance(admin_settings, dict):
        pl = admin_settings.get("playlist")
        if isinstance(pl, list) and pl:
            public_playlist = pl
            log(f"✓ Load {len(public_playlist)} tracks từ admin-settings.json")

    # 1d) Load blog posts (admin/templates/_blog_posts.json — admin Flask quản lý)
    # Bake vào repo_data.blog để PUBLIC_REPO_DATA.blog + public/repo.json có data.
    blog_posts = load_blog_posts()
    if blog_posts:
        repo_data["blog"] = blog_posts
        log(f"✓ Load {len(blog_posts)} blog posts từ _blog_posts.json")

    # 2) Render index.html
    html = render_index_html(repo_slug, repo_data, owner=owner, owner_github=owner_github,
                             nav_links=nav_links, public_playlist=public_playlist,
                             admin_settings=admin_settings)
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
    # Public build đã mirror assets/ của repo vào public/assets/. Logic:
    #   pkg.icon = "assets/icon/Classic_dialer.png"
    #   split("assets/").pop() = "icon/Classic_dialer.png"
    #   prefix "./assets/" → "./assets/icon/Classic_dialer.png" (đúng subdir).
    html = html.replace(
        '<img src="/repo-asset?repo=${encodeURIComponent(currentRepo)}&path=${encodeURIComponent(pkg.icon)}"',
        '<img src="${"./assets/" + encodeURIComponent((pkg.icon || "").split("assets/").pop() || pkg.icon.split("/").pop())}"',
    )
    # Trên static hosting (GH Pages), /auth/* không tồn tại. fetchAuthState()
    # sẽ phát hiện và gọi hideLoginForStatic(). Inject sớm để tránh flash.
    if not owner and "/auth/github/login" not in html:
        # Inject 1 lần ngay sau <body> để ẩn #authGroup trước khi render.
        # Dùng inline script (không qua fetch) để chạy được cả khi offline.
        inject = (
            '<script>(function(){'
            '  if (window.PUBLIC_MODE && !window.PUBLIC_REPO_OWNER) {'
            '    var g = document.getElementById("authGroup");'
            '    if (g) g.style.display = "none";'
            '  }'
            '})();</script>'
        )
        html = html.replace("<body>", "<body>\n  " + inject, 1)
    # Ghi file bằng bytes mode để newline JSON đã escape KHÔNG bị convert
    # thành platform newline (Windows = \r\n làm vỡ JSON string).
    (PUBLIC / "index.html").write_bytes(html.encode("utf-8"))
    log(f"✓ Render index.html ({len(html):,} bytes, cache v={_CACHE_VERSION})")

    # 3) Copy static files (admin/static → public/static) rồi patch app.js
    # để mọi URL `/repo-asset?repo=...&path=...` → `./assets/<relative path>`.
    # pkg.icon có thể là path đầy đủ ("assets/icon/test.png") — giữ nguyên
    # phần relative sau "assets/" để file nằm đúng subdir.
    # Logic: split path trên "assets/" rồi lấy phần sau. Nếu không có "assets/"
    # thì coi như filename, prefix "./assets/" thẳng.
    n = copy_tree(ADMIN / "static", PUBLIC / "static")
    appjs = PUBLIC / "static" / "app.js"
    if appjs.exists():
        text = appjs.read_text(encoding="utf-8")
        before = text.count("/repo-asset")
        # Helper JS expression: lấy relative path sau "assets/" (hoặc basename).
        # Áp dụng được cho mọi iconPath/path/pkg.icon khác nhau.
        def expr(var: str) -> str:
            return (f'"./assets/" + (({var}.split("assets/").pop() || '
                    f'{var}.split("/").pop()) || "")')
        # Pattern 1: state.currentRepo + encodeURIComponent(path)
        text = re.sub(
            r'<img src="/repo-asset\?repo=\$\{(state\.currentRepo)\}&path=\$\{encodeURIComponent\(([^)]+)\)\}"',
            lambda m: f'<img src="${{{expr(m.group(2))}}}"',
            text,
        )
        # Pattern 2: encodeURIComponent(repo) + encodeURIComponent(path)
        text = re.sub(
            r'<img src="/repo-asset\?repo=\$\{encodeURIComponent\(([^)]+)\)\}&path=\$\{encodeURIComponent\(([^)]+)\)\}"',
            lambda m: f'<img src="${{{expr(m.group(2))}}}"',
            text,
        )
        # Pattern 3: chỉ /repo-asset?repo=...&path=... (fallback cho mọi chỗ còn lại)
        text = re.sub(
            r'<img src="/repo-asset\?repo=[^&"]+&path=\$\{encodeURIComponent\(([^)]+)\)\}"',
            lambda m: f'<img src="${{{expr(m.group(1))}}}"',
            text,
        )
        # Cuối cùng: bất kỳ URL /repo-asset nào còn lại → fallback empty icon
        text = re.sub(
            r'<img src="/repo-asset\?[^"]*"',
            '<img src="${"./assets/" + (iconPath || "").split("assets/").pop()}"',
            text,
        )
        after = text.count("/repo-asset")
        appjs.write_text(text, encoding="utf-8")
        log(f"✓ Mirror admin/static → public/static ({n} files, "
            f"patched app.js: {before}→{after} /repo-asset URLs)")
    else:
        log(f"✓ Mirror admin/static → public/static ({n} files)")

    # 4) Snapshot repo.json
    # Đảm bảo các key optional (blog, ...) luôn tồn tại để tránh KeyError
    # ở downstream như GitHub Actions kiểm tra d['data']['blog'].
    snapshot_data = dict(repo_data)
    snapshot_data.setdefault('blog', [])
    (PUBLIC / "repo.json").write_text(
        json.dumps({"slug": repo_slug, "data": snapshot_data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"✓ Snapshot repo.json ({len(snapshot_data.get('packages', []))} packages, "
        f"{len(snapshot_data.get('blog', []))} blog posts)")

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

    # 5b) Mirror root-level assets/blog/ → public/assets/blog/
    # Admin upload blog cover/gallery vào assets/blog/ ở root (không phải
    # repositories/demo/assets/blog). Pages cần file này để render blog cover.
    src_blog_assets = ROOT / "assets" / "blog"
    if src_blog_assets.exists():
        blog_copied = 0
        for f in src_blog_assets.rglob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue
            rel = f.relative_to(src_blog_assets)
            d = PUBLIC / "assets" / "blog" / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            blog_copied += 1
        log(f"✓ Mirror blog assets ({blog_copied} files copied từ assets/blog/)")

    # 5c) Mirror root-level AUDIO files (assets/rain.mp3, assets/rain_heavy.mp3, ...)
    # vào public/assets/ để rain player trên GH Pages phát được.
    #
    # Lý do: Front Repo JS cố định load từ `/assets/rain.mp3` (xem
    # admin/templates/index.html initLight/initHeavy), và admin có thể đã
    # upload URL khác qua Dashboard → nhưng default vẫn cần file tồn tại ở
    # public/assets/. Nếu localStorage của user chưa có URL custom thì
    # <audio src="/assets/rain.mp3"> sẽ 404 trên Pages → không có tiếng mưa.
    #
    # SYNC_INCLUDE_PATHS của admin/sync.py cũng liệt kê "assets/" rồi
    # nhưng trong build_public.py trước đây CHỈ mirror assets/<repo>/, không
    # mirror file audio ở root. Fix: copy các file trực tiếp dưới assets/ (không
    # vào folder con) sang public/assets/ để giữ URL `/assets/<filename>` hoạt động.
    src_root_assets = ROOT / "assets"
    if src_root_assets.exists():
        audio_exts = {".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac"}
        audio_copied = 0
        for f in src_root_assets.iterdir():
            # Chỉ copy FILE trực tiếp dưới assets/ (không đệ quy) — tránh
            # đè assets/blog/ đã được mirror ở 5b).
            if not f.is_file() or f.name.startswith("."):
                continue
            if f.suffix.lower() not in audio_exts:
                continue
            d = PUBLIC / "assets" / f.name
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            audio_copied += 1
        log(f"✓ Mirror root audio assets ({audio_copied} file copied từ assets/*.{{mp3,ogg,wav,m4a,aac,flac}})")

    # 6) Render blog.html (trang bài viết chi tiết) cho public mode.
    # User click blog item trên public site → sang ./blog.html?id=<id>
    # vì Flask /blog-post/<id> không có trên GH Pages.
    blog_html_src = ADMIN / "templates" / "blog.html"
    if blog_html_src.exists():
        blog_html = blog_html_src.read_text(encoding="utf-8")
        # Inject PUBLIC_MODE + PUBLIC_REPO_DATA bootstrap đầu trang
        # (loadPosts() cần window.PUBLIC_REPO_DATA.blog để render).
        # Check bằng <script>PUBLIC_MODE để tránh false-positive với comment
        # trong source (vd "// GH Pages: window.PUBLIC_MODE...").
        if "<script>window.PUBLIC_MODE" not in blog_html:
            # Tái tạo bootstrap từ repo_data (đã load ở bước 1).
            # Escape JSON string an toàn: dùng json.dumps đã chuẩn hoá.
            blog_bootstrap = (
                f"window.PUBLIC_REPO_SLUG = {json.dumps(repo_slug)};\n"
                f"window.PUBLIC_REPO_DATA = {json.dumps(repo_data, ensure_ascii=False)};\n"
                f"window.PUBLIC_REPO_OWNER = {json.dumps(bool(owner))};\n"
                f"window.PUBLIC_REPO_OWNER_GITHUB = {json.dumps(gh_owner)};\n"
                f"window.PUBLIC_REPO_NAME = {json.dumps(gh_repo_name)};\n"
                f"window.PUBLIC_MODE = true;\n"
            )
            blog_html = blog_html.replace(
                "</head>",
                f"<script>{blog_bootstrap}</script>\n</head>",
                1,
            )
        # Patch URLs tương tự index.html
        blog_html = re.sub(r"/admin/static/", lambda _m: "./static/", blog_html)
        if "<base" not in blog_html.lower():
            blog_html = blog_html.replace(
                "<head>",
                '<head>\n  <base href="./">',
                1,
            )
        blog_html = re.sub(r'(href="|src=")/(static|assets)/', _to_relative, blog_html)
        # Patch /api/* fetch sang noop (không tồn tại trên GH Pages)
        blog_html = blog_html.replace(
            "fetch('/api/blog/posts')",
            "(window.PUBLIC_MODE ? Promise.resolve({posts: (window.PUBLIC_REPO_DATA?.blog || [])}) : fetch('/api/blog/posts'))",
        )
        # Link trong blog list: /blog-post/X → ./blog.html?id=X ở public mode
        blog_html = blog_html.replace(
            '<a href="/blog-post/${p.id}"',
            '<a href="${window.PUBLIC_MODE ? `./blog.html?id=${p.id}` : `/blog-post/${p.id}`}"',
        )
        (PUBLIC / "blog.html").write_text(blog_html, encoding="utf-8")
        log("✓ Render blog.html (public mode)")
    else:
        log("⚠ blog.html not found, skipping")

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
    p.add_argument("--owner", action="store_true",
                   help="Đánh dấu build này là của chủ repo: hiện theme/shadow/logo color "
                        "picker, Admin Dashboard link, nút Sửa/Xóa packages, cho phép "
                        "sửa Thông tin chung. Mặc định KHÔNG bật → user thường chỉ xem.")
    p.add_argument("--owner-github", default="",
                   help="GitHub username của owner (vd 'YangJii'). Dùng cho public "
                        "release lookup API khi user thường click 'Tìm' trên package.")
    args = p.parse_args()
    return build(repo_slug=args.repo, clean=not args.no_clean, owner=args.owner,
                 owner_github=args.owner_github)


if __name__ == "__main__":
    sys.exit(main())
