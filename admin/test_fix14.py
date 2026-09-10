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

    # Front repo
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

    # ===== Test rain =====
    print('\n=== Rain test (dashboard) ===')
    # Close settings menu, test rain
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    rain_check = page.evaluate('''
        (() => {
            const c = document.getElementById('rain-canvas');
            if (!c) return 'no_canvas';
            const ctx = c.getContext('2d');
            const data = ctx.getImageData(0, 0, c.width, c.height).data;
            // Count non-zero pixels (rain drops)
            let count = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i+3] > 0) count++;
            }
            return {
                canvas_width: c.width,
                canvas_height: c.height,
                rain_pixels: count,
                has_window_initRain: typeof window.initRain === 'function',
                rainEnabled: window.rainEnabled,
                heavyRain: window.heavyRain,
                drops_count: window.drops ? window.drops.length : 'undefined'
            };
        })()
    ''')
    print(f'  Dashboard rain check: {rain_check}')

    page.wait_for_timeout(2000)
    rain_check2 = page.evaluate('''
        (() => {
            const c = document.getElementById('rain-canvas');
            if (!c) return 'no_canvas';
            const ctx = c.getContext('2d');
            const data = ctx.getImageData(0, 0, c.width, c.height).data;
            let count = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i+3] > 0) count++;
            }
            return count;
        })()
    ''')
    print(f'  Dashboard rain pixels after 2s: {rain_check2}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix14_dash_rain.png')

    browser.close()
    print('\n=== DONE ===')
