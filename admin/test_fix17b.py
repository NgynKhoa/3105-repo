# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    print('=== Front repo settings slider test ===')
    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix17_front_dark.png')

    slider_check = page.evaluate('''
        (() => {
            const r = document.getElementById('rangeTransparency');
            if (!r) return null;
            const cs = getComputedStyle(r);
            return {
                border: cs.border,
                box_shadow: cs.boxShadow,
                outline: cs.outline,
                parent_padding: getComputedStyle(r.parentElement).padding,
            };
        })()
    ''')
    print(f'  Front slider: {slider_check}')

    # Toggle light mode
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)
    page.screenshot(path='c:/Users/NK/Desktop\MOD/3105-repo/admin/fix17_front_light.png'.replace('\\', '/'))

    # Close
    page.evaluate('document.getElementById("closeSettings").click()')
    page.wait_for_timeout(300)

    # Check hint box in light mode (on front page)
    print('\n=== Hint box (light mode) ===')
    hint_check = page.evaluate('''
        (() => {
            const h = document.querySelector('.hint-box');
            if (!h) return null;
            const cs = getComputedStyle(h);
            const b = h.getBoundingClientRect();
            return {
                bg: cs.backgroundColor,
                border_top: cs.borderTopColor,
                border_left: cs.borderLeftColor,
                color: cs.color,
                width: b.width,
            };
        })()
    ''')
    print(f'  Hint box: {hint_check}')

    browser.close()
    print('done')
