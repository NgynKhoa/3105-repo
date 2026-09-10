# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    # Force no-cache
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(f'{BASE}/dashboard?_=d1&t={123}')
    page.wait_for_timeout(3000)

    # Direct check: what is the rendered text-shadow on .dash-logo-text?
    result = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoText');
            if (!p) return 'no element';
            const cs = getComputedStyle(p);
            // List all matching CSS rules for .dash-logo-text
            const sheets = document.styleSheets;
            const matches = [];
            for (let sheet of sheets) {
                try {
                    for (let rule of sheet.cssRules) {
                        if (rule.selectorText && rule.selectorText.includes('dash-logo-text')) {
                            matches.push({
                                selector: rule.selectorText,
                                textShadow: rule.style.textShadow || 'none',
                            });
                        }
                    }
                } catch (e) {}
            }
            return {
                css_var_shadow: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb'),
                css_var_holo: getComputedStyle(document.documentElement).getPropertyValue('--logo-holo'),
                css_var_glow_alpha: getComputedStyle(document.documentElement).getPropertyValue('--logo-glow-alpha'),
                css_var_glow_radius: getComputedStyle(document.documentElement).getPropertyValue('--logo-glow-radius'),
                css_var_stroke: getComputedStyle(document.documentElement).getPropertyValue('--logo-stroke'),
                computed_text_shadow: cs.textShadow,
                computed_stroke: cs.webkitTextStroke,
                computed_color: cs.color,
                matching_rules: matches,
            };
        })()
    ''')
    print(f'Result: {result}')

    browser.close()
