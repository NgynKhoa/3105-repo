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

    print('=== Fresh Dashboard: logo preview = theme color (green) ===')
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            const html = document.documentElement;
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(html).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix33_dash_green.png')

    print('\n=== Switch to Style tab, click PINK theme ===')
    page.click('.dash-tab[data-tab="style"]')
    page.wait_for_timeout(500)
    page.click('#themeGridDash .theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)
    page.click('.dash-tab[data-tab="general"]')
    page.wait_for_timeout(500)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            const html = document.documentElement;
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(html).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix33_dash_pink.png')

    print('\n=== Switch to Style tab, click CYAN theme ===')
    page.click('.dash-tab[data-tab="style"]')
    page.wait_for_timeout(500)
    page.click('#themeGridDash .theme-btn[data-theme="cyan"]')
    page.wait_for_timeout(500)
    page.click('.dash-tab[data-tab="general"]')
    page.wait_for_timeout(500)
    s = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            const html = document.documentElement;
            return {
                lt_color: getComputedStyle(lt).color,
                neon: getComputedStyle(html).getPropertyValue("--neon").trim(),
            };
        })()
    ''')
    print(f'  {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix33_dash_cyan.png')

    browser.close()
