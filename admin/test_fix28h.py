# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()

    # ONE context, use same page to navigate
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== SETUP: Front orange shadow ===')
    page.goto(BASE + '?_=s1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=s2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    print('\n=== Open Dashboard fresh ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3500)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard logo: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28h_dash.png')

    # Click pink shadow btn on dashboard → preview should change to pink
    print('\n=== Click pink shadow btn on Dashboard ===')
    page.click('#settingsBtn')
    page.wait_for_timeout(500)
    page.click('.shadow-btn[data-shadow="pink"]')
    page.wait_for_timeout(500)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                front_shadowTheme: localStorage.getItem("front_shadowTheme"),
            };
        })()
    ''')
    print(f'  Dashboard preview: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28h_dash_pink_clicked.png')

    # Close settings, click Front shadow → front saves
    print('\n=== Close settings, go to Front, change shadow to cyan ===')
    page.click('#closeSettings')
    page.wait_for_timeout(300)
    page.goto(BASE + '?_=f3')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="cyan"]')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    print('\n=== Back to Dashboard, logo should be CYAN ===')
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3500)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard logo: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28h_dash_cyan.png')

    assert '0, 240, 255' in s['preview_color'], f'FAIL: expected cyan, got {s["preview_color"]}'
    print('  [PASS] Front shadow=cyan → Dashboard logo cyan')

    browser.close()
    print('\n=== ALL PASS ===')
