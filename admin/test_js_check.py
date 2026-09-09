from playwright.sync_api import sync_playwright
import json

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get all scripts and try to find error
        result = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                const out = [];
                for (let i = 0; i < scripts.length; i++) {
                    const text = scripts[i].textContent;
                    try {
                        new Function(text);
                        out.push({i: i, status: 'OK', len: text.length});
                    } catch (e) {
                        // Find the line
                        out.push({i: i, status: 'ERROR', msg: e.message, len: text.length});
                    }
                }
                return out;
            }
        """)
        print(json.dumps(result, indent=2))

        browser.close()

run_tests()
