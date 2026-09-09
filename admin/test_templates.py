from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get full script
        full_script = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                return scripts[2].textContent;
            }
        """)

        # Look for template literals with potential issues
        import re
        # Find template literals
        template_pattern = r'`[^`]*`'
        matches = list(re.finditer(template_pattern, full_script))
        print(f"Found {len(matches)} template literals")

        # Check each template literal
        for i, m in enumerate(matches):
            tl = m.group()
            # Check if there's a mismatched ${}
            dollar_count = tl.count('${')
            brace_count = tl.count('}')
            if dollar_count != brace_count:
                print(f"Template literal {i}: MISMATCH ${dollar_count} vs }}{brace_count}")
                print(f"  Content: {repr(tl[:100])}")
                # Show context
                start = max(0, m.start() - 50)
                end = min(len(full_script), m.end() + 50)
                print(f"  Context: {repr(full_script[start:end])}")

        browser.close()

run_tests()
