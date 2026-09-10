# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    console_logs = []
    page.on('console', lambda msg: console_logs.append(f'[{msg.type}] {msg.text}'))

    print('=== TEST 1: Shadow changes immediately without reload ===')
    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2500)
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

    logo_shadow = page.evaluate('''
        (() => {
            const lt = document.querySelector('#logo-text .lt');
            if (!lt) return null;
            const cs = getComputedStyle(lt);
            return {
                css_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
                inline_shadow: lt.style.textShadow.substring(0, 50),
                stroke: lt.style.webkitTextStroke,
            };
        })()
    ''')
    print(f'  After pink: {logo_shadow}')

    # Switch to cyan WITHOUT reload
    page.click('.shadow-btn[data-shadow="cyan"]')
    page.wait_for_timeout(300)
    logo_shadow2 = page.evaluate('''
        (() => {
            const lt = document.querySelector('#logo-text .lt');
            if (!lt) return null;
            const cs = getComputedStyle(lt);
            return {
                css_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
                inline_shadow: lt.style.textShadow.substring(0, 50),
                stroke: lt.style.webkitTextStroke,
            };
        })()
    ''')
    print(f'  After cyan (no reload): {logo_shadow2}')

    page.click('#closeSettings')
    page.wait_for_timeout(300)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix20_front_cyan.png')

    # Switch back to pink WITHOUT reload
    page.click('#settingsBtn')
    page.wait_for_timeout(200)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="pink"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(300)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix20_front_pink.png')

    # ===== TEST 2: BG not reset =====
    print('\n=== TEST 2: BG not reset ===')
    # Front default: dark
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2500)
    bg1 = page.evaluate('getComputedStyle(document.body).backgroundColor')
    print(f'  Initial front BG: {bg1}')

    # Navigate to dashboard
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(2500)

    # Toggle dark OFF in dashboard
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    bg_dash = page.evaluate('getComputedStyle(document.body).backgroundColor')
    print(f'  Dashboard BG after toggle OFF: {bg_dash}')

    # Back to front
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)
    bg_front = page.evaluate('getComputedStyle(document.body).backgroundColor')
    print(f'  Front BG after back: {bg_front}')

    # ===== TEST 3: Preview takes real-time color from front =====
    print('\n=== TEST 3: Preview takes shadow color from front repo ===')
    page.goto(BASE + '?_=f3')
    page.wait_for_timeout(2500)
    page.evaluate('window.applyShadowTheme("lavender")')
    page.wait_for_timeout(300)

    # Now go to dashboard
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(2500)

    preview = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            if (!p) return null;
            const cs = getComputedStyle(p);
            return {
                css_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb').trim(),
                text_shadow: cs.textShadow.substring(0, 100),
                stroke: cs.webkitTextStroke,
            };
        })()
    ''')
    print(f'  Preview after lavender: {preview}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix20_dash_preview.png')

    browser.close()
    print('\n=== DONE ===')
    for log in console_logs[-15:]:
        print(f'  CONSOLE: {log}')
