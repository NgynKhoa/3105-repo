"""Verify GH Pages live after deploy."""
from playwright.sync_api import sync_playwright

URL = "https://ngynkhoa.github.io/3105-repo/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    # Check userThemeGroup exists + visible
    info = page.evaluate("""() => {
        const ug = document.getElementById('userThemeGroup');
        const grid = document.getElementById('userPaletteGrid');
        const tabs = document.getElementById('userStyleTabs');
        return {
            userGroup_exists: !!ug,
            userGroup_display: ug ? getComputedStyle(ug).display : 'missing',
            grid_buttons: grid ? grid.querySelectorAll('.theme-btn').length : 0,
            tab_buttons: tabs ? tabs.querySelectorAll('button').length : 0,
            has_bg_tab: tabs ? !!tabs.querySelector('[data-tab="bg"]') : false,
            // Also check blog height
            blog_h: document.getElementById('blog-section') ? getComputedStyle(document.getElementById('blog-section')).height : null,
        };
    }""")
    print("UI state:", info)

    # Open settings + click pink
    page.click("#settingsBtn")
    page.wait_for_timeout(500)
    page.evaluate("document.getElementById('userPaletteGrid').querySelector('[data-color=pink]').click()")
    page.wait_for_timeout(500)
    state = page.evaluate("""() => ({
        user_theme: localStorage.getItem('user_theme'),
        neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
    })""")
    print("After click pink:", state)

    page.screenshot(path="_screenshot_gh_after.png", full_page=True)
    print("Screenshot saved")

    # Reload + verify persist
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    state2 = page.evaluate("""() => ({
        user_theme: localStorage.getItem('user_theme'),
        neon: getComputedStyle(document.documentElement).getPropertyValue('--neon').trim(),
        blog_h: getComputedStyle(document.getElementById('blog-section')).height,
    })""")
    print("After reload:", state2)

    b.close()
