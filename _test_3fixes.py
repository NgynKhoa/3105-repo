"""End-to-end test cho 3 fixes:
  1. Shadow theme: user click → --logo-shadow-color update
  2. Music cover: applyCover rewrite localhost → relative
  3. Blog back button: href './' or './blog.html' (no 404)
"""
from playwright.sync_api import sync_playwright

URLS = [
    ("public_static", "http://127.0.0.1:8765/"),
    ("gh_live", "https://ngynkhoa.github.io/3105-repo/"),
]


def test(label, url):
    print(f"\n{'='*60}\n=== {label}: {url} ===\n{'='*60}")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # Track network failures (404 etc.)
        failures = []
        page.on("response", lambda r: failures.append((r.url, r.status)) if r.status >= 400 else None)

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        # ===== TEST 1: SHADOW THEME =====
        print("\n--- Test 1: Shadow theme ---")
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        # Switch to shadow tab
        page.evaluate("document.querySelector('.user-style-tab[data-tab=shadow]').click()")
        page.wait_for_timeout(300)
        # Click pink in shadow tab
        page.evaluate("document.getElementById('userPaletteGrid').querySelector('[data-color=pink]').click()")
        page.wait_for_timeout(800)
        shadow_state = page.evaluate("""() => {
            const r = getComputedStyle(document.documentElement);
            return {
                user_shadowTheme: localStorage.getItem('user_shadowTheme'),
                logo_shadow_color: r.getPropertyValue('--logo-shadow-color').trim(),
                logo_shadow_rgb: r.getPropertyValue('--logo-shadow-rgb').trim(),
                logo_holo_color: r.getPropertyValue('--logo-holo-color').trim(),
            };
        }""")
        print(f"  shadow state: {shadow_state}")
        # Check logo text color (visible change)
        logo_state = page.evaluate("""() => {
            const el = document.getElementById('logo-text');
            if (!el) return {missing: true};
            const cs = getComputedStyle(el);
            return {
                color: cs.color,
                textShadow: cs.textShadow.substring(0, 100),
            };
        }""")
        print(f"  logo state: {logo_state}")

        # ===== TEST 2: MUSIC COVER =====
        print("\n--- Test 2: Music cover ---")
        cover_state = page.evaluate("""() => {
            const cover = document.getElementById('mpCover');
            if (!cover) return {missing: true};
            return {
                bgImage: getComputedStyle(cover).backgroundImage,
                has_image: cover.classList.contains('has-image'),
            };
        }""")
        print(f"  cover state: {cover_state}")

        # ===== TEST 3: BLOG BACK BUTTON =====
        print("\n--- Test 3: Blog back button ---")
        # Click first blog item → open blog detail
        # Need to be on /blog.html?id=X page
        page.close()
        ctx2 = b.new_context(viewport={"width": 1280, "height": 900})
        page2 = ctx2.new_page()
        # Capture network failures from blog.html context
        blog_failures = []
        page2.on("response", lambda r: blog_failures.append((r.url, r.status)) if r.status >= 400 else None)
        blog_url = url.rstrip("/") + "/blog.html?id=1"
        page2.goto(blog_url, wait_until="domcontentloaded", timeout=30000)
        page2.wait_for_timeout(5000)

        # Check back-btn href
        back_links = page2.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.back-btn, .post-back-link').forEach(el => {
                out.push({
                    class: el.className,
                    href: el.getAttribute('href'),
                });
            });
            return out;
        }""")
        print(f"  back links: {back_links}")

        # Try clicking first back link → check if navigation works (no 404)
        if back_links:
            first_href = back_links[0]['href']
            print(f"  Testing click on first back link: {first_href}")
            # Don't actually navigate (would close this test), just verify the href doesn't look like /blog or /
            is_relative = first_href.startswith('./') or not first_href.startswith('/')
            print(f"  href is relative (good): {is_relative}")

        # Final 404 check from main page
        page_failures = [f for f in failures if f[1] >= 400]
        page2_failures = [f for f in blog_failures if f[1] >= 400]
        print(f"\n--- Network failures on main page ({len(page_failures)}) ---")
        for u, s in page_failures[:10]:
            print(f"  {s} {u}")
        print(f"\n--- Network failures on blog page ({len(page2_failures)}) ---")
        for u, s in page2_failures[:10]:
            print(f"  {s} {u}")

        # Screenshot
        page2.screenshot(path=f"_screenshot_3fixes_{label}.png", full_page=True)
        b.close()


for label, url in URLS:
    try:
        test(label, url)
    except Exception as e:
        print(f"  ERR {label}: {e}")
