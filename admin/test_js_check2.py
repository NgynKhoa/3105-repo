from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get script 2 and try parsing line by line
        result = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                const text = scripts[2].textContent;
                const lines = text.split('\\n');

                // Try each subset to find where error occurs
                for (let i = lines.length; i > 0; i--) {
                    const subset = lines.slice(0, i).join('\\n');
                    try {
                        new Function(subset);
                        return { lastOK: i, error: null };
                    } catch (e) {
                        return { lastOK: i, error: e.message };
                    }
                }
                return { lastOK: 0, error: null };
            }
        """)
        print(f"Result: {result}")

        browser.close()

run_tests()
