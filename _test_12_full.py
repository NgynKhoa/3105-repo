#!/usr/bin/env python3
"""Test comprehensive: tất cả checkbox, dropdown, modal, edge cases, lưu + push git."""
import sys, json, urllib.request, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"
errors = []
all_pass = True

def check(name, condition, detail=""):
    global all_pass
    status = "PASS" if condition else "FAIL"
    if not condition:
        all_pass = False
    print(f"  [{status}] {name}: {detail}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"PAGE: {e}"))

    page.goto("http://127.0.0.1:5050/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    print("=== A. Page load ===")
    check("Title", page.title() == "Owen Custom Repository — Builder", page.title())
    check("Shell exists", page.query_selector("#shell") is not None)
    check("Repo dropdown exists", page.query_selector("#repoSelect") is not None)
    check("Package list", page.eval_on_selector_all(".pkg-item", "els => els.length") > 0, "items > 0")

    print("\n=== B. Modal open/close ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    check("Modal opens", page.is_visible("#modal"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check("ESC closes modal", not page.is_visible("#modal"))

    page.click("#btnAdd")
    page.wait_for_timeout(500)
    box = page.eval_on_selector("#modal", "el => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; }")
    page.mouse.click(int(box['x'] + 30), int(box['y'] + 30))
    page.wait_for_timeout(300)
    check("Overlay click closes modal", not page.is_visible("#modal"))

    page.click("#btnAdd")
    page.wait_for_timeout(500)
    page.click("#btnCancel")
    page.wait_for_timeout(300)
    check("Cancel closes modal", not page.is_visible("#modal"))

    page.click("#btnAdd")
    page.wait_for_timeout(500)
    page.click("#btnCloseModal")
    page.wait_for_timeout(300)
    check("X button closes modal", not page.is_visible("#modal"))

    print("\n=== C. Form fields ===")
    page.click("#btnAdd")
    page.wait_for_timeout(800)
    # Count fields
    fields = page.eval_on_selector_all("#modalBody input, #modalBody select, #modalBody textarea", "els => els.length")
    check("Form has fields", fields > 30, f"{fields} fields")

    # Required fields
    req_fields = ["f_identifier", "f_name", "f_version", "f_author", "f_summary",
                   "f_category", "f_tags", "f_icon", "f_banner", "f_sha256", "f_size",
                   "f_password", "f_featured", "f_isPrivate", "f_description", "f_changelog"]
    for f in req_fields:
        check(f"Field {f} exists", page.query_selector(f"#{f}") is not None)

    print("\n=== D. Checkbox toggles ===")
    # Default OS
    check("f_use_default_os initially checked", page.is_checked("#f_use_default_os"))
    page.uncheck("#f_use_default_os")
    page.wait_for_timeout(300)
    check("iOS custom wrap visible after uncheck", page.is_visible("#f_ios_custom_wrap"))
    page.check("#f_use_default_os")
    page.wait_for_timeout(300)
    check("iOS custom wrap hidden after check", not page.is_visible("#f_ios_custom_wrap"))

    # Default screens
    check("f_use_default_screens initially checked", page.is_checked("#f_use_default_screens"))
    page.uncheck("#f_use_default_screens")
    page.wait_for_timeout(300)
    check("screensListWrap visible after uncheck", page.is_visible("#screensListWrap"))

    print("\n=== E. File combobox ===")
    page.focus("#f_download")
    page.wait_for_timeout(300)
    items = page.eval_on_selector_all("#f_download_menu .dl-item", "els => els.length")
    check("Combobox shows items on focus", items > 0, f"{items} items")
    page.fill("#f_download", "PATCH")
    page.wait_for_timeout(300)
    items = page.eval_on_selector_all("#f_download_menu .dl-item", "els => els.length")
    check("Filter 'PATCH' works", items > 0 and items < 19, f"{items} matches")

    # Auto-fill hash
    page.fill("#f_download", "")
    page.focus("#f_download")
    page.wait_for_timeout(300)
    page.click("#f_download_menu .dl-item >> nth=0")
    page.wait_for_timeout(200)
    page.click("#btnAutoFill")
    page.wait_for_timeout(800)
    sha = page.input_value("#f_sha256")
    check("SHA256 auto-filled (64 hex)", len(sha) == 64, f"{len(sha)} chars")

    print("\n=== F. Icon picker ===")
    page.click("#btnIconToggle")
    page.wait_for_timeout(500)
    items = page.eval_on_selector_all("#iconPickerGrid > *", "els => els.length")
    check("Icon grid populated", items > 0, f"{items} items")

    page.fill("#f_icon_search", "PUBG")
    page.wait_for_timeout(500)
    filtered = page.eval_on_selector_all("#iconPickerGrid > *", "els => els.length")
    check("Search 'PUBG' filters", 0 < filtered < items, f"{filtered} matches")

    page.fill("#f_icon_search", "")
    page.wait_for_timeout(300)
    page.click("#iconPickerGrid > * >> nth=0")
    page.wait_for_timeout(300)
    icon_val = page.input_value("#f_icon")
    check("Icon click sets value", bool(icon_val), icon_val)

    print("\n=== G. Banner picker ===")
    page.click("#btnBannerToggle")
    page.wait_for_timeout(500)
    items = page.eval_on_selector_all("#bannerPickerGrid > *", "els => els.length")
    check("Banner grid populated", items > 0, f"{items} items")
    page.click("#bannerPickerGrid > * >> nth=0")
    page.wait_for_timeout(300)
    banner_val = page.input_value("#f_banner")
    check("Banner click sets value", bool(banner_val), banner_val)

    print("\n=== H. Folder switcher ===")
    page.select_option("#f_icon_folder", "icon")
    page.wait_for_timeout(800)
    items = page.eval_on_selector_all("#iconPickerGrid > *", "els => els.length")
    check("Folder 'icon' has items", items > 0, f"{items} items in icon/")

    print("\n=== I. Validation - save with empty fields ===")
    page.click("#btnCloseModal")
    page.wait_for_timeout(500)
    page.click("#btnAdd")
    page.wait_for_timeout(800)
    page.click("#btnSavePackage")
    page.wait_for_timeout(800)
    toast = page.text_content("#toast")
    check("Save empty shows toast", "Thiếu" in toast or "thiếu" in toast.lower(), toast[:80])
    page.click("#btnCloseModal")
    page.wait_for_timeout(300)

    print("\n=== J. Duplicate identifier UI ===")
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    edit_btns[0].click()
    page.wait_for_timeout(800)
    page.fill("#f_identifier", "owen-001")
    page.click("#btnSavePackage")
    page.wait_for_timeout(1500)
    toast = page.text_content("#toast")
    check("Duplicate identifier caught", "tồn tại" in toast.lower() or "exists" in toast.lower(), toast[:80])
    check("Modal stays open on error", page.is_visible("#modal"))
    page.click("#btnCloseModal")
    page.wait_for_timeout(300)

    print("\n=== K. SHA256 normalize (lowercase -> uppercase) ===")
    # Check via API
    resp = urllib.request.urlopen(f"{BASE}/api/repo/demo/packages").read()
    data = json.loads(resp)
    sample = data["packages"][0]
    check("Sample sha256 is uppercase", sample["sha256"] == sample["sha256"].upper(), f"len={len(sample['sha256'])}")

    print("\n=== L. Save & push button ===")
    box_before = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight})")
    page.click("#btnSave")
    page.wait_for_timeout(300)
    box_during = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, disabled: el.disabled})")
    check("Save button not resized", abs(box_before['w'] - box_during['w']) <= 2, f"before={box_before['w']} during={box_during['w']}")
    check("Save button disabled during save", box_during['disabled'])
    page.wait_for_timeout(3000)

    print("\n=== M. Search ===")
    page.fill("#pkgSearchInput", "PUBG")
    page.wait_for_timeout(800)
    rows = page.eval_on_selector_all(".pkg-item", "els => els.length")
    check("Search 'PUBG' returns rows", rows > 0, f"{rows} rows")
    page.fill("#pkgSearchInput", "")
    page.wait_for_timeout(300)

    print("\n=== N. Pagination ===")
    page_btns = page.eval_on_selector_all("#pkgPageNumbers button", "els => els.map(b => b.textContent)")
    check("Pagination buttons", len(page_btns) > 0, f"{page_btns}")

    print("\n=== O. Reload button ===")
    page.click("#btnReload")
    page.wait_for_timeout(1500)
    items = page.eval_on_selector_all(".pkg-item", "els => els.length")
    check("Reload restores list", items > 0, f"{items} items")

    print("\n=== ERRORS ===")
    for e in errors[:15]:
        print(f"  {e}")

    browser.close()

print("\n" + "="*60)
print(f"ALL PASS: {all_pass}")
print("="*60)
