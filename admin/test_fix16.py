# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    # ===== Test slider thumb alignment =====
    print('=== Slider thumb alignment ===')
    page.goto(f'{BASE}/dashboard?_=a1')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)

    slider_check = page.evaluate('''
        (() => {
            const r = document.getElementById('rangeTransparency');
            if (!r) return 'no_slider';
            const rect = r.getBoundingClientRect();
            const style = getComputedStyle(r);
            return {
                width: rect.width,
                height: rect.height,
                input_bg: style.background,
                input_padding: style.padding,
                input_box_sizing: style.boxSizing,
            };
        })()
    ''')
    print(f'  Dashboard transparency slider: {slider_check}')

    page.click('#closeSettings')
    page.wait_for_timeout(200)

    # ===== Test rain opacity/speed responsiveness =====
    print('\n=== Rain opacity/speed responsiveness ===')

    # Get initial rain state
    page.goto(f'{BASE}/dashboard?_=r1')
    page.wait_for_timeout(2500)

    # Rain before change
    rain_before = page.evaluate('''
        (() => {
            const c = document.getElementById('rain-canvas');
            if (!c) return null;
            const ctx = c.getContext('2d');
            const data = ctx.getImageData(0, 0, Math.min(c.width, 400), Math.min(c.height, 300)).data;
            let count = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i+3] > 0) count++;
            }
            return {
                pixels: count,
                heavyRain: window.heavyRain,
                rainOpacity: window.rainOpacity,
                rainSpeed: window.rainSpeed
            };
        })()
    ''')
    print(f'  Rain BEFORE change: {rain_before}')

    # Open settings and go to Style tab
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.evaluate('''
        Array.from(document.querySelectorAll(".dash-tab")).forEach(t => {
            if (t.textContent.includes("Style")) t.click();
        });
    ''')
    page.wait_for_timeout(800)

    # Change rain speed
    rain_speed_slider = page.locator('#rainSpeed')
    if rain_speed_slider.count() > 0:
        # Set to max speed
        page.evaluate('''
            (() => {
                const el = document.getElementById('rainSpeed');
                el.value = 10;
                el.dispatchEvent(new Event('input'));
            })()
        ''')
        print('  Changed rainSpeed to 10')
    else:
        print('  rainSpeed slider not found')

    # Change rain opacity
    rain_op_slider = page.locator('#rainOpacity')
    if rain_op_slider.count() > 0:
        page.evaluate('''
            (() => {
                const el = document.getElementById('rainOpacity');
                el.value = 100;
                el.dispatchEvent(new Event('input'));
            })()
        ''')
        print('  Changed rainOpacity to 100')
    else:
        print('  rainOpacity slider not found')

    page.wait_for_timeout(1000)

    # Check after change
    rain_after = page.evaluate('''
        (() => {
            const c = document.getElementById('rain-canvas');
            if (!c) return null;
            const ctx = c.getContext('2d');
            const data = ctx.getImageData(0, 0, Math.min(c.width, 400), Math.min(c.height, 300)).data;
            let count = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i+3] > 0) count++;
            }
            return {
                pixels: count,
                heavyRain: window.heavyRain,
                rainOpacity: window.rainOpacity,
                rainSpeed: window.rainSpeed
            };
        })()
    ''')
    print(f'  Rain AFTER change: {rain_after}')

    if rain_before and rain_after:
        print(f'  Speed changed: {rain_before["rainSpeed"]} -> {rain_after["rainSpeed"]}')
        print(f'  Opacity changed: {rain_before["rainOpacity"]} -> {rain_after["rainOpacity"]}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix16_dash_sliders.png')

    # ===== Test front repo slider =====
    print('\n=== Front repo slider ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)
    page.click('#settingsBtn')
    page.wait_for_timeout(500)

    front_slider = page.evaluate('''
        (() => {
            const r = document.getElementById('rangeTransparency');
            if (!r) return 'no_slider';
            const rect = r.getBoundingClientRect();
            const style = getComputedStyle(r);
            return {
                width: rect.width,
                height: rect.height,
            };
        })()
    ''')
    print(f'  Front slider: {front_slider}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix16_front_slider.png')

    browser.close()
    print('\n=== DONE ===')
