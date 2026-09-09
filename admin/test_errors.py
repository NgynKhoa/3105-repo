from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        errors = []
        page.on("pageerror", lambda err: errors.append(f"PAGE ERROR: {err}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE [{msg.type}]: {msg.text}") if msg.type in ["error", "warning"] else None)

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        print("All errors/warnings:")
        for e in errors:
            print(f"  {e}")

        # Check which script block has the error
        check = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                let result = [];
                scripts.forEach((s, i) => {
                    const src = s.src || 'inline';
                    if (src === 'inline' || src.includes('app.js')) {
                        try {
                            new Function(s.textContent);
                            result.push({index: i, src: src, error: null});
                        } catch(e) {
                            result.push({index: i, src: src, error: e.message, line: e.lineNumber});
                        }
                    }
                });
                return result;
            }
        """)
        print(f"\nScript check: {check}")

        browser.close()

run_tests()
