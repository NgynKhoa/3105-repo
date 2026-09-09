#!/usr/bin/env python3
"""Test nút Save với API chậm để quan sát loading state."""
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

    # Intercept API để delay 2s
    def slow_api(route, request):
        import time
        if "/save" in request.url or "/push" in request.url:
            time.sleep(2)
        route.continue_()
    page.route("**/api/repo/demo/save", slow_api)
    page.route("**/api/repo/demo/push", slow_api)

    box_before = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"Before: {box_before}")

    page.click("#btnSave")
    page.wait_for_timeout(500)  # trong khi đang xử lý
    box_during = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim(), disabled: el.disabled, dataLoading: el.dataset.loading, hasBefore: getComputedStyle(el, '::before').content})")
    print(f"During: {box_during}")

    page.wait_for_timeout(5000)
    box_after = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, text: el.textContent.trim()})")
    print(f"After:  {box_after}")

    print("\n=== ERRORS ===")
    for e in errors[:5]:
        print(f"  {e}")
    browser.close()
print("DONE")
