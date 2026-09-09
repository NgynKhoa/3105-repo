from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get script 2 content
        script_content = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                return {
                    count: scripts.length,
                    scripts: Array.from(scripts).map((s, i) => ({
                        index: i,
                        src: s.src || 'inline',
                        length: s.textContent.length,
                        preview: s.textContent.substring(0, 200)
                    }))
                };
            }
        """)
        print(f"Scripts: {script_content}")

        # Get the full settings script
        full_script = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                return scripts[2].textContent;
            }
        """)
        print(f"\nScript 2 full length: {len(full_script)}")

        # Find transparency section
        idx = full_script.find('rangeTransparency')
        if idx >= 0:
            print(f"\nAround transparency ({idx}):")
            print(repr(full_script[max(0,idx-200):idx+500]))

        browser.close()

run_tests()
