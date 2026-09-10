# -*- coding: utf-8 -*-
"""Deep debug body bg"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(BASE + "?_=deep1")
    page.wait_for_timeout(1500)
    page.evaluate("localStorage.clear()")
    page.goto(BASE + "?_=deep2")
    page.wait_for_timeout(2500)

    page.click("#settingsBtn")
    page.wait_for_timeout(400)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)

    # Inspect body bg rules in cascade
    info = page.evaluate("""
        (() => {
            const body = document.body;
            const cs = getComputedStyle(body);
            return {
                bg: cs.background,
                bgColor: cs.backgroundColor,
                bgImage: cs.backgroundImage,
                // Find all stylesheets and look for body bg
                matchingRules: (() => {
                    const rules = [];
                    for (const sheet of document.styleSheets) {
                        try {
                            for (const rule of sheet.cssRules) {
                                if (rule.cssText && /body\\s*\\{/.test(rule.cssText)) {
                                    rules.push(rule.cssText);
                                }
                                if (rule.cssText && rule.cssText.includes('body') && rule.cssText.includes('background')) {
                                    if (!rules.includes(rule.cssText)) rules.push(rule.cssText);
                                }
                            }
                        } catch (e) {}
                    }
                    return rules;
                })(),
                inlineStyle: body.getAttribute('style') || ''
            };
        })()
    """)
    import json
    print(json.dumps(info, indent=2))

    browser.close()
