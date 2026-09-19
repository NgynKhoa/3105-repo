"""Test USER THEME PICKER trên GH Pages (hoặc public_static nếu có)."""
from playwright.sync_api import sync_playwright

URLS = [
    ("public_static", "http://127.0.0.1:8765/"),
    ("gh_live", "https://ngynkhoa.github.io/3105-repo/"),
]


def test_one(label, url):
    print(f"\n=== {label}: {url} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        # 1. Open Settings menu
        page.click("#settingsBtn")
        page.wait_for_timeout(500)

        # 2. Check userThemeGroup visible + has palette
        info = page.evaluate("""() => {
            const userGroup = document.getElementById('userThemeGroup');
            const adminGroup = document.getElementById('adminThemeGroup');
            const userGrid = document.getElementById('userPaletteGrid');
            const userPaletteFor = document.getElementById('userPaletteFor');
            const userStyleTabs = document.getElementById('userStyleTabs');
            return {
                PUBLIC_MODE: !!window.PUBLIC_MODE,
                isAuthOwner: !!window.__isAuthOwner,
                userGroup_display: userGroup ? getComputedStyle(userGroup).display : 'missing',
                adminGroup_display: adminGroup ? getComputedStyle(adminGroup).display : 'missing',
                userGrid_buttonCount: userGrid ? userGrid.querySelectorAll('.theme-btn').length : 0,
                userStyleTabs_buttonCount: userStyleTabs ? userStyleTabs.querySelectorAll('button').length : 0,
                has_bg_tab: userStyleTabs ? !!userStyleTabs.querySelector('[data-tab="bg"]') : false,
                paletteFor: userPaletteFor ? userPaletteFor.textContent : null,
            };
        }""")
        print(f"  Info: {info}")

        # 3. Click theme button 'pink' in userThemeGroup
        page.evaluate("""() => {
            const grid = document.getElementById('userPaletteGrid');
            const btn = grid && grid.querySelector('[data-color="pink"]');
            if (btn) btn.click();
        }""")
        page.wait_for_timeout(500)

        # 4. Verify localStorage + CSS var
        state = page.evaluate("""() => {
            return {
                user_theme: localStorage.getItem('user_theme'),
                user_shadowTheme: localStorage.getItem('user_shadowTheme'),
                neon_css: getComputedStyle(document.documentElement).getPropertyValue('--neon'),
                bg_css: getComputedStyle(document.documentElement).getPropertyValue('--bg'),
            };
        }""")
        print(f"  After click pink: {state}")

        # 5. Reload page → theme should persist
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        state_after = page.evaluate("""() => {
            return {
                user_theme: localStorage.getItem('user_theme'),
                neon_css: getComputedStyle(document.documentElement).getPropertyValue('--neon'),
            };
        }""")
        print(f"  After reload: {state_after}")

        # 6. Screenshot
        page.click("#settingsBtn")  # reopen
        page.wait_for_timeout(300)
        page.screenshot(path=f"_screenshot_user_theme_{label}.png", full_page=True)
        print(f"  Screenshot saved.")

        browser.close()


for label, url in URLS:
    try:
        test_one(label, url)
    except Exception as e:
        print(f"  ERR {label}: {e}")
