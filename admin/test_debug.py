from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Listen for console errors
        errors = []
        page.on("console", lambda msg: errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)

        # Test 1: Home page + settings
        print("Test 1: Home page + settings...")
        page.goto(BASE)
        page.wait_for_timeout(2000)
        page.screenshot(path="test1_home.png", full_page=False)
        print(f"  - Settings button visible: {page.locator('#settingsBtn').is_visible()}")
        print(f"  - Console errors: {len(errors)}")

        # Test 2: Click settings
        print("\nTest 2: Click settings button...")
        page.click("#settingsBtn")
        page.wait_for_timeout(1000)
        menu_visible = page.locator("#settingsMenu").is_visible()
        print(f"  - Settings menu visible: {menu_visible}")
        if not menu_visible:
            # Check if JS error
            print(f"  - Console errors: {errors}")
            # Check if element exists
            count = page.locator("#settingsMenu").count()
            print(f"  - Settings menu count: {count}")
            # Try to get display style
            display = page.evaluate("document.getElementById('settingsMenu').style.display")
            print(f"  - Settings menu display: '{display}'")
        page.screenshot(path="test2_settings.png", full_page=False)

        # Test 3: Try theme click via JS
        if menu_visible:
            print("\nTest 3: Theme switch...")
            page.click('[data-theme="pink"]')
            page.wait_for_timeout(500)
            page.screenshot(path="test3_pink.png", full_page=False)

        # Test 4: Dashboard
        print("\nTest 4: Dashboard...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        page.screenshot(path="test4_dashboard.png", full_page=False)

        # Test 5: Blog page
        print("\nTest 5: Blog list...")
        page.goto(f"{BASE}/blog")
        page.wait_for_timeout(2000)
        page.screenshot(path="test5_blog.png", full_page=False)
        print(f"  - Blog cards: {page.locator('.blog-card').count()}")

        # Test 6: Blog post new tab
        print("\nTest 6: Blog post page...")
        page.goto(f"{BASE}/blog-post/1")
        page.wait_for_timeout(2000)
        page.screenshot(path="test6_post.png", full_page=False)

        browser.close()
        print("\nDone!")

run_tests()
