#!/usr/bin/env python3
"""Verify các fix sau khi áp dụng."""
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

    # FIX 2 verified: Nút Save không resize
    print("=== FIX 2: Nút Save button KHÔNG resize ===")
    box_before = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  Before: {box_before}")
    page.click("#btnSave")
    page.wait_for_timeout(200)
    box_during = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim(), disabled: el.disabled, hasBefore: getComputedStyle(el, '::before').content})")
    print(f"  During: {box_during}")
    page.wait_for_timeout(3000)
    box_after = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"  After:  {box_after}")
    if abs(box_before['w'] - box_after['w']) > 2:
        print(f"  ⚠ STILL RESIZING: {box_before['w']} -> {box_after['w']}")
    else:
        print(f"  ✓ Width stable: {box_before['w']}px")

    # Test edit duplicate identifier
    print("\n=== TEST: Duplicate identifier via UI ===")
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    if edit_btns:
        edit_btns[0].click()
        page.wait_for_timeout(800)
        cur_id = page.input_value("#f_identifier")
        print(f"  Current ID: '{cur_id}'")
        page.fill("#f_identifier", "owen-001")
        page.click("#btnSavePackage")
        page.wait_for_timeout(1500)
        toast = page.text_content("#toast")
        print(f"  Toast: '{toast}'")
        print(f"  Modal visible: {page.is_visible('#modal')}")
        page.click("#btnCloseModal")
        page.wait_for_timeout(500)

    print("\n=== ERRORS ===")
    for e in errors[:10]:
        print(f"  {e}")
    browser.close()
print("DONE")
