#!/usr/bin/env python3
"""
Step 1: Export the current admin-settings.json → public defaults.
Step 2: Verify that incognito would load the same config.

Public defaults = key-value pairs mà Front Repo (anon user) cần để
render GIỐNG HỆT local dashboard (theme, rain, music, layout, fonts, ...).

Khi admin bật /api/admin-settings-merge từ local: file .3105/admin-settings.json
được update → chạy script này để re-bake.
"""
import json, os, pathlib, re, sys

ADMIN_SETTINGS      = pathlib.Path(__file__).resolve().parent / ".3105" / "admin-settings.json"
OUT_PUBLIC_DEFAULTS = pathlib.Path(__file__).resolve().parent / ".3105" / "public-defaults.json"

# Map từ Python snake_case (Flask save) sang JS camelCase (localStorage keys).
# Cả 2 dạng đều xuất hiện trong admin-settings.json. Build public chỉ chấp nhận
# JS keys (vì Front Repo đọc localStorage với tên camelCase).
_SNAKE_TO_CAMEL = {
    "admin_theme": "admin_theme",
    "shadow_theme": "shadowTheme",
    "dark_mode": "darkMode",
    "rain_enabled": "rainEnabled",
    "heavy_rain": "heavyRain",
    "bg_image": "bgImage",
    "download_mode": "downloadMode",
    "nav_links": "admin_nav_links",
    "dash_darkMode": "dash_darkMode",
    "dash_theme": "dash_theme",
    "dash_transparency": "dash_transparency",
    "repo_logoText": "repo_logoText",
    "repo_logoFont": "repo_logoFont",
    "repo_logoFontSize": "repo_logoFontSize",
    "repo_logoFontWeight": "repo_logoFontWeight",
    "repo_logoDepth": "repo_logoDepth",
    "repo_logoStroke": "repo_logoStroke",
    "repo_logoHoloIntensity": "repo_logoHoloIntensity",
    "repo_logoGlowRadius": "repo_logoGlowRadius",
    "repo_logoGlowAlpha": "repo_logoGlowAlpha",
    "repo_logoBlink": "repo_logoBlink",
    "repo_logoBlinkLetters": "repo_logoBlinkLetters",
    "repo_logoAccentLetters": "repo_logoAccentLetters",
    "repo_logoAccentColor": "repo_logoAccentColor",
    "repo_pkgHeight": "repo_pkgHeight",
    "repo_filesHeight": "repo_filesHeight",
    "repo_blogHeight": "repo_blogHeight",
    "repo_boxOrder": "repo_boxOrder",
    "repo_hiddenBoxes": "repo_hiddenBoxes",
    "repo_removedBoxes": "repo_removedBoxes",
    "repo_primaryFont": "repo_primaryFont",
    "repo_monoFont": "repo_monoFont",
    "repo_titleFont": "repo_titleFont",
    "repo_baseFontSize": "repo_baseFontSize",
    "repo_titleFontSize": "repo_titleFontSize",
    "repo_rainEnabled": "repo_rainEnabled",
    "repo_heavyRain": "repo_heavyRain",
    "repo_rainOpacity": "repo_rainOpacity",
    "repo_rainSpeed": "repo_rainSpeed",
    "rain_volume": "rain_volume",
    "repo_rainAudioLight": "repo_rainAudioLight",
    "repo_rainAudioHeavy": "repo_rainAudioHeavy",
    "admin_rainAudio": "admin_rainAudio",
    "admin_playlist": "admin_playlist",
    "mp_currentIdx": "mp_currentIdx",
    "mp_loop": "mp_loop",
    "mp_volume": "mp_volume",
    "repo_blogPosts": "repo_blogPosts",
    "repo_blog_updated": "repo_blog_updated",
    "repo_previewLayout": "repo_previewLayout",
    "repo_theme": "repo_theme",
    "repo_shadowTheme": "repo_shadowTheme",
    "repo_transparency": "repo_transparency",
}

