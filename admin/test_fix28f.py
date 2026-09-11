# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()

    print('=== TEST: Cross-tab sync via storage event ===')
    # Tab 1: Front
    page1 = browser.new_page(viewport={'width': 1400, 'height': 900})
    page1.goto(BASE + '?_=f1')
    page1.wait_for_timeout(2500)
    page1.evaluate('localStorage.clear()')

    # Tab 2: Dashboard
    page2 = browser.new_page(viewport={'width': 1400, 'height': 900})
    page2.goto(f'{BASE}/dashboard?_=d1')
    page2.wait_for_timeout(3500)

    s = page2.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard before front change: {s}')

    # Front set orange
    page1.goto(BASE + '?_=f2')
    page1.wait_for_timeout(2500)
    page1.click('#settingsBtn')
    page1.wait_for_timeout(300)
    page1.click('#tabShadow')
    page1.wait_for_timeout(200)
    page1.click('.shadow-btn[data-shadow="orange"]')
    page1.wait_for_timeout(500)

    # Dashboard tab should auto-receive storage event
    page2.wait_for_timeout(1500)

    s = page2.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard after front=orange (no reload): {s}')

    assert '255, 136, 0' in s['preview_color'], f'FAIL: expected orange, got {s["preview_color"]}'
    print('  [PASS] Cross-tab storage event sync works')

    # Now front = pink
    page1.click('#tabShadow')
    page1.wait_for_timeout(200)
    page1.click('.shadow-btn[data-shadow="pink"]')
    page1.wait_for_timeout(500)
    page2.wait_for_timeout(1500)

    s = page2.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard after front=pink (no reload): {s}')
    assert '255, 45, 123' in s['preview_color'], f'FAIL: expected pink, got {s["preview_color"]}'
    print('  [PASS] Cross-tab sync pink')

    page1.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28f_front_pink.png')
    page2.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28f_dash_pink.png')

    browser.close()
    print('\n=== DONE - ALL PASS ===')
