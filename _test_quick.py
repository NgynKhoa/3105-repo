"""Quick test: 3 fixes on public_static (rebuilt)."""
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    # Test 1: Shadow
    page.click("#settingsBtn")
    page.wait_for_timeout(500)
    page.evaluate("document.querySelector('.user-style-tab[data-tab=shadow]').click()")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('userPaletteGrid').querySelector('[data-color=pink]').click()")
    page.wait_for_timeout(800)
    shadow_state = page.evaluate("""() => {
        const r = getComputedStyle(document.documentElement);
        return {
            user_shadowTheme: localStorage.getItem('user_shadowTheme'),
            logo_shadow_color: r.getPropertyValue('--logo-shadow-color').trim(),
        };
    }""")
    print(f"Shadow state: {shadow_state}")

    # Test 2: Cover
    cover_state = page.evaluate("""() => {
        const c = document.getElementById('mpCover');
        return c ? {bgImage: getComputedStyle(c).backgroundImage} : {missing: true};
    }""")
    print(f"Cover state: {cover_state}")

    # Test 3: Back button on blog.html
    page2 = ctx.new_page()
    page2.goto(URL + "blog.html?id=1", wait_until="domcontentloaded", timeout=30000)
    page2.wait_for_timeout(4000)
    back_links = page2.evaluate("""() => {
        return Array.from(document.querySelectorAll('.back-btn, .post-back-link')).map(el => ({
            class: el.className, href: el.getAttribute('href')
        }));
    }""")
    print(f"Back links: {back_links}")

    # Try clicking back-btn → check no 404
    page2.click(".back-btn")
    page2.wait_for_timeout(3000)
    print(f"After back-btn click URL: {page2.url}")

    b.close()
