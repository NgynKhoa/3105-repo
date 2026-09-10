# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    # ===== TEST 1: Shadow color changes immediately =====
    print('=== TEST 1: Shadow color changes immediately ===')
    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)

    # Pick pink shadow
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="pink"]')
    page.wait_for_timeout(300)

    css_var = page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim()')
    print(f'  Shadow RGB after pink: {css_var}')

    # Switch to cyan shadow immediately
    page.click('.shadow-btn[data-shadow="cyan"]')
    page.wait_for_timeout(300)
    css_var2 = page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim()')
    print(f'  Shadow RGB after cyan: {css_var2}')
    page.click('#closeSettings')

    # ===== TEST 2: Spaces preserved in logo text =====
    print('\n=== TEST 2: Spaces preserved ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(2500)

    page.fill('#logoText', 'OWEN CUSTOM REPO')
    page.wait_for_timeout(200)
    page.evaluate('saveGeneral()')
    page.wait_for_timeout(500)

    # Check saved
    saved = page.evaluate('localStorage.getItem("repo_logoText")')
    print(f'  Saved logoText: "{saved}"')

    # Reload front - applyLogoSettings runs via setTimeout on load
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2500)

    logo_html = page.evaluate('document.getElementById("logo-text").innerHTML')
    print(f'  Logo innerHTML (first 200 chars): {logo_html[:200]}')

    spans = page.evaluate('''
        (() => {
            var lts = document.querySelectorAll("#logo-text .lt");
            return Array.from(lts).map(s => s.textContent);
        })()
    ''')
    print(f'  Spans: {spans}')
    space_count = page.evaluate('''
        document.querySelectorAll("#logo-text .space-sep").length
    ''')
    print(f'  Space spans count: {space_count}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix19_spaces.png')

    # ===== TEST 3: BG not reset after navigating to admin =====
    print('\n=== TEST 3: BG not reset ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2500)
    # Set dark mode
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    # Toggle should already be on (dark) - verify bg is dark
    bg_dark = page.evaluate('getComputedStyle(document.body).backgroundColor')
    print(f'  Front BG dark: {bg_dark}')
    page.click('#closeSettings')
    page.wait_for_timeout(200)

    # Navigate to dashboard
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(2500)
    # Navigate back
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)
    bg_after = page.evaluate('getComputedStyle(document.body).backgroundColor')
    print(f'  Front BG after nav to admin: {bg_after}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix19_bg.png')

    browser.close()
    print('\n=== DONE ===')
