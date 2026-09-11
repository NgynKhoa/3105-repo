# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== TEST 1: Clean state ===')
    page.goto(BASE + '?_=c1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')

    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            return {
                neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
                neon_rgb: getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim(),
                logo_text_rgb: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-rgb').trim(),
                logo_text_color: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-color').trim(),
                preview_color: getComputedStyle(p).color,
                preview_stroke: getComputedStyle(p).webkitTextStrokeColor,
                preview_shadow_first: getComputedStyle(p).textShadow.substring(0, 50),
            };
        })()
    ''')
    print(f'  Default dashboard: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix27_dash_clean.png')

    print('\n=== TEST 2: Set Front to PINK + ORANGE shadow ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(3000)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(200)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    print('\n=== TEST 3: Go to Dashboard with PINK theme ===')
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3000)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="cyan"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            return {
                dash_neon_rgb: getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim(),
                dash_neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
                logo_text_rgb: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-rgb').trim(),
                logo_text_color: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-color').trim(),
                panel_border: getComputedStyle(document.querySelector('.form-input')).borderColor,
                preview_color: getComputedStyle(p).color,
                preview_shadow: getComputedStyle(p).textShadow.substring(0, 50),
            };
        })()
    ''')
    print(f'  Dashboard cyan theme (panels cyan, logo orange):')
    for k, v in s.items(): print(f'    {k}: {v}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix27_dash_cyan_panels_orange_logo.png')

    # Manually verify: preview LOGO TEXT color should be ORANGE (from Front shadow)
    # panel border should be CYAN (from dashboard neon)
    assert '255, 136, 0' in s['logo_text_rgb'], f'FAIL: logo text rgb = {s["logo_text_rgb"]} (expected orange 255, 136, 0)'
    assert '0, 240, 255' in s['dash_neon_rgb'], f'FAIL: dashboard neon rgb = {s["dash_neon_rgb"]} (expected cyan)'
    assert '0, 240, 255' in s['panel_border'], f'FAIL: panel border should be cyan'
    print('  [PASS] Logo color = orange from Front, panels = cyan from Dashboard')

    print('\n=== TEST 4: Change Front shadow to RED, reload dashboard ===')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(3000)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(300)
    page.click('.shadow-btn[data-shadow="red"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    page.goto(f'{BASE}/dashboard?_=d3')
    page.wait_for_timeout(3000)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            return {
                dash_neon_rgb: getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim(),
                logo_text_rgb: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-rgb').trim(),
                preview_color: getComputedStyle(p).color,
            };
        })()
    ''')
    print(f'  Dashboard after Front shadow=red:')
    for k, v in s.items(): print(f'    {k}: {v}')
    assert '255, 68, 68' in s['logo_text_rgb'], f'FAIL: logo should be red, got {s["logo_text_rgb"]}'
    assert '0, 240, 255' in s['dash_neon_rgb'], f'FAIL: panel should still be cyan'
    print('  [PASS] Logo color = RED from Front, panels = CYAN from Dashboard (still cyan, no cascade)')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix27_dash_cyan_panels_red_logo.png')

    browser.close()
    print('\n=== DONE - ALL PASS ===')
