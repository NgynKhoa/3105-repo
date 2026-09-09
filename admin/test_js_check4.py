from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get line 2
        result = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                const text = scripts[2].textContent;
                const lines = text.split('\\n');
                return {
                    line1: lines[0],
                    line2: lines[1],
                    line3: lines[2],
                    charCodes: Array.from(lines[1]).slice(0, 200).map(c => c.charCodeAt(0))
                };
            }
        """)
        print(f"Result: {result}")

        browser.close()

run_tests()
