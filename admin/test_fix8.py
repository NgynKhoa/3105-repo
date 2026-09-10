# -*- coding: utf-8 -*-
"""Test fix-8: dark mode after light mode - inputs back to dark"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(BASE + "?_=t1")
    page.wait_for_timeout(2000)
    page.evaluate("localStorage.clear()")

    # Dashboard fresh
    page.goto(f"{BASE}/dashboard?_=d1")
    page.wait_for_timeout(2500)

    def get_input_bgs():
        return page.evaluate("""
            (() => {
                const ids = ['siteTitle', 'logoText', 'repoUrl', 'siteDesc', 'postIcon', 'postTitle', 'postExcerpt', 'postContent'];
                const result = {};
                for (const id of ids) {
                    const el = document.getElementById(id);
                    if (el) result[id] = getComputedStyle(el).backgroundColor;
                }
                return result;
            })()
        """)

    def toggle_dark():
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

    print("=== Initial (dark) ===")
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  {k}: {v}")
    assert all("0, 0, 0" in v for v in bgs.values()), f"Initial should be dark! got: {bgs}"

    print("\n=== After toggle to LIGHT ===")
    toggle_dark()
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  {k}: {v}")
    for k, v in bgs.items():
        assert "255, 255, 255" in v, f"After light: {k} should be light! got: {v}"

    print("\n=== After toggle back to DARK ===")
    toggle_dark()
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  {k}: {v}")
    for k, v in bgs.items():
        assert "0, 0, 0" in v, f"After back to dark: {k} should be dark! got: {v}"

    print("\n=== Reload page (should stay dark) ===")
    page.goto(f"{BASE}/dashboard?_=d2")
    page.wait_for_timeout(2500)
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  {k}: {v}")
    for k, v in bgs.items():
        assert "0, 0, 0" in v, f"After reload dark: {k} should be dark! got: {v}"

    print("\n=== Reload page after LIGHT MODE set ===")
    toggle_dark()
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  After light toggle: {v}")
    page.goto(f"{BASE}/dashboard?_=d3")
    page.wait_for_timeout(2500)
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  After reload: {v}")
    for k, v in bgs.items():
        assert "255, 255, 255" in v, f"After reload light: {k} should be light! got: {v}"

    # Now back to dark
    print("\n=== After reload light, toggle back to dark ===")
    toggle_dark()
    bgs = get_input_bgs()
    for k, v in bgs.items(): print(f"  {v}")
    for k, v in bgs.items():
        assert "0, 0, 0" in v, f"After dark from light: {k} should be dark! got: {v}"

    browser.close()
    print("\n=== ALL PASS ===")
