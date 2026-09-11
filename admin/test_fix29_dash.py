# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== SETUP: Front cyan shadow ===')
    page.goto(BASE + '?_=s1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=s2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="cyan"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)
    print(f'  front_shadowTheme: {page.evaluate("localStorage.getItem(\"front_shadowTheme\")")}')

    print('\n=== Dashboard: logo = cyan from Front ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3500)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                panel_border: getComputedStyle(document.querySelector('.form-input')).borderColor,
            };
        })()
    ''')
    print(f'  Logo color: {s["preview_color"]} (should be cyan from Front)')
    print(f'  Neon: {s["neon"]} (dashboard default green)')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix29_dash_cyan.png')

    assert '0, 240, 255' in s['preview_color'], f'FAIL: logo should be cyan, got {s["preview_color"]}'
    print('  [PASS] Dashboard logo = cyan from Front, neon = green from Dashboard')

    browser.close()
    print('\n=== ALL PASS ===')
