# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== SETUP: Clear + set front shadow=orange ===')
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
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(500)
    print(f'  front_shadowTheme: {page.evaluate("localStorage.getItem(\"front_shadowTheme\")")}')

    print('\n=== Front: logo color = orange (from shadow) ===')
    s = page.evaluate('''
        (() => {
            const logoEl = document.querySelector("#logo-text .lt") || document.getElementById("logo-text");
            return {
                logo_color: getComputedStyle(logoEl).color,
                neon_color: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  Logo color: {s["logo_color"]} | Neon: {s["neon_color"]}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix29_front_orange.png')
    assert '255, 136, 0' in s['logo_color'], f'FAIL: {s["logo_color"]}'
    print('  [PASS]')

    print('\n=== Open settings, switch to Theme tab, click PINK ===')
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabTheme')  # Switch to theme tab first (panelShadow was showing from before)
    page.wait_for_timeout(200)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)

    s = page.evaluate('''
        (() => {
            const logoEl = document.querySelector("#logo-text .lt") || document.getElementById("logo-text");
            return {
                logo_color: getComputedStyle(logoEl).color,
                neon_color: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  Logo color: {s["logo_color"]} (should STILL be orange)')
    print(f'  Neon: {s["neon_color"]} (should be pink)')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix29_front_pink_theme.png')
    assert '255, 136, 0' in s['logo_color'], f'FAIL: logo should be orange, got {s["logo_color"]}'
    assert 'ff2d7b' in s['neon_color'], f'FAIL: neon should be pink'
    print('  [PASS] Logo orange, neon pink (independent)')

    print('\n=== Change front shadow to cyan ===')
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="cyan"]')
    page.wait_for_timeout(500)

    s = page.evaluate('''
        (() => {
            const logoEl = document.querySelector("#logo-text .lt") || document.getElementById("logo-text");
            return {
                logo_color: getComputedStyle(logoEl).color,
                neon_color: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  Logo color: {s["logo_color"]} (should be cyan)')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix29_front_cyan.png')
    assert '0, 240, 255' in s['logo_color'], f'FAIL: logo should be cyan, got {s["logo_color"]}'
    print('  [PASS] Logo = cyan (follows shadow)')

    browser.close()
    print('\n=== ALL PASS ===')
