from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Binary search
        result = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                const text = scripts[2].textContent;
                const lines = text.split('\\n');

                // Try to parse and find which line causes error
                let line = '';
                let error = null;
                for (let i = 1; i <= lines.length; i++) {
                    const subset = lines.slice(0, i).join('\\n');
                    try {
                        new Function(subset);
                    } catch (e) {
                        line = i;
                        error = e.message;
                        break;
                    }
                }
                return { errorLine: line, error: error };
            }
        """)
        print(f"Result: {result}")

        browser.close()

run_tests()
