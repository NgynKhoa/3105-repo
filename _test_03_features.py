#!/usr/bin/env python3
"""Test: search, pagination, checkbox, combobox file, dropdown."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"PAGE: {e}"))

    page.goto("http://127.0.0.1:5050/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    # TEST: Search
    print("=== TEST: Search ===")
    page.fill("#pkgSearchInput", "PUBG")
    page.wait_for_timeout(800)
    rows = page.eval_on_selector_all(".pkg-item", "els => els.length")
    print(f"  Rows matching 'PUBG': {rows}")
    page.fill("#pkgSearchInput", "")
    page.wait_for_timeout(500)

    # TEST: Pagination - 14 packages / 5 per page = 3 pages
    print("\n=== TEST: Pagination ===")
    # Check page number buttons
    page_btns = page.eval_on_selector_all("#pkgPageNumbers button", "els => els.map(b => b.textContent)")
    print(f"  Page number buttons: {page_btns}")
    # Click page 2
    if len(page_btns) >= 2:
        page.click("#pkgPageNumbers button:nth-child(2)")
        page.wait_for_timeout(500)
        rows_p2 = page.eval_on_selector_all(".pkg-item", "els => els.length")
        print(f"  Rows on page 2: {rows_p2}")

    # Back to page 1
    page.click("#pkgPageNumbers button:nth-child(1)")
    page.wait_for_timeout(500)

    # TEST: Open modal Add + check checkbox default
    print("\n=== TEST: Modal Add checkboxes ===")
    page.click("#btnAdd")
    page.wait_for_timeout(800)

    # Check checkbox "Dùng screenshot mặc định" — default true
    use_screens = page.is_checked("#f_use_default_screens")
    print(f"  f_use_default_screens: {use_screens}")

    # Check checkbox "Dùng iOS rule mặc định"
    use_os = page.is_checked("#f_use_default_os")
    print(f"  f_use_default_os: {use_os}")

    # Click "Dùng screenshot mặc định" OFF → panel screenshot phải hiện ra
    page.uncheck("#f_use_default_screens")
    page.wait_for_timeout(500)
    screens_visible = page.is_visible("#screensListWrap")
    print(f"  screensListWrap visible after uncheck: {screens_visible}")

    # Check back
    page.check("#f_use_default_screens")
    page.wait_for_timeout(500)
    screens_visible = page.is_visible("#screensListWrap")
    print(f"  screensListWrap visible after check: {screens_visible}")

    # Toggle iOS rule off
    page.uncheck("#f_use_default_os")
    page.wait_for_timeout(500)
    ios_wrap_visible = page.is_visible("#f_ios_custom_wrap")
    print(f"  f_ios_custom_wrap visible: {ios_wrap_visible}")
    # Kiểm tra xem có select os_min/os_max không
    has_ios_min = page.query_selector("#f_ios_min") is not None
    has_ios_max = page.query_selector("#f_ios_max") is not None
    print(f"  Has ios_min: {has_ios_min}, has_ios_max: {has_ios_max}")

    # Test combobox file .3105
    print("\n=== TEST: Combobox file .3105 ===")
    page.fill("#f_download", "PATCH")
    page.wait_for_timeout(500)
    menu_visible = page.is_visible("#f_download_menu")
    print(f"  Menu visible: {menu_visible}")
    if menu_visible:
        items = page.eval_on_selector_all("#f_download_menu div", "els => els.map(e => e.textContent)")
        print(f"  Menu items ({len(items)}): {items[:5]}")

    page.click("#btnCloseModal")
    page.wait_for_timeout(500)

    # Test nút Lưu (Save) -> save repoMeta only
    print("\n=== TEST: Save meta ===")
    # Sửa tên repo để test
    page.fill("#meta_name", "Owen Custom Repository TEST")
    page.wait_for_timeout(300)
    page.click("#btnSave")
    page.wait_for_timeout(1500)
    toast = page.text_content("#toast")
    print(f"  Toast: '{toast}'")

    # Đợi xong rồi revert
    page.fill("#meta_name", "Owen Custom Repository")
    page.click("#btnSave")
    page.wait_for_timeout(1500)

    print("\n=== ERRORS ===")
    for e in errors[:10]:
        print(f"  {e}")
    browser.close()
print("DONE")
