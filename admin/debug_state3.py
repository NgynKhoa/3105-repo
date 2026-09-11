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

    info = page.evaluate('''
        (() => {
            const lt = document.querySelector("#logo-text .lt");
            const cs = window.getComputedStyle(lt);
            return {
                inline_style_attr: lt.getAttribute("style") || "(none)",
                inline_color: lt.style.color,
                computed_color: cs.color,
                inherited_color: window.getComputedStyle(lt.parentNode).color,
                matching_rules: (() => {
                    // Try to find which rule sets color
                    const rules = [];
                    for (const ss of document.styleSheets) {
                        try {
                            for (const r of ss.cssRules) {
                                if (r.style && r.style.color && lt.matches(r.selectorText)) {
                                    rules.push(r.selectorText + ' => ' + r.style.color);
                                }
                            }
                        } catch(e){}
                    }
                    return rules;
                })(),
            };
        })()
    ''')
    for k, v in info.items():
        print(f'{k}:')
        print(f'  {v}')

    browser.close()
