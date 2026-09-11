# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== TEST FINAL: Cross-page sync ===')
    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)

    # Set pink + lavender shadow + light mode in front
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(200)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="lavender"]')
    page.wait_for_timeout(200)
    page.click('#tabTheme')
    page.wait_for_timeout(200)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    # Go to dashboard
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)
    active_theme = page.evaluate('document.querySelector(".theme-btn.active")?.dataset.theme')
    active_shadow = page.evaluate('document.querySelector(".shadow-btn.active")?.dataset.shadow')
    toggle_off = page.evaluate('document.getElementById("toggleDarkMode").checked') == False
    print(f'  Dashboard: theme={active_theme}, shadow={active_shadow}, light={toggle_off}')

    # Click cyan theme in dashboard
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="cyan"]')
    page.wait_for_timeout(300)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    saved = page.evaluate('''
        (() => ({
            theme: localStorage.getItem('theme'),
            shadow: localStorage.getItem('shadowTheme'),
            dark: localStorage.getItem('darkMode'),
        }))()
    ''')
    print(f'  After dashboard change: {saved}')

    # Back to front
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(3000)
    front_state = page.evaluate('''
        (() => ({
            bg: getComputedStyle(document.body).backgroundColor,
            neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
            logo_shadow: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
        }))()
    ''')
    print(f'  Front return: {front_state}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix25_final.png')

    # Verify preview logo chỉ lấy shadow color, panels lấy theme color
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3000)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    # Change to purple theme
    page.click('.theme-btn[data-theme="lavender"]')
    page.wait_for_timeout(300)
    page.close_settings = False
    # Then change shadow only
    page.click('.shadow-btn[data-shadow="red"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    # Check panel border color = purple (neon)
    # Check preview shadow = red
    verification = page.evaluate('''
        (() => ({
            neon_rgb: getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim(),
            logo_shadow_rgb: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
            preview_text_shadow: getComputedStyle(document.getElementById('dashLogoText') || document.body).textShadow.substring(0, 80),
            panel_border: getComputedStyle(document.querySelector('.form-input') || document.body).borderColor,
        }))()
    ''')
    print(f'  Final verification:')
    print(f'    Neon (panel): {verification["neon_rgb"]} (should be lavender 179,136,255)')
    print(f'    Logo shadow: {verification["logo_shadow_rgb"]} (should be red 255,68,68)')
    print(f'    Preview shadow: {verification["preview_text_shadow"]}')
    print(f'    Panel border: {verification["panel_border"]}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix25_dash_mismatch.png')

    browser.close()
    print('\n=== DONE ===')
