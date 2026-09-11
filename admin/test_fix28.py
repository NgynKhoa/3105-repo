# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== SETUP: Set front orange shadow ===')
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

    ls = page.evaluate('''
        (() => ({
            front_shadowTheme: localStorage.getItem('front_shadowTheme'),
            logo_text_rgb: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-rgb').trim(),
            logo_text_color: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-color').trim(),
        }))()
    ''')
    print(f'  Front LS: {ls}')

    print('\n=== Open Dashboard fresh ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3500)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            const logoShadowRgb = getComputedStyle(document.documentElement).getPropertyValue('--logo-text-rgb').trim();
            const logoTextColor = getComputedStyle(document.documentElement).getPropertyValue('--logo-text-color').trim();
            return {
                logo_text_rgb: logoShadowRgb,
                logo_text_color: logoTextColor,
                preview_color_css: getComputedStyle(p).color,
                preview_shadow_rgb: getComputedStyle(p).textShadow,
                neon_rgb: getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim(),
                logo_text_loaded: p ? p.style.color : 'null',
            };
        })()
    ''')
    print(f'  Dashboard vars: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28_dash_orange.png')

    print('\n=== Verify: Reload Dashboard ===')
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3000)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            return {
                logo_text_rgb: getComputedStyle(document.documentElement).getPropertyValue('--logo-text-rgb').trim(),
                preview_color: getComputedStyle(p).color,
            };
        })()
    ''')
    print(f'  After reload: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28_dash_reload.png')

    browser.close()
    print('\n=== DONE ===')
