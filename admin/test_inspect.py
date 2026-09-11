# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto(BASE + '/dashboard?_=' + str(__import__('time').time()))
    page.wait_for_timeout(3000)

    # Check the actual color computed value of .dash-logo-text
    info = page.evaluate('''
        (() => {
            const lt = document.querySelector("#dashLogoText");
            const cs = getComputedStyle(lt);
            const html = document.documentElement;
            // Find which CSS rules match .dash-logo-text with color
            const matching = [];
            for (const ss of document.styleSheets) {
                try {
                    for (const r of ss.cssRules) {
                        if (r.style && r.style.color && lt.matches(r.selectorText)) {
                            matching.push({sel: r.selectorText, color: r.style.color});
                        }
                    }
                } catch(e){}
            }
            return {
                color: cs.color,
                inline_style: lt.getAttribute("style") || "(none)",
                matching: matching,
                neon_var: getComputedStyle(html).getPropertyValue("--neon").trim(),
                preview_color_var: getComputedStyle(html).getPropertyValue("--logo-preview-color").trim(),
                // Try via cssStyleDeclaration
                lt_color_declaration: cs.getPropertyValue("color"),
            };
        })()
    ''')
    for k, v in info.items():
        print(f'{k}:')
        print(f'  {v}')

    # Also fetch raw HTML to verify CSS contains var change
    html_content = page.content()
    if 'color: var(--logo-preview-color)' in html_content:
        print('\n[OK] Template has color: var(--logo-preview-color)')
    else:
        print('\n[FAIL] Template missing color: var(--logo-preview-color)')
    if '--logo-preview-color: #80ff40' in html_content:
        print('[OK] Template has --logo-preview-color: #80ff40')
    else:
        print('[FAIL] Template missing --logo-preview-color: #80ff40')

    browser.close()
