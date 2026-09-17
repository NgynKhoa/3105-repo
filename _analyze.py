import re, pathlib

# ─── Định nghĩa TẤT CẢ setting controls có trong cả 2 trang ───────────────
FRONT_SETTINGS = [
    # (key_localStorage, control_id, loai, vị trí, note)
    ("theme",           "paletteGrid",       "click/palette",   "Front ⚙️"),
    ("shadowTheme",     "paletteGrid",       "click/palette",   "Front ⚙️"),
    ("bgImage",        "bgFileInput",       "upload",          "Front ⚙️"),
    ("downloadMode",    "downloadModePicker","select",          "Front ⚙️"),
    ("rainEnabled",     "toggleRain",        "checkbox",        "Front ⚙️"),
    ("heavyRain",       "toggleHeavyRain",   "checkbox",        "Front ⚙️"),
    ("rain_volume",     "rainVolumeRange",   "range",           "Front ⚙️"),
    ("darkMode",        "toggleDarkMode",    "checkbox",        "Front ⚙️"),
    ("transparency",    "rangeTransparency","range",            "Front ⚙️"),
    ("hideAdminBg",     "toggleHideAdminBg", "checkbox",        "Front ⚙️"),
    ("admin_nav_links", "navLinksInput",     "textarea",        "Front ⚙️"),
    ("admin_playlist",  "playlistInput",     "textarea",        "Front ⚙️"),
    # Now Playing (Music Player) — trên Front Repo
    ("mp_volume",       "volRange",          "range",           "Front 🎵 Now Playing"),
    ("mp_loop",         "btnLoop",           "toggle",          "Front 🎵 Now Playing"),
    ("mp_currentIdx",   "(logic)",          "internal",        "Front 🎵 Now Playing"),
    ("mp_playing",      "(logic)",           "internal",        "Front 🎵 Now Playing"),
    # Audio URLs (rain audio file)
    ("repo_rainAudioLight","(uploaded)",    "file",            "Front ⚙️ Audio"),
    ("repo_rainAudioHeavy","(uploaded)",    "file",            "Front ⚙️ Audio"),
]

DASHBOARD_SETTINGS = [
    ("repo_theme",      "repoThemePicker",  "picker",           "Dashboard ⚙️"),
    ("repo_shadowTheme","shadowPicker",     "picker",           "Dashboard ⚙️"),
    ("repo_logoText",   "logoText",         "text",             "Dashboard LOGO"),
    ("repo_logoFont",   "logoFont",         "select",           "Dashboard LOGO"),
    ("repo_logoFontSize","logoFontSize",    "range",            "Dashboard LOGO"),
    ("repo_logoFontWeight","logoFontWeight","select",            "Dashboard LOGO"),
    ("repo_logoDepth",  "logoDepth",        "range",            "Dashboard LOGO"),
    ("repo_logoStroke", "logoStroke",       "range",            "Dashboard LOGO"),
    ("repo_logoHoloIntensity","logoHoloIntensity","range",      "Dashboard LOGO"),
    ("repo_logoGlowRadius","logoGlowRadius","range",            "Dashboard LOGO"),
    ("repo_logoGlowAlpha","logoGlowAlpha",  "range",            "Dashboard LOGO"),
    ("repo_logoBlink",  "logoBlink",        "range",            "Dashboard LOGO"),
    ("repo_logoBlinkLetters","logoBlinkLetters","text",         "Dashboard LOGO"),
    ("repo_logoAccentLetters","logoAccentLetters","text",       "Dashboard LOGO"),
    ("repo_logoAccentColor","logoAccentColor","color",          "Dashboard LOGO"),
    ("repo_pkgHeight",  "pkgHeight",        "range",            "Dashboard Box Sizes"),
    ("repo_filesHeight","filesHeight",       "range",            "Dashboard Box Sizes"),
    ("repo_blogHeight", "blogHeight",       "range",            "Dashboard Box Sizes"),
    ("repo_boxOrder",   "boxList",          "drag-drop",        "Dashboard Box Sizes"),
    ("repo_hiddenBoxes","(toggle)",         "click",            "Dashboard Box Sizes"),
    ("repo_removedBoxes","(toggle)",        "click",            "Dashboard Box Sizes"),
    ("repo_primaryFont","primaryFont",      "select",           "Dashboard Fonts"),
    ("repo_monoFont",   "monoFont",         "select",           "Dashboard Fonts"),
    ("repo_titleFont",  "titleFont",        "select",           "Dashboard Fonts"),
    ("repo_baseFontSize","baseFontSize",    "range",            "Dashboard Fonts"),
    ("repo_titleFontSize","titleFontSize",  "range",            "Dashboard Fonts"),
    ("repo_rainEnabled","toggleRain",       "checkbox",         "Dashboard Rain"),
    ("repo_heavyRain",  "toggleHeavyRain",  "checkbox",         "Dashboard Rain"),
    ("repo_rainOpacity","rainOpacity",      "range",            "Dashboard Rain"),
    ("repo_rainSpeed",  "rainSpeed",        "range",            "Dashboard Rain"),
    ("repo_rainAudioLight","(upload)",      "file",             "Dashboard Rain Audio"),
    ("repo_rainAudioHeavy","(upload)",      "file",             "Dashboard Rain Audio"),
    ("admin_playlist",  "playlistUpload",   "file",             "Dashboard Playlist"),
    ("admin_nav_links", "navLinksUpload",   "file",             "Dashboard Nav Links"),
    ("repo_previewLayout","(auto)",         "auto-save",        "Dashboard Layout"),
    ("repo_blogPosts",  "(edit blog)",      "edit",             "Dashboard Blog"),
]

