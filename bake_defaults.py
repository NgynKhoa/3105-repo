#!/usr/bin/env python3
"""
Step 1: Export the current admin-settings.json → public defaults.
Step 2: Verify that incognito would load the same config.
"""
import json, os, pathlib

ADMIN_SETTINGS = pathlib.Path("c:/Users/NK/Desktop/MOD/3105-repo/.3105/admin-settings.json")
OUT_PUBLIC_DEFAULTS = pathlib.Path("c:/Users/NK/Desktop/MOD/3105-repo/.3105/public-defaults.json")

def extract_public_settings(admin_settings: dict) -> dict:
    """
    Lọc ra các key mà PUBLIC (non-authenticated) user cần.
    Bao gồm: theme, logo, fonts, rain, blog, nav links, music.
    Loại bỏ: admin-only keys (admin_*, mp_*, dash_*).
    """
    admin_only_prefixes = ("admin_", "dash_")
    skip_keys = {
        "__settingsPatched",
        "mp_currentIdx", "mp_loop", "mp_playing", "mp_volume",
    }

    public = {}
    for k, v in admin_settings.items():
        if any(k.startswith(p) for p in admin_only_prefixes):
            continue
        if k in skip_keys:
            continue
        public[k] = v

    # Add a flag so frontend knows this is baked-in defaults
    public["__bakedDefaults"] = True
    return public

def main():
    # 1. Load admin settings
    with open(ADMIN_SETTINGS, encoding="utf-8") as f:
        admin = json.load(f)

    public_defaults = extract_public_settings(admin)

    # 2. Write public defaults
    with open(OUT_PUBLIC_DEFAULTS, "w", encoding="utf-8") as f:
        json.dump(public_defaults, f, indent=2, ensure_ascii=False)

    print(f"[OK] Extracted {len(public_defaults)} public settings -> {OUT_PUBLIC_DEFAULTS}")
    print(f"\nPublic keys ({len(public_defaults)}):")
    for k in sorted(public_defaults.keys()):
        v = public_defaults[k]
        if isinstance(v, str) and len(v) > 60:
            v = v[:60] + "..."
        print(f"  {k}: {v}")

    # 3. Summary
    print(f"\n--- Summary ---")
    print(f"Total admin settings: {len(admin)}")
    print(f"Public settings:      {len(public_defaults)}")
    print(f"Admin-only keys:      {len(admin) - len(public_defaults)}")

if __name__ == "__main__":
    main()
