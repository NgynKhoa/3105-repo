from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Clear cookies/storage to start fresh
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Clear localStorage on first run
        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(2000)

        # Test 1: Settings menu opens
        print("Test 1: Settings menu opens...")
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        visible = page.locator("#settingsMenu").is_visible()
        print(f"  - Menu visible: {visible}")
        page.screenshot(path="final_1_settings_open.png", full_page=False)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # Test 2: Theme switching
        print("\nTest 2: Theme switching...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.click('[data-theme="cyan"]')
        page.wait_for_timeout(500)
        page.screenshot(path="final_2_cyan.png", full_page=False)
        page.click('[data-theme="pink"]')
        page.wait_for_timeout(500)
        page.screenshot(path="final_3_pink.png", full_page=False)
        page.click('[data-theme="green"]')
        page.wait_for_timeout(500)
        page.click("#closeSettings")

        # Test 3: Transparency
        print("\nTest 3: Transparency...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("""
            document.getElementById('rangeTransparency').value = 30;
            document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));
        """)
        page.wait_for_timeout(500)
        page.screenshot(path="final_4_transparency_30.png", full_page=False)
        page.click("#closeSettings")
        page.wait_for_timeout(300)
        page.evaluate("""
            document.getElementById('rangeTransparency').value = 92;
            document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));
        """)

        # Test 4: Dashboard
        print("\nTest 4: Dashboard...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        page.screenshot(path="final_5_dashboard.png", full_page=False)
        print(f"  - Tabs: {page.locator('.dash-tab').count()}")

        # Test 5: Dashboard boxes
        page.click('[data-tab="boxes"]')
        page.wait_for_timeout(500)
        page.screenshot(path="final_6_boxes.png", full_page=False)
        print(f"  - Box items: {page.locator('.box-item').count()}")

        # Test 6: Dashboard blog panel
        page.click('[data-tab="blog"]')
        page.wait_for_timeout(500)
        page.screenshot(path="final_7_blog_panel.png", full_page=False)
        print(f"  - Blog items: {page.locator('.blog-item').count()}")

        # Test 7: Dashboard style panel (theme)
        page.click('[data-tab="style"]')
        page.wait_for_timeout(500)
        page.screenshot(path="final_8_style.png", full_page=False)

        # Test 8: Theme switching in dashboard
        page.click('#themeGridDash [data-theme="pink"]')
        page.wait_for_timeout(500)
        page.screenshot(path="final_9_dash_pink.png", full_page=False)

        # Test 9: Blog page
        print("\nTest 9: Blog page...")
        page.goto(f"{BASE}/blog")
        page.wait_for_timeout(2000)
        page.screenshot(path="final_10_blog.png", full_page=False)
        print(f"  - Blog cards: {page.locator('.blog-card').count()}")

        # Test 10: Blog post in new tab (target=_blank)
        cards = page.locator(".blog-card")
        if cards.count() > 0:
            target = cards.first.get_attribute("target")
            href = cards.first.get_attribute("href")
            print(f"  - Card target: {target} (should be _blank)")
            print(f"  - Card href: {href} (should be /blog-post/*)")

        # Test 11: Blog post standalone page
        page.goto(f"{BASE}/blog-post/1")
        page.wait_for_timeout(2000)
        page.screenshot(path="final_11_post.png", full_page=False)

        # Test 12: Dark mode toggle
        print("\nTest 12: Dark mode toggle...")
        page.goto(BASE)
        page.wait_for_timeout(2000)
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.click('label[for=""], #toggleDarkMode')  # Click dark mode toggle
        # Actually click checkbox
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        # Now in light mode
        page.screenshot(path="final_12_light_mode.png", full_page=False)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        # Back to dark mode
        page.screenshot(path="final_13_dark_mode.png", full_page=False)

        browser.close()
        print("\n=== ALL TESTS COMPLETED ===")

run_tests()
