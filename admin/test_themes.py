from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto("http://127.0.0.1:5050")
    time.sleep(2)
    page.click("#settingsBtn")
    time.sleep(1)
    page.click('[data-theme="pink"]')
    time.sleep(1)
    page.screenshot(path="test_pink_theme.png", full_page=False)
    page.click('[data-theme="cyan"]')
    time.sleep(1)
    page.screenshot(path="test_cyan_theme.png", full_page=False)
    browser.close()
    print("OK")
