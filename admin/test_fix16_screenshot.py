# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    # Dashboard settings - transparency slider + rain sliders
    page.goto(f'{BASE}/dashboard?_=t1')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix16_dash_settings.png')
    print('Dashboard settings screenshot saved')

    # Dashboard Style panel
    page.evaluate('''
        Array.from(document.querySelectorAll(".dash-tab")).forEach(t => {
            if (t.textContent.includes("Style")) t.click();
        });
    ''')
    page.wait_for_timeout(800)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix16_dash_style.png')
    print('Dashboard Style panel screenshot saved')

    # Front repo settings
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix16_front_settings.png')
    print('Front settings screenshot saved')

    browser.close()
    print('=== DONE ===')
