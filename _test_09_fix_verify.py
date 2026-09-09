#!/usr/bin/env python3
"""Verify các fix và test các trường hợp còn lại."""
import sys, json, urllib.request, time
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

    # FIX 1: Modal close on overlay click
    print("=== FIX 1: Modal close on overlay ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    print(f"  Before: visible={page.is_visible('#modal')}")
    # Click tọa độ trong overlay nhưng KHÔNG trong modal-content
    page.evaluate("document.querySelector('#modal').dispatchEvent(new MouseEvent('click', {bubbles:true, clientX: 50, clientY: 50, target: document.querySelector('#modal')}))")
    page.wait_for_timeout(500)
    print(f"  After dispatch click on overlay: visible={page.is_visible('#modal')}")

    # Try real click on overlay (header area, outside modal-content)
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    # Click chính giữa header (y=20) — chắc chắn ngoài modal-content
    box = page.eval_on_selector("#modal", "el => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; }")
    print(f"  Modal rect: {box}")
    page.mouse.click(int(box['x'] + 50), int(box['y'] + 20))  # góc trên-trái của overlay
    page.wait_for_timeout(500)
    print(f"  After mouse click overlay top-left: visible={page.is_visible('#modal')}")

    # FIX 2: Nút Save resize issue
    print("\n=== FIX 2: Nút Save button size ===")
    box_before = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  Before: {box_before}")
    # Click save
    page.click("#btnSave")
    page.wait_for_timeout(200)
    box_during = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim(), disabled: el.disabled})")
    print(f"  During: {box_during}")
    page.wait_for_timeout(3000)
    box_after = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  After:  {box_after}")

    # TEST: button width có khác nhau không?
    if box_before['w'] != box_after['w']:
        print(f"  ⚠ Width changed: {box_before['w']} -> {box_after['w']}")
    else:
        print(f"  ✓ Width stable")

    # TEST: ESC close modal
    print("\n=== TEST: ESC closes modal ===")
    page.click("#btnAdd")
    page.wait_for_timeout(500)
    print(f"  Before ESC: visible={page.is_visible('#modal')}")
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    print(f"  After ESC: visible={page.is_visible('#modal')}")

    # TEST: nút Lưu package có resize?
    print("\n=== TEST: btnSavePackage size ===")
    page.click("#btnAdd")
    page.wait_for_timeout(800)
    box = page.eval_on_selector("#btnSavePackage", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  Initial: {box}")
    page.fill("#f_name", "Test")
    page.click("#btnSavePackage")
    page.wait_for_timeout(200)
    box = page.eval_on_selector("#btnSavePackage", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim(), disabled: el.disabled})")
    print(f"  During: {box}")

    # TEST: nút btnSavePackage đang lưu -> text thay đổi, có resize?
    page.wait_for_timeout(1500)

    # Check modal đã đóng chưa
    print(f"  Modal visible after save: {page.is_visible('#modal')}")

    # TEST: Duplicate identifier khi sửa
    print("\n=== TEST: Duplicate identifier via UI ===")
    # Mở edit package owen-002 -> đổi identifier thành owen-001 (đã tồn tại)
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    print(f"  Edit buttons: {len(edit_btns)}")
    if edit_btns:
        edit_btns[0].click()  # Edit package đầu tiên (trang 1)
        page.wait_for_timeout(800)
        # Lấy identifier hiện tại
        cur_id = page.input_value("#f_identifier")
        print(f"  Current ID: '{cur_id}'")
        page.fill("#f_identifier", "owen-001")  # Trùng với package khác
        page.click("#btnSavePackage")
        page.wait_for_timeout(1500)
        toast = page.text_content("#toast")
        print(f"  Toast: '{toast}'")
        # Modal có còn mở không?
        print(f"  Modal still visible: {page.is_visible('#modal')}")
        # Đóng
        page.click("#btnCloseModal")
        page.wait_for_timeout(500)

    print("\n=== ERRORS ===")
    for e in errors[:15]:
        print(f"  {e}")
    browser.close()
print("DONE")
