# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== TEST: Auto-save settings across pages ===')
    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)

    # Set theme pink + shadow lavender + darkMode OFF in front
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(200)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="lavender"]')
    page.wait_for_timeout(200)
    # Toggle dark OFF
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    # Check saved state
    saved = page.evaluate('''
        (() => {
            return {
                theme: localStorage.getItem('theme'),
                shadowTheme: localStorage.getItem('shadowTheme'),
                darkMode: localStorage.getItem('darkMode'),
                neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
                logo_shadow: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
            };
        })()
    ''')
    print(f'  Saved after front settings: {saved}')

    # Navigate to dashboard
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)

    dash_state = page.evaluate('''
        (() => {
            return {
                bg: getComputedStyle(document.body).backgroundColor,
                neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
                neon_rgb: getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim(),
                logo_shadow: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
                text: getComputedStyle(document.body).color,
                preview_color: getComputedStyle(document.getElementById('dashLogoText') || document.body).color,
                preview_shadow: getComputedStyle(document.getElementById('dashLogoText') || document.body).textShadow.substring(0, 60),
            };
        })()
    ''')
    print(f'  Dashboard state: {dash_state}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix24_dash_synced.png')

    # Check toggle status
    toggle_checked = page.evaluate('document.getElementById("toggleDarkMode").checked')
    active_theme_btn = page.evaluate('document.querySelector(".theme-btn.active")?.dataset.theme')
    active_shadow_btn = page.evaluate('document.querySelector(".shadow-btn.active")?.dataset.shadow')
    print(f'  Dashboard toggle checked: {toggle_checked} | active theme: {active_theme_btn} | shadow: {active_shadow_btn}')

    # Navigate back to front
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(3000)

    front_state = page.evaluate('''
        (() => {
            return {
                bg: getComputedStyle(document.body).backgroundColor,
                neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
                logo_shadow: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
            };
        })()
    ''')
    print(f'  Front state after return: {front_state}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix24_front_synced.png')

    browser.close()
    print('=== DONE ===')
