# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(BASE + '?_=s1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=s2')
    page.wait_for_timeout(2500)

    print('=== Fresh: theme=green, no shadow ===')
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#logo-text .lt");
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                shadow: getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix30_fresh.png')

    print('\n=== Click PINK theme ===')
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('.theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#logo-text .lt");
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix30_pink.png')

    print('\n=== Click ORANGE shadow ===')
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(500)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#logo-text .lt");
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                shadow: getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix30_orange_shadow.png')

    browser.close()
