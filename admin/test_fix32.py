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

    print('=== Fresh: theme=green, logo preview should be green ===')
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
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix32_dash_green.png')

    print('\n=== Open Style tab, click PINK theme ===')
    page.click('.dash-tab[data-tab="style"]')
    page.wait_for_timeout(500)
    page.click('#themeGridDash .theme-btn[data-theme="pink"]')
    page.wait_for_timeout(500)

    # Verify theme applied to body
    body_color = page.evaluate('getComputedStyle(document.body).textShadow')
    print(f'  body text-shadow (sample of theme color): {body_color[:80]}...')

    # Switch back to general to see logo preview
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
    print(f'  After PINK theme: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix32_dash_pink.png')

    print('\n=== Click CYAN theme ===')
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
    print(f'  After CYAN theme: {s}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix32_dash_cyan.png')

    browser.close()
