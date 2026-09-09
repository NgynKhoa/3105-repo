#!/usr/bin/env python3
"""Test: các edge case UX trên web."""
import sys, json, urllib.request
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

    # TEST 1: Modal click overlay -> đóng
    print("=== TEST 1: Modal close on overlay click ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    print(f"  Modal visible: {page.is_visible('#modal')}")
    # Click ra ngoài modal body
    page.mouse.click(10, 10)  # click góc trên-trái, ngoài modal
    page.wait_for_timeout(500)
    print(f"  Modal visible after click outside: {page.is_visible('#modal')}")

    # TEST 2: Modal click ESC
    print("\n=== TEST 2: Modal close on ESC ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    print(f"  Modal visible after ESC: {page.is_visible('#modal')}")

    # TEST 3: Toast tự ẩn
    print("\n=== TEST 3: Toast auto-hide ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    page.click("#btnSavePackage")  # save empty -> toast error
    page.wait_for_timeout(500)
    toast_text = page.text_content("#toast")
    print(f"  Toast: '{toast_text}'")
    print(f"  Toast visible: {page.is_visible('#toast')}")
    page.wait_for_timeout(4000)
    print(f"  Toast visible after 4s: {page.is_visible('#toast')}")

    # TEST 4: Nút Save có resize khi push chạy?
    print("\n=== TEST 4: Save button resize ===")
    page.click("#btnCloseModal")
    page.wait_for_timeout(500)
    box_before = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  Before click: {box_before}")
    # Click save (không có thay đổi)
    page.click("#btnSave")
    page.wait_for_timeout(500)  # trong khi đang lưu
    box_during = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim(), disabled: el.disabled})")
    print(f"  During save:  {box_during}")
    page.wait_for_timeout(3000)
    box_after = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim(), disabled: el.disabled})")
    print(f"  After save:   {box_after}")

    # TEST 5: button có rộng ra do text "Đang lưu..." so với "[>]"?
    print("\n=== TEST 5: Buttons trong modal không bị wrap ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    btn_save_pkg = page.eval_on_selector("#btnSavePackage", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    btn_cancel = page.eval_on_selector("#btnCancel", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  btnSavePackage: {btn_save_pkg}")
    print(f"  btnCancel: {btn_cancel}")

    # TEST 6: Khi bấm Save trong modal -> button có resize?
    page.fill("#f_name", "Test")
    page.wait_for_timeout(200)
    box_pkg_save = page.eval_on_selector("#btnSavePackage", "el => ({w: el.offsetWidth, h: el.offsetHeight})")
    print(f"  btnSavePackage before save: {box_pkg_save}")
    page.click("#btnSavePackage")
    page.wait_for_timeout(300)
    box_pkg_save_during = page.eval_on_selector("#btnSavePackage", "el => ({w: el.offsetWidth, h: el.offsetHeight, disabled: el.disabled, text: el.textContent.trim()})")
    print(f"  btnSavePackage during save: {box_pkg_save_during}")
    page.wait_for_timeout(1000)

    # TEST 7: Image preview load trong form
    print("\n=== TEST 7: Icon/Banner preview ===")
    page.click("#btnAdd")
    page.wait_for_timeout(800)
    # Click vào ảnh thứ 2 trong icon picker
    page.click("#btnIconToggle")
    page.wait_for_timeout(500)
    icon_items = page.eval_on_selector_all("#iconPickerGrid img", "els => els.length")
    print(f"  Icon images: {icon_items}")
    # Click 1 ảnh
    if icon_items >= 2:
        page.click("#iconPickerGrid > * >> nth=1")
        page.wait_for_timeout(500)
        f_icon_val = page.input_value("#f_icon")
        print(f"  Selected icon: '{f_icon_val}'")
        # Check label "Đã chọn"
        cur_text = page.text_content("#iconPickerCurrent")
        print(f"  Current label: '{cur_text}'")

    # TEST 8: Icon search filter
    print("\n=== TEST 8: Icon search ===")
    page.fill("#f_icon_search", "PUBG")
    page.wait_for_timeout(500)
    filtered = page.eval_on_selector_all("#iconPickerGrid > *", "els => els.length")
    print(f"  Filtered by 'PUBG': {filtered}")

    # TEST 9: Folder selector switch
    print("\n=== TEST 9: Switch icon folder ===")
    page.fill("#f_icon_search", "")
    page.wait_for_timeout(300)
    # Switch to icon folder
    page.select_option("#f_icon_folder", "icon")
    page.wait_for_timeout(800)
    items = page.eval_on_selector_all("#iconPickerGrid > *", "els => els.length")
    print(f"  Items in 'icon/' folder: {items}")

    # TEST 10: Click nút X (delete) trong icon folder
    print("\n=== TEST 10: Delete folder button ===")
    btn_delete_folder_visible = page.is_visible("#btnDeleteIconFolder")
    print(f"  Delete folder button visible: {btn_delete_folder_visible}")

    page.click("#btnCloseModal")
    page.wait_for_timeout(500)

    print("\n=== ERRORS ===")
    for e in errors[:15]:
        print(f"  {e}")
    browser.close()
print("DONE")
