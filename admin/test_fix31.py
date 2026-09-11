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

    print('=== Fresh: dashboard with green theme ===')
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                preview_color: getComputedStyle(document.documentElement).getPropertyValue("--logo-preview-color").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix31_dash_initial.png')

    print('\n=== Click PINK theme in Style tab ===')
    page.click('.dash-tab[data-tab="style"]')
    page.wait_for_timeout(300)
    page.click('#themeGridDash .theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)
    page.click('.dash-tab[data-tab="general"]')
    page.wait_for_timeout(300)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                preview_color: getComputedStyle(document.documentElement).getPropertyValue("--logo-preview-color").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix31_dash_pink_theme.png')

    print('\n=== Click CYAN theme in Style tab ===')
    page.click('.dash-tab[data-tab="style"]')
    page.wait_for_timeout(300)
    page.click('#themeGridDash .theme-btn[data-theme="cyan"]')
    page.wait_for_timeout(500)
    page.click('.dash-tab[data-tab="general"]')
    page.wait_for_timeout(300)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                preview_color: getComputedStyle(document.documentElement).getPropertyValue("--logo-preview-color").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix31_dash_cyan_theme.png')

    browser.close()
