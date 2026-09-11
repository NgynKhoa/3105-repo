# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== Clean state, never visited front ===')
    page.goto(BASE + '?_=s1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')

    # Go DIRECTLY to dashboard (simulating user opening dashboard without front)
    print('\n=== Dashboard directly, no front visited ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3500)

    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
                logo_text_rgb_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-rgb").trim(),
                logo_shadow_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-color").trim(),
                front_shadowTheme: localStorage.getItem("front_shadowTheme"),
                repo_shadowTheme: localStorage.getItem("repo_shadowTheme"),
            };
        })()
    ''')
    print(f'  State: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28e_dash_direct.png')

    # Now go to front, set orange shadow, then back to dashboard
    print('\n=== Front set orange shadow, then back to dashboard ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(3500)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard after front=orange: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28e_dash_orange.png')

    # Now set Front shadow=pink
    print('\n=== Front set pink shadow, then back ===')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="pink"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    page.goto(f'{BASE}/dashboard?_=d3')
    page.wait_for_timeout(3500)
    s = page.evaluate('''
        (() => {
            const p = document.getElementById("dashLogoText");
            return {
                preview_color: getComputedStyle(p).color,
                logo_text_color_var: getComputedStyle(document.documentElement).getPropertyValue("--logo-text-color").trim(),
            };
        })()
    ''')
    print(f'  Dashboard after front=pink: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix28e_dash_pink.png')

    browser.close()
    print('\n=== DONE ===')
