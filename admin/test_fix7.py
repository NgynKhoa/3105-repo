# -*- coding: utf-8 -*-
"""Test fix-7: input bg in light mode - selectRepo, accent color, etc."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto(BASE + "?_=input1")
    page.wait_for_timeout(2000)
    page.evaluate("localStorage.clear()")

    # Test 1: Open add-repo modal, check input bg in dark mode
    print("Test 1: Dark mode - input bg is dark (rgba(0,0,0,0.3))...")
    page.goto(BASE + "?_=dark1")
    page.wait_for_timeout(2500)
    # Open modal to add repo
    page.evaluate("window.openRepoForm ? openRepoForm() : null")
    page.wait_for_timeout(500)
    # Try finding add button
    add_btns = page.evaluate("""
        Array.from(document.querySelectorAll('button')).filter(b => /thêm repo|add repo|\\+ thêm/i.test(b.textContent)).map(b => b.textContent.trim())
    """)
    print(f"  Add repo buttons found: {add_btns}")
    # Check input bg for siteTitle (on dashboard)
    page.goto(BASE + "/dashboard?_=dark2")
    page.wait_for_timeout(2500)
    site_title_bg_dark = page.evaluate("""
        getComputedStyle(document.getElementById('siteTitle')).backgroundColor
    """)
    print(f"  Dashboard siteTitle bg (dark): {site_title_bg_dark}")
    assert "0, 0, 0" in site_title_bg_dark, f"Dark input bg expected dark! got: {site_title_bg_dark}"

    # Test 2: Light mode
    print("\nTest 2: Light mode - input bg is light...")
    page.click("#settingsBtn")
    page.wait_for_timeout(400)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)
    site_title_bg_light = page.evaluate("""
        getComputedStyle(document.getElementById('siteTitle')).backgroundColor
    """)
    print(f"  Dashboard siteTitle bg (light): {site_title_bg_light}")
    # Light: rgba(255, 255, 255, 0.6)
    assert "255, 255, 255" in site_title_bg_light, f"Light input bg expected light! got: {site_title_bg_light}"
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    # Test 3: Front repo modal inputs in light mode
    print("\nTest 3: Front repo modal input bg in light mode...")
    page.goto(BASE + "?_=light1")
    page.wait_for_timeout(2500)
    # Open add repo modal
    page.evaluate("document.getElementById('toggleDarkMode') && document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)
    # Find open repo button
    btn_text = page.evaluate("""
        Array.from(document.querySelectorAll('button, a, [role="button"]')).map(b => b.textContent.trim()).filter(t => t && t.length < 50)
    """)
    print(f"  Buttons available: {btn_text[:15]}")

    # Try to open modal
    open_modal = page.evaluate("""
        (() => {
            // Find buttons containing "thêm" or "+"
            const btns = Array.from(document.querySelectorAll('button'));
            for (const b of btns) {
                if (b.textContent.includes('Thêm') || b.textContent.includes('+')) {
                    return b.outerHTML.substring(0, 200);
                }
            }
            return 'no button';
        })()
    """)
    print(f"  Open modal button: {open_modal[:100]}")

    browser.close()
    print("\n=== TESTS DONE ===")
