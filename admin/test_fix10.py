# -*- coding: utf-8 -*-
"""Test fix-10: modal add/edit package light mode"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(BASE + "?_=m1")
    page.wait_for_timeout(2000)
    page.evaluate("localStorage.clear()")
    page.goto(BASE + "?_=m2")
    page.wait_for_timeout(2500)

    # Open add package modal
    btns = page.query_selector_all("button")
    for b in btns:
        txt = b.text_content().strip()
        if "+ Thêm" in txt or "+Thêm" in txt:
            b.click()
            break
    page.wait_for_timeout(800)

    # Check dark mode modal
    dark = page.evaluate("""
        (() => {
            const modal = document.getElementById('modal');
            const content = document.querySelector('.modal-content');
            const header = document.querySelector('.modal-header');
            const body = document.getElementById('modalBody');
            const r = {};
            if (modal) r['_is_open'] = modal.classList.contains('open');
            if (content) r['_content_bg'] = getComputedStyle(content).backgroundColor;
            if (header) r['_header_border'] = getComputedStyle(header).borderBottomColor;
            // Check first input
            const inp = body ? body.querySelector('input, select, textarea') : null;
            if (inp) {
                r['_input_bg'] = getComputedStyle(inp).backgroundColor;
                r['_input_color'] = getComputedStyle(inp).color;
            }
            return r;
        })()
    """)
    print("=== Dark mode modal ===")
    for k, v in dark.items(): print(f"  {k}: {v}")

    # Toggle light
    page.click("#settingsBtn")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(500)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    light = page.evaluate("""
        (() => {
            const content = document.querySelector('.modal-content');
            const header = document.querySelector('.modal-header');
            const body = document.getElementById('modalBody');
            const r = {};
            if (content) r['_content_bg'] = getComputedStyle(content).backgroundColor;
            if (header) r['_header_border'] = getComputedStyle(header).borderBottomColor;
            const inp = body ? body.querySelector('input, select, textarea') : null;
            if (inp) {
                r['_input_bg'] = getComputedStyle(inp).backgroundColor;
                r['_input_color'] = getComputedStyle(inp).color;
            }
            return r;
        })()
    """)
    print("\n=== Light mode modal ===")
    for k, v in light.items(): print(f"  {k}: {v}")

    # Toggle back dark
    page.click("#settingsBtn")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(500)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    back_dark = page.evaluate("""
        (() => {
            const content = document.querySelector('.modal-content');
            const r = {};
            if (content) r['_content_bg'] = getComputedStyle(content).backgroundColor;
            const body = document.getElementById('modalBody');
            const inp = body ? body.querySelector('input') : null;
            if (inp) r['_input_bg'] = getComputedStyle(inp).backgroundColor;
            return r;
        })()
    """)
    print("\n=== Back to Dark modal ===")
    for k, v in back_dark.items(): print(f"  {k}: {v}")

    # Screenshot
    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix10_modal_dark.png")
    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix10_modal_light.png")

    browser.close()
    print("\n=== DONE ===")
