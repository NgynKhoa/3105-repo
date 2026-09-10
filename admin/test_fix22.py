# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(3000)

    info = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            if (!p) return 'no element';
            return {
                id: p.id,
                className: p.className,
                tag: p.tagName,
                parent: p.parentElement.className,
                matches: p.matches('.dash-logo-text'),
                css_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb'),
                text_shadow: getComputedStyle(p).textShadow,
            };
        })()
    ''')
    print(f'Element: {info}')

    browser.close()
