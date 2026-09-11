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
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabShadow')
    page.wait_for_timeout(200)
    page.click('.shadow-btn[data-shadow="orange"]')
    page.wait_for_timeout(300)
    page.click('#closeSettings')
    page.wait_for_timeout(500)

    info = page.evaluate('''
        (() => {
            const lt = document.querySelector("#logo-text .lt");
            const parent = document.getElementById("logo-text");
            return {
                lt_color: getComputedStyle(lt).color,
                lt_textShadow: getComputedStyle(lt).textShadow,
                lt_stroke: getComputedStyle(lt).webkitTextStroke,
                lt_inline_color: lt.style.color,
                parent_color: getComputedStyle(parent).color,
                neon_var: getComputedStyle(document.documentElement).getPropertyValue("--neon").trim(),
                logo_shadow_rgb: getComputedStyle(document.documentElement).getPropertyValue("--logo-shadow-rgb").trim(),
            };
        })()
    ''')
    for k, v in info.items():
        print(f'{k}: {v}')

    browser.close()
