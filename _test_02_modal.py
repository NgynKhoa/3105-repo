#!/usr/bin/env python3
"""Playwright test - Test modal và form thêm package."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

errors = []
warnings = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()

    page.on("console", lambda msg: (errors.append(msg.text) if msg.type == "error" else warnings.append(msg.text)))
    page.on("pageerror", lambda err: errors.append(f"PAGEERROR: {err}"))

    print("=== LOAD PAGE ===")
    page.goto("http://127.0.0.1:5050/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # Mở modal "Add"
    print("\n=== TEST: Open modal Add ===")
    page.click("#btnAdd")
    page.wait_for_timeout(1000)

    if not page.is_visible("#modal"):
        print("FAIL: modal không mở")
        sys.exit(1)

    # Đếm fields
    fields = page.eval_on_selector_all("#modalBody input, #modalBody select, #modalBody textarea", "els => els.length")
    print(f"Total form fields: {fields}")

    # Các field IDs
    field_ids = page.eval_on_selector_all("#modalBody [id]", "els => els.map(e => e.id).filter(Boolean)")
    print(f"Field IDs: {field_ids}")

    # Check default values
    print("\n=== TEST: Default values ===")
    defaults = {
        "f_identifier": "owen-XXX",
        "f_name": "",
        "f_version": "1.0.0",
        "f_author": "@owenindahouse",
        "f_category": "Customization",
        "f_summary": "",
    }
    for fid, expected in defaults.items():
        val = page.input_value(f"#{fid}")
        print(f"  {fid:30s} = '{val}' (expected: {expected})")

    # Screenshot
    page.screenshot(path="_test_02_modal.png", full_page=True)
    print("\nScreenshot saved: _test_02_modal.png")

    # Test bấm Lưu khi chưa điền gì -> phải báo lỗi
    print("\n=== TEST: Save with empty fields ===")
    page.click("#btnSavePackage")
    page.wait_for_timeout(800)
    toast_text = page.text_content("#toast")
    print(f"  Toast after save: '{toast_text}'")

    # Đóng modal
    page.click("#btnCloseModal")
    page.wait_for_timeout(500)

    # Test mở modal SỬA 1 package
    print("\n=== TEST: Open edit modal ===")
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    print(f"  Edit buttons found: {len(edit_btns)}")
    if edit_btns:
        edit_btns[0].click()
        page.wait_for_timeout(1000)
        # Check identifier
        id_val = page.input_value("#f_identifier")
        print(f"  Editing identifier: '{id_val}'")
        # Check description
        desc_val = page.input_value("#f_description")
        print(f"  Description length: {len(desc_val)}")
        page.click("#btnCloseModal")
        page.wait_for_timeout(500)

    print("\n=== ERRORS ===")
    for e in errors[:10]:
        print(f"  {e}")

    browser.close()
print("DONE")
