"""Test user theme picker end-to-end."""
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)

    # 1. Open Settings
    page.click("#settingsBtn")
    page.wait_for_timeout(500)

    info = page.evaluate("""() => {
        const ug = document.getElementById('userThemeGroup');
        const grid = document.getElementById('userPaletteGrid');
        const tabs = document.getElementById('userStyleTabs');
        return {
            userGroup_display: ug ? getComputedStyle(ug).display : 'missing',
            grid_buttons: grid ? grid.querySelectorAll('.theme-btn').length : 0,
            tab_buttons: tabs ? tabs.querySelectorAll('button').length : 0,
            has_bg_tab: tabs ? !!tabs.querySelector('[data-tab="bg"]') : false,
        };
    }""")
    print("1. UI loaded:", info)

    # 2. Click pink theme
    page.evaluate("document.getElementById('userPaletteGrid').querySelector('[data-color=pink]').click()")
    page.wait_for_timeout(500)
    state = page.evaluate("""() => ({
        user_theme: localStorage.getItem('user_theme'),
        neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
    })""")
    print("2. After pink click:", state)

    # 3. Click shadow tab + lavender
    page.evaluate("document.querySelector('.user-style-tab[data-tab=shadow]').click()")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('userPaletteGrid').querySelector('[data-color=lavender]').click()")
    page.wait_for_timeout(500)
    state2 = page.evaluate("""() => ({
        user_theme: localStorage.getItem('user_theme'),
        user_shadowTheme: localStorage.getItem('user_shadowTheme'),
    })""")
    print("3. After shadow lavender:", state2)

    # 4. Reload page
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    state3 = page.evaluate("""() => ({
        user_theme: localStorage.getItem('user_theme'),
        user_shadowTheme: localStorage.getItem('user_shadowTheme'),
        neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
        shadow_theme_css: getComputedStyle(document.documentElement).getPropertyValue('--shadow-theme').trim(),
    })""")
    print("4. After reload:", state3)

    page.screenshot(path="_screenshot_user_theme_final.png", full_page=True)
    print("Screenshot saved")
    b.close()
