# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(BASE + '/dashboard?_=s1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '/dashboard?_=s2')
    page.wait_for_timeout(2500)

    print('=== Fresh ===')
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            const html = document.documentElement;
            return {
                lt_color: getComputedStyle(lt).color,
                lt_inline_color: lt.style.color,
                neon: getComputedStyle(html).getPropertyValue("--neon").trim(),
                preview_color: getComputedStyle(html).getPropertyValue("--logo-preview-color").trim(),
            };
        })()
    ''')
    print(f'  {s}')

    print('\n=== Click PINK theme ===')
    page.click('#themeGridDash .theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            const html = document.documentElement;
            return {
                lt_color: getComputedStyle(lt).color,
                lt_inline_color: lt.style.color,
                neon: getComputedStyle(html).getPropertyValue("--neon").trim(),
                preview_color: getComputedStyle(html).getPropertyValue("--logo-preview-color").trim(),
            };
        })()
    ''')
    print(f'  {s}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix31_dash_pink.png')

    browser.close()
