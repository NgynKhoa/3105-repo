# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    # ===== Front: HELLO + trail =====
    print('=== Front: HELLO + cursor trail ===')
    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)

    hello = page.evaluate('''
        (() => {
            const h = document.getElementById('helloBanner');
            if (!h) return null;
            const s = getComputedStyle(h);
            return { color: s.color, text_shadow: s.textShadow };
        })()
    ''')
    print(f'  HELLO: {hello}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_hello_dark.png')

    # Switch to cyan theme
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.click('#tabTheme')
    page.wait_for_timeout(200)
    page.click('.theme-btn[data-theme="cyan"]')
    page.wait_for_timeout(300)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_hello_cyan.png')

    hello_cyan = page.evaluate('''
        (() => {
            const h = document.getElementById('helloBanner');
            if (!h) return null;
            return getComputedStyle(h).color;
        })()
    ''')
    print(f'  HELLO after cyan: {hello_cyan}')

    # ===== Tab switching Theme/Shadow =====
    print('\n=== Theme/Shadow tabs ===')
    page.click('#tabShadow')
    page.wait_for_timeout(300)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_shadow_tab.png')

    # Pick pink for shadow
    page.click('.shadow-btn[data-shadow="pink"]')
    page.wait_for_timeout(300)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_shadow_pink.png')

    logo_style = page.evaluate('''
        (() => {
            const el = document.querySelector('#logo-text .lt');
            if (!el) return null;
            return {
                text_shadow: el.style.textShadow,
                stroke: el.style.webkitTextStroke,
                css_var: getComputedStyle(document.documentElement).getPropertyValue('--logo-shadow-rgb'),
            };
        })()
    ''')
    print(f'  Logo shadow after pink: {logo_style}')

    page.click('#closeSettings')
    page.wait_for_timeout(300)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_full_front.png')

    # ===== Dashboard Logo Editor =====
    print('\n=== Dashboard Logo Editor ===')
    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(2500)

    # Check preview exists
    preview_check = page.evaluate('''
        (() => {
            const p = document.getElementById('dashLogoPreview');
            if (!p) return null;
            const lt = document.getElementById('dashLogoText');
            return {
                has_preview: !!p,
                preview_text: lt ? lt.textContent : null,
                font: lt ? lt.style.fontFamily : null,
                font_size: lt ? lt.style.fontSize : null,
            };
        })()
    ''')
    print(f'  Preview: {preview_check}')

    # Test change logo text
    page.fill('#logoText', 'HELLO')
    page.wait_for_timeout(300)
    text_check = page.evaluate('document.getElementById("dashLogoText").textContent')
    print(f'  After change logoText=HELLO: preview="{text_check}"')

    # Test change font
    page.select_option('#logoFont', "'VT323', monospace")
    page.wait_for_timeout(300)
    font_check = page.evaluate('document.getElementById("dashLogoText").style.fontFamily')
    print(f'  After change font: {font_check}')

    # Test change size
    page.evaluate("document.getElementById('logoFontSize').value=70; document.getElementById('logoFontSize').dispatchEvent(new Event('input'))")
    page.wait_for_timeout(300)
    size_check = page.evaluate('document.getElementById("dashLogoText").style.fontSize')
    print(f'  After change size: {size_check}')

    # Test change depth
    page.evaluate("document.getElementById('logoDepth').value=6; document.getElementById('logoDepth').dispatchEvent(new Event('input'))")
    page.wait_for_timeout(300)

    # Test change glow
    page.evaluate("document.getElementById('logoGlowRadius').value=100; document.getElementById('logoGlowRadius').dispatchEvent(new Event('input'))")
    page.wait_for_timeout(300)

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_dash_logo_editor.png')

    # Save and check
    page.evaluate('saveGeneral()')
    page.wait_for_timeout(500)

    saved = page.evaluate('''
        (() => {
            return {
                text: localStorage.getItem('repo_logoText'),
                font: localStorage.getItem('repo_logoFont'),
                size: localStorage.getItem('repo_logoFontSize'),
                depth: localStorage.getItem('repo_logoDepth'),
                glow: localStorage.getItem('repo_logoGlowRadius'),
            };
        })()
    ''')
    print(f'  Saved: {saved}')

    # Reload front and check
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2500)
    front_logo = page.evaluate('''
        (() => {
            const el = document.querySelector('#logo-text .lt');
            if (!el) return null;
            return {
                text: el.textContent,
                font: el.style.fontFamily,
                size: el.style.fontSize,
                shadow_set: el.style.textShadow.substring(0, 100),
            };
        })()
    ''')
    print(f'  Front after reload: {front_logo}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix18_front_after_save.png')

    browser.close()
    print('\n=== DONE ===')
