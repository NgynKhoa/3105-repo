# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== TEST: Preview takes shadow color from front repo ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)

    # Change shadow on front
    page.evaluate('window.applyShadowTheme("lavender")')
    page.wait_for_timeout(300)
    front_var = page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim()')
    print(f'  Front --logo-shadow-rgb after lavender: {front_var}')

    # Check localStorage
    ls = page.evaluate('localStorage.getItem("shadowTheme")')
    print(f'  localStorage shadowTheme: {ls}')

    # Navigate to dashboard
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)

    # Check CSS var on dashboard
    dash_var = page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim()')
    print(f'  Dashboard --logo-shadow-rgb: {dash_var}')

    # Check preview element styles
    preview = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            if (!p) return null;
            const cs = getComputedStyle(p);
            return {
                css_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
                text_shadow: cs.textShadow,
                stroke: cs.webkitTextStroke,
                font_family: cs.fontFamily,
                color: cs.color,
            };
        })()
    ''')
    print(f'  Preview: {preview}')

    # Test change shadow theme on dashboard via applyShadowTheme if exists
    has_shadow = page.evaluate('typeof window.applyShadowTheme === "function"')
    print(f'  Dashboard has applyShadowTheme: {has_shadow}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix21_dash_lavender.png')

    browser.close()
    print('=== DONE ===')
