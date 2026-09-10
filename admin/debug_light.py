# -*- coding: utf-8 -*-
"""Debug light mode front repo"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(BASE + "?_=fresh1")
    page.wait_for_timeout(1500)
    page.evaluate("localStorage.clear()")
    page.goto(BASE + "?_=fresh2")
    page.wait_for_timeout(2500)

    # Open settings, toggle light mode
    page.click("#settingsBtn")
    page.wait_for_timeout(400)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)

    # Get all relevant CSS vars
    info = page.evaluate("""
        (() => {
            const root = getComputedStyle(document.documentElement);
            const body = getComputedStyle(document.body);
            const main = getComputedStyle(document.querySelector('main') || document.body);
            return {
                bgColor: root.getPropertyValue('--bg-color').trim(),
                panel: root.getPropertyValue('--panel').trim(),
                panelAlt: root.getPropertyValue('--panel-alt').trim(),
                text: root.getPropertyValue('--text').trim(),
                textBright: root.getPropertyValue('--text-bright').trim(),
                bodyBg: body.backgroundColor,
                bodyColor: body.color,
                mainBg: main.backgroundColor,
                mainColor: main.color,
            };
        })()
    """)
    for k, v in info.items():
        print(f"{k}: {v}")

    # Check specific boxes
    checks = page.evaluate("""
        (() => {
            const ids = ['masthead', 'stars', 'music-player', 'moon-widget', 'info-box', 'packages-box', 'blog-section', 'footer-box'];
            const result = {};
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) {
                    const cs = getComputedStyle(el);
                    result[id] = {
                        bg: cs.backgroundColor,
                        color: cs.color,
                        borderColor: cs.borderLeftColor
                    };
                }
            }
            // Also pkg items
            const pkg = document.querySelector('.pkg-item');
            if (pkg) {
                const cs = getComputedStyle(pkg);
                result['pkg-item'] = { bg: cs.backgroundColor, color: cs.color };
            }
            return result;
        })()
    """)
    print("\n=== Boxes ===")
    for k, v in checks.items():
        print(f"{k}: {v}")

    page.click("#closeSettings")
    page.wait_for_timeout(300)
    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix6_light_repo.png", full_page=True)
    print("\nScreenshot saved: fix6_light_repo.png")

    # Also dashboard light mode
    page.goto(f"{BASE}/dashboard")
    page.wait_for_timeout(2000)
    page.click("#settingsBtn")
    page.wait_for_timeout(400)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)
    page.click("#closeSettings")
    page.wait_for_timeout(500)
    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix6_light_dash.png", full_page=True)
    print("Screenshot saved: fix6_light_dash.png")

    browser.close()
