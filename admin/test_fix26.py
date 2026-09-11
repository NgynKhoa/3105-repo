# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

def get_state(page):
    return page.evaluate('''
        (() => ({
            theme: localStorage.getItem('front_theme') || localStorage.getItem('dash_theme'),
            dark: localStorage.getItem('front_darkMode') || localStorage.getItem('dash_darkMode'),
            shadow: localStorage.getItem('front_shadowTheme') || localStorage.getItem('dash_shadowTheme'),
            bg: getComputedStyle(document.body).backgroundColor,
            neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
            logo_shadow: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
            text: getComputedStyle(document.body).color,
        }))()
    ''')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== TEST 1: Clean state, default values ===')
    page.goto(BASE + '?_=c1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=c2')
    page.wait_for_timeout(2500)
    s = get_state(page)
    print(f'  Front clean: {s}')

    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)
    s = get_state(page)
    print(f'  Dashboard clean: {s}')

    print('\n=== TEST 2: Set Front to pink+light+lavorange shadow ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(3000)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(200)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(200)
    page.click('#tabTheme')
    page.wait_for_timeout(200)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    ls = page.evaluate('''
        (() => ({
            front_theme: localStorage.getItem('front_theme'),
            front_darkMode: localStorage.getItem('front_darkMode'),
            front_shadowTheme: localStorage.getItem('front_shadowTheme'),
            dash_theme: localStorage.getItem('dash_theme'),
            dash_darkMode: localStorage.getItem('dash_darkMode'),
            dash_shadowTheme: localStorage.getItem('dash_shadowTheme'),
        }))()
    ''')
    print(f'  LS after front settings: {ls}')
    s = get_state(page)
    print(f'  Front visual: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix26_front_pink.png')

    print('\n=== TEST 3: Dashboard should be UNCHANGED (green+dark default) ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)
    s = get_state(page)
    print(f'  Dashboard visual (expect green+dark+lavorange shadow): {s}')
    active_theme = page.evaluate('document.querySelector(".theme-btn.active")?.dataset.theme')
    toggle_off = page.evaluate('document.getElementById("toggleDarkMode").checked') == False
    print(f'  Dashboard active theme: {active_theme} | light: {toggle_off}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix26_dash_default.png')

    print('\n=== TEST 4: Set Dashboard to cyan+light (independent from front) ===')
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="cyan"]')
    page.wait_for_timeout(300)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    ls = page.evaluate('''
        (() => ({
            front_theme: localStorage.getItem('front_theme'),
            front_darkMode: localStorage.getItem('front_darkMode'),
            dash_theme: localStorage.getItem('dash_theme'),
            dash_darkMode: localStorage.getItem('dash_darkMode'),
        }))()
    ''')
    print(f'  LS after dash settings: {ls}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix26_dash_cyan.png')

    print('\n=== TEST 5: Reload Front - should stay pink+light, NOT change to cyan ===')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(3000)
    s = get_state(page)
    print(f'  Front after reload: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix26_front_reload.png')

    print('\n=== TEST 6: Reload Dashboard - should stay cyan+light ===')
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3000)
    s = get_state(page)
    print(f'  Dashboard after reload: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix26_dash_reload.png')

    print('\n=== TEST 7: Preview logo gets Front shadow color, NOT dashboard shadow ===')
    preview = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            return {
                logo_shadow_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
                preview_text_shadow: getComputedStyle(p).textShadow.substring(0, 60),
                panel_border: getComputedStyle(document.querySelector('.form-input') || document.body).borderColor,
            };
        })()
    ''')
    print(f'  Preview: {preview}')

    browser.close()
    print('\n=== DONE ===')
