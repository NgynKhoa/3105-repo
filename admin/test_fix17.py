# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix17_front_settings.png')
    print('front saved')

    # Check the range slider styles
    slider_check = page.evaluate('''
        (() => {
            const r = document.getElementById('rangeTransparency');
            if (!r) return 'no_slider';
            const cs = getComputedStyle(r);
            const parent = r.parentElement;
            const cs2 = getComputedStyle(parent);
            return {
                slider_outline: cs.outline,
                slider_border: cs.border,
                slider_box_shadow: cs.boxShadow,
                parent_border: cs2.border,
                parent_box_shadow: cs2.boxShadow,
                parent_class: parent.className,
            };
        })()
    ''')
    print(f'front slider: {slider_check}')

    browser.close()
    print('done')
