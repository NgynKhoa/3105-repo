# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    # ===== Test slider size =====
    print('=== Slider size comparison ===')
    page.goto(BASE + '?_=s1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')

    page.goto(BASE + '?_=s2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)

    front_slider = page.evaluate('''
        (() => {
            const r = document.getElementById('rangeTransparency');
            if (!r) return null;
            const rect = r.getBoundingClientRect();
            return { width: rect.width, height: rect.height };
        })()
    ''')
    print(f'  Front slider: {front_slider}')

    page.goto(f'{BASE}/dashboard?_=sd1')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)

    dash_slider = page.evaluate('''
        (() => {
            const r = document.getElementById('rangeTransparency');
            if (!r) return null;
            const rect = r.getBoundingClientRect();
            return { width: rect.width, height: rect.height };
        })()
    ''')
    print(f'  Dashboard slider: {dash_slider}')

    # ===== Test section title font =====
    print('\n=== Section title font ===')
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    title_font = page.evaluate('''
        (() => {
            const t = document.querySelector('.section-title');
            if (!t) return null;
            const s = getComputedStyle(t);
            return {
                font: s.fontFamily,
                size: s.fontSize,
                weight: s.fontWeight,
                color: s.color
            };
        })()
    ''')
    print(f'  Dashboard .section-title: {title_font}')

    # ===== Test Rain Opacity/Speed sliders =====
    print('\n=== Rain sliders ===')
    # Switch to Styles panel
    tabs = page.evaluate('Array.from(document.querySelectorAll(".dash-tab")).map(t => t.textContent.trim())')
    print(f'  Tabs: {tabs}')
    for tab_text in ['Style', 'Styles', 'Rain']:
        page.evaluate(f'''
            Array.from(document.querySelectorAll(".dash-tab")).forEach(t => {{
                if (t.textContent.includes("{tab_text}")) {{
                    t.click();
                }}
            }});
        ''')
    page.wait_for_timeout(800)

    rain_sliders = page.evaluate('''
        (() => {
            const r = {};
            ['baseFontSize', 'titleFontSize', 'rainOpacity', 'rainSpeed'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    const rect = el.getBoundingClientRect();
                    r[id] = { width: rect.width, height: rect.height };
                }
            });
            // Check active panel
            const activePanel = document.querySelector('.dash-panel.active');
            r['_active_panel'] = activePanel ? activePanel.id : 'none';
            return r;
        })()
    ''')
    print(f'  Rain/Font sliders: {rain_sliders}')

    # ===== Test music player buttons in light mode =====
    print('\n=== Music player light mode ===')
    page.goto(BASE + '?_=m1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=m2')
    page.wait_for_timeout(2500)

    # Toggle light mode
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    music_buttons = page.evaluate('''
        (() => {
            const btn = document.querySelector('.mp-btn');
            const main = document.querySelector('.mp-btn-main');
            const r = {};
            if (btn) {
                const s = getComputedStyle(btn);
                r.btn_bg = s.backgroundColor;
                r.btn_border = s.borderTopColor;
            }
            if (main) {
                const s = getComputedStyle(main);
                r.main_bg = s.backgroundColor;
            }
            // Check light mode active
            r.dark_checkbox = document.getElementById('toggleDarkMode').checked;
            return r;
        })()
    ''')
    print(f'  Music buttons (light mode): {music_buttons}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix15_music_light.png')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix15_dash_styles.png')

    browser.close()
    print('\n=== DONE ===')
