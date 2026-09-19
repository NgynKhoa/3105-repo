"""Verify GH Pages after deploy."""
from playwright.sync_api import sync_playwright

URL = "https://ngynkhoa.github.io/3105-repo/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    failures = []
    page.on("response", lambda r: failures.append((r.url, r.status)) if r.status >= 400 and 'fonts.gstatic' not in r.url and 'fonts.googleapis' not in r.url else None)
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(6000)

    # Test 1: Shadow
    page.click("#settingsBtn")
    page.wait_for_timeout(500)
    page.evaluate("document.querySelector('.user-style-tab[data-tab=shadow]').click()")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('userPaletteGrid').querySelector('[data-color=pink]').click()")
    page.wait_for_timeout(1000)
    shadow = page.evaluate("""() => {
        const r = getComputedStyle(document.documentElement);
        return {
            logo_shadow_color: r.getPropertyValue('--logo-shadow-color').trim(),
            logo_holo_color: r.getPropertyValue('--logo-holo-color').trim(),
        };
    }""")
    print(f"Shadow: {shadow}")

    # Test 2: Cover
    cover = page.evaluate("""() => {
        const c = document.getElementById('mpCover');
        return c ? {bgImage: getComputedStyle(c).backgroundImage} : {missing: true};
    }""")
    print(f"Cover: {cover}")

    # Test 3: Back button
    p2 = ctx.new_page()
    p2_failures = []
    p2.on("response", lambda r: p2_failures.append((r.url, r.status)) if r.status >= 400 and 'fonts.gstatic' not in r.url and 'fonts.googleapis' not in r.url else None)
    p2.goto(URL + "blog.html?id=1", wait_until="domcontentloaded", timeout=30000)
    p2.wait_for_timeout(4000)
    back = p2.evaluate("""() => Array.from(document.querySelectorAll('.back-btn, .post-back-link')).map(el => ({
        class: el.className, href: el.getAttribute('href')
    }))""")
    print(f"Back links: {back}")

    # Network failures
    print(f"\nMain page 404s ({len([f for f in failures if f[1] >= 400])}):")
    for u, s in [f for f in failures if f[1] >= 400][:5]:
        print(f"  {s} {u}")
    print(f"\nBlog page 404s ({len([f for f in p2_failures if f[1] >= 400])}):")
    for u, s in [f for f in p2_failures if f[1] >= 400][:5]:
        print(f"  {s} {u}")
    b.close()
