from playwright.sync_api import sync_playwright
import time, sys

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5050"
out = sys.argv[2] if len(sys.argv) > 2 else "screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(url)
    time.sleep(2)
    page.evaluate("window.scrollTo(0, 300)")
    time.sleep(1)
    page.screenshot(path=out, full_page=False)
    browser.close()
    print(f"Screenshot saved to {out}")
