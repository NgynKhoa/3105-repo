# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1400, 'height': 900}, bypass_csp=True)
    page = context.new_page()
    page.route('**/*', lambda route: route.continue_(headers={**route.request.headers, 'Cache-Control': 'no-cache'}))
    page.goto(BASE + '?_=' + str(__import__('time').time()))
    page.wait_for_timeout(3000)

    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=' + str(__import__('time').time()))
    page.wait_for_timeout(3000)

    # No settings, fresh state
    info = page.evaluate('''
        (() => {
            const lt = document.querySelector("#logo-text .lt");
            const parent = document.getElementById("logo-text");
            return {
                lt_color: getComputedStyle(lt).color,
                lt_inline_color: lt.style.color || '(empty)',
                parent_color: getComputedStyle(parent).color,
                neon_var: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                logo_shadow_rgb: getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim(),
                saved_theme: localStorage.getItem("front_theme") || localStorage.getItem("repo_theme"),
                saved_shadow: localStorage.getItem("front_shadowTheme") || localStorage.getItem("shadowTheme") || localStorage.getItem("repo_shadowTheme"),
            };
        })()
    ''')
    print('=== FRESH STATE ===')
    for k, v in info.items():
        print(f'  {k}: {v}')

    browser.close()
