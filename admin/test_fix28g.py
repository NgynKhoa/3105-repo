# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()

    page1 = browser.new_page(viewport={'width': 1400, 'height': 900})
    page1.goto(BASE + '?_=f1')
    page1.wait_for_timeout(2500)
    page1.evaluate('localStorage.clear()')

    # Capture console errors
    page2 = browser.new_page(viewport={'width': 1400, 'height': 900})
    page2.on('console', lambda m: print(f'  [page2 console] {m.type}: {m.text}'))
    page2.on('pageerror', lambda e: print(f'  [page2 error] {e}'))
    page2.goto(f'{BASE}/dashboard?_=d1')
    page2.wait_for_timeout(3500)

    # Add a debug log to dashboard
    page2.evaluate('''
        window.addEventListener('storage', function(e) {
            console.log('STORAGE EVENT:', e.key, '=', e.newValue);
        }, true);
        console.log('Dashboard listeners installed');
    ''')

    print('=== Set orange via page1 (front) ===')
    page1.goto(BASE + '?_=f2')
    page1.wait_for_timeout(2500)
    page1.click('#settingsBtn')
    page1.wait_for_timeout(300)
    page1.click('#tabShadow')
    page1.wait_for_timeout(200)
    page1.click('.shadow-btn[data-shadow="orange"]')
    page1.wait_for_timeout(1000)

    ls = page1.evaluate('localStorage.getItem("front_shadowTheme")')
    print(f'  page1 LS front_shadowTheme: {ls}')

    page2.wait_for_timeout(2000)
    s = page2.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                front_shadowTheme: localStorage.getItem("front_shadowTheme"),
            };
        })()
    ''')
    print(f'  page2 state: {s}')

    browser.close()
