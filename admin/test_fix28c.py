# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
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
    ls = page.evaluate('({front_shadowTheme: localStorage.getItem("front_shadowTheme")})')
    print(f'  Front shadow: {ls["front_shadowTheme"]}')

    print('\n=== Open Dashboard fresh ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3500)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                logo_text_rgb_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-rgb").trim(),
            };
        })()
    ''')
    print(f'  Dashboard logo: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28c_dash.png')

    # Click pink shadow btn directly in dashboard (no tab needed)
    page.click('.shadow-btn[data-shadow="pink"]')
    page.wait_for_timeout(500)

    s2 = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                front_shadowTheme: localStorage.getItem("front_shadowTheme"),
            };
        })()
    ''')
    print(f'  After clicking pink shadow btn: {s2}')

    print('\n=== Reload Dashboard ===')
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3500)
    s3 = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                front_shadowTheme: localStorage.getItem("front_shadowTheme"),
            };
        })()
    ''')
    print(f'  After reload: {s3}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28c_reload.png')

    browser.close()
    print('\n=== DONE ===')