# Keys hoàn toàn là camelCase (JS) — KHÔNG nằm trong snake map. Giữ nguyên tên.
_CAMEL_KEYS = {
    "theme", "admin_theme", "transparency", "transparency_dark", "transparency_light",
    "shadowTheme", "darkMode", "rainEnabled", "heavyRain", "bgImage",
    "currentRepo", "repo_lang",
}

# Admin-only / private keys không bao giờ bake ra Pages.
ADMIN_ONLY_PREFIXES = ("admin_", "dash_")
SKIP_KEYS = {
    "__settingsPatched",
    "__bakedDefaults",
    "mp_playing",
}


def extract_public_settings(admin_settings: dict) -> dict:
    """Lấy ra các public key + chuẩn hoá về camelCase.

    Quy tắc:
      - Nếu key nằm trong `_SNAKE_TO_CAMEL` (mapping Python→JS): bake dưới tên JS,
        BỎ QUA bản Python.
      - Nếu key đã là camelCase (nằm trong `_CAMEL_KEYS`): giữ nguyên.
      - Nếu key bắt đầu bằng 'admin_'/'dash_': skip (admin-only).
      - Các key còn lại: giữ nguyên + log warning để admin biết.
    """
    public = {}

    # Pass 1: bake các JS (camelCase) keys thẳng
    for k in _CAMEL_KEYS:
        if k in admin_settings:
            v = admin_settings[k]
            if v is None or v == "" or v == [] or v == {}:
                continue
            public[k] = v

    # Pass 2: bake snake_case keys (mapped sang camelCase)
    for snake_key, js_key in _SNAKE_TO_CAMEL.items():
        if snake_key in admin_settings:
            v = admin_settings[snake_key]
            # Bỏ None / empty / "0" string (sẽ ràng buộc frontend set default)
            if v is None or v == "" or v == [] or v == {}:
                continue
            # Luôn ghi đè JS key (ưu tiên Python key, vì Flask save admin-settings
            # là source of truth).
            public[js_key] = v

    # Pass 3: cảnh báo + giữ keys chưa được phân loại
    classified = _CAMEL_KEYS | set(_SNAKE_TO_CAMEL.keys()) | SKIP_KEYS
    for k in admin_settings:
        if k in classified:
            continue
        if any(k.startswith(p) for p in ADMIN_ONLY_PREFIXES):
            continue
        # Unknown key → giữ lại + log
        v = admin_settings[k]
        if v is None or v == "":
            continue
        public[k] = v
        print(f"  [warn] unknown key {k!r} baked as-is (size={len(str(v))})", file=sys.stderr)

    # Marker cho frontend biết đây là baked defaults
    public["__bakedDefaults"] = True
    return public


def main():
    if not ADMIN_SETTINGS.exists():
        print(f"[ERR] {ADMIN_SETTINGS} not found", file=sys.stderr)
        sys.exit(1)

    # 1. Load admin settings
    with open(ADMIN_SETTINGS, encoding="utf-8") as f:
        admin = json.load(f)

    public_defaults = extract_public_settings(admin)

    # 2. Write public defaults
    OUT_PUBLIC_DEFAULTS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PUBLIC_DEFAULTS, "w", encoding="utf-8") as f:
        json.dump(public_defaults, f, indent=2, ensure_ascii=False)

    print(f"[OK] Extracted {len(public_defaults)} public settings")
    print(f"  src : {ADMIN_SETTINGS}")
    print(f"  out : {OUT_PUBLIC_DEFAULTS}")
    print()
    print(f"Public keys ({len(public_defaults)}):")
    for k in sorted(public_defaults.keys()):
        v = public_defaults[k]
        if isinstance(v, str) and len(v) > 60:
            v = v[:60] + "..."
        if isinstance(v, (dict, list)):
            v = type(v).__name__ + f"(len={len(v)})"
        print(f"  {k:36} = {v}")

    # 3. Summary
    print()
    print("--- Summary ---")
    print(f"Total admin settings:   {len(admin)}")
    print(f"Public (deduplicated):  {len(public_defaults)}")


if __name__ == "__main__":
    main()
