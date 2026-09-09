from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # Test 1: Click blog post in /blog list
    page.goto("http://127.0.0.1:5050/blog")
    time.sleep(2)
    page.click(".blog-card:first-child")
    time.sleep(2)
    page.screenshot(path="test_blog_post.png", full_page=False)
    print("✓ Blog post click test passed")
    browser.close()
