from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        errors = []

        # Test 1: Home page
        print("Test 1: Home page...")
        page.goto(BASE)
        page.wait_for_timeout(2000)
        page.screenshot(path="test1_home.png", full_page=False)
        print("  - Settings button visible:", page.locator("#settingsBtn").is_visible())
        print("  - Blog section visible:", page.locator("#blog-section").is_visible())

        # Test 2: Settings menu opens
        print("\nTest 2: Settings menu...")
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        visible = page.locator("#settingsMenu").is_visible()
        print("  - Settings menu opened:", visible)
        page.screenshot(path="test2_settings.png", full_page=False)

        # Test 3: Theme switch
        print("\nTest 3: Theme switch...")
        page.click('[data-theme="pink"]')
        page.wait_for_timeout(500)
        page.screenshot(path="test3_pink_theme.png", full_page=False)
        page.click('[data-theme="cyan"]')
        page.wait_for_timeout(500)
        page.screenshot(path="test3_cyan_theme.png", full_page=False)

        # Test 4: Transparency slider
        print("\nTest 4: Transparency slider...")
        # Close settings first
        page.click("#closeSettings")
        page.wait_for_timeout(300)
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        # Set to 50%
        page.evaluate("document.getElementById('rangeTransparency').value = 50; document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));")
        page.wait_for_timeout(500)
        page.screenshot(path="test4_transparency.png", full_page=False)
        page.click("#closeSettings")

        # Test 5: Blog page
        print("\nTest 5: Blog page...")
        page.goto(f"{BASE}/blog")
        page.wait_for_timeout(2000)
        page.screenshot(path="test5_blog_list.png", full_page=False)
        blog_cards = page.locator(".blog-card").count()
        print(f"  - Blog cards found: {blog_cards}")

        # Test 6: Blog post in new tab
        print("\nTest 6: Blog post opens in new tab...")
        page.goto(f"{BASE}/blog")
        page.wait_for_timeout(2000)
        if blog_cards > 0:
            href = page.locator(".blog-card").first.get_attribute("href")
            print(f"  - Blog card href: {href}")
            # Check if it has target="_blank"
            target = page.locator(".blog-card").first.get_attribute("target")
            print(f"  - Opens in new tab: {target == '_blank'}")

        # Test 7: Dashboard page
        print("\nTest 7: Dashboard page...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        page.screenshot(path="test7_dashboard.png", full_page=False)
        print("  - Dashboard tabs visible:", page.locator(".dash-tab").count())

        # Test 8: Dashboard boxes tab
        print("\nTest 8: Dashboard boxes tab...")
        page.click('[data-tab="boxes"]')
        page.wait_for_timeout(500)
        page.screenshot(path="test8_boxes_tab.png", full_page=False)
        print("  - Box items:", page.locator(".box-item").count())

        # Test 9: Dashboard blog tab
        print("\nTest 9: Dashboard blog tab...")
        page.click('[data-tab="blog"]')
        page.wait_for_timeout(500)
        page.screenshot(path="test9_blog_tab.png", full_page=False)

        # Test 10: Dashboard style tab with theme
        print("\nTest 10: Dashboard style tab...")
        page.click('[data-tab="style"]')
        page.wait_for_timeout(500)
        page.screenshot(path="test10_style_tab.png", full_page=False)

        # Test 11: Dark mode toggle
        print("\nTest 11: Dark mode toggle on home...")
        page.goto(BASE)
        page.wait_for_timeout(2000)
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        page.screenshot(path="test11_light_mode.png", full_page=False)
        print("  - Dark mode toggled to light")

        # Test 12: Blog post page
        print("\nTest 12: Blog post standalone page...")
        page.goto(f"{BASE}/blog-post/1")
        page.wait_for_timeout(2000)
        page.screenshot(path="test12_blog_post.png", full_page=False)
        post_title = page.locator(".post-title").is_visible()
        print(f"  - Post title visible: {post_title}")

        browser.close()
        print("\n" + "="*50)
        print("ALL TESTS COMPLETED!")
        print("="*50)

run_tests()