# ─── Đọc file thực tế ───────────────────────────────────────────────────────
index_html = pathlib.Path("admin/templates/index.html").read_text(encoding="utf-8")
dash_html  = pathlib.Path("admin/templates/dashboard.html").read_text(encoding="utf-8")

def find_sync(key, text):
    """Tìm xem key có được setItem + sync lên GitHub không."""
    # setItem
    si = bool(re.search(rf"localStorage\.setItem\(\s*['\"]{re.escape(key)}['\"]", text))
    # sync (trong Front: syncAdminSettingsPatch, trong Dash: commitAllSettingsToGitHub)
    sync = bool(re.search(rf"(syncAdminSettingsPatch|commitAllSettingsToGitHub)\s*\(", text))
    # repo_ prefix setItem
    si_repo = bool(re.search(rf"localStorage\.setItem\(\s*['\"]({re.escape(key)})['\"]", text))
    return si, sync

def find_apply(key, text):
    """Tìm xem key có được APPLY (đọc + dùng để thay đổi UI) không."""
    patterns = [
        rf"localStorage\.getItem\(\s*['\"]({re.escape(key)})['\"]",
        rf"\b({re.escape(key)})\b(?!\s*[=:])",  # dùng biến
    ]
    hits = 0
    for p in patterns:
        hits += len(re.findall(p, text))
    return hits > 0

# ─── Tổng hợp ────────────────────────────────────────────────────────────────
all_settings = []
for key, ctrl, kind, loc in FRONT_SETTINGS:
    si, syncing = find_sync(key, index_html)
    applying = find_apply(key, index_html)
    all_settings.append((key, ctrl, kind, loc, si, syncing, applying, "index.html"))

for key, ctrl, kind, loc in DASHBOARD_SETTINGS:
    si, syncing = find_sync(key, dash_html)
    applying = find_apply(key, dash_html)
    all_settings.append((key, ctrl, kind, loc, si, syncing, applying, "dashboard.html"))

# Deduplicate (cùng key có thể xuất hiện ở cả 2)
seen = {}
for row in all_settings:
    k = row[0]
    if k not in seen:
        seen[k] = row

print("=" * 100)
print(f"📋 TỔNG HỢP: {len(seen)} settings thực tế có thể chỉnh trên Front / Dashboard")
print("=" * 100)

problems = []
for key, ctrl, kind, loc, si, syncing, applying, src in sorted(seen.values(), key=lambda x: x[3]):
    si_s  = "✅ setItem" if si else "❌ NO setItem"
    syn_s = "✅ sync" if syncing else "❌ NO sync"
    ap_s  = "✅ apply" if applying else "❌ NO apply"
    status = "OK" if (si and syncing) else ("⚠️ NO SYNC" if si else "🔴 BROKEN")
    if status != "OK":
        problems.append((key, ctrl, kind, loc, si_s, syn_s, ap_s, status))
    print(f"  [{status:10}] {key:<35} | {loc:<25} | {si_s} | {syn_s} | {ap_s}")

print()
print("=" * 100)
print(f"🔴 VẤN ĐỀ CẦN FIX: {len(problems)} settings")
print("=" * 100)
for key, ctrl, kind, loc, si_s, syn_s, ap_s, status in sorted(problems, key=lambda x: x[7], reverse=True):
    print(f"  {status}  {key:<35} ({kind}) at {loc}")
    if not si_s.startswith("✅"):
        print(f"           → {si_s} (KEY KHÔNG ĐƯỢC LƯU vào localStorage!)")
    if not syn_s.startswith("✅"):
        print(f"           → {syn_s} (KHÔNG PUSH lên GitHub!)")

print()
print("=" * 100)
print("📋 BẢNG KEY CẦN PUSH LÊN GITHUB (tất cả 60 keys)")
print("=" * 100)
all_keys = sorted(seen.keys())
for i in range(0, len(all_keys), 5):
    print("  " + "  |  ".join(f"{k:<30}" for k in all_keys[i:i+5]))
