# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== Setup: Front orange shadow ===')
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

    print('\n=== Dashboard fresh ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3500)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  Initial (green dashboard, orange logo from front): {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix29_initial.png')

    print('\n=== Click PINK theme btn on dashboard ===')
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                neon_rgb: getComputedStyle(document.documentElement).getPropertyValue("--neon-rgb").trim(),
                inline_style: p.getAttribute("style"),
            };
        })()
    ''')
    print(f'  After click PINK theme: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix29_pink_theme.png')

    browser.close()
    print('\n=== DONE ===')
