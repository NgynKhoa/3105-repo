from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get full script 2 content
        full_script = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                return scripts[2].textContent;
            }
        """)

        # Try to parse it line by line
        lines = full_script.split('\n')
        print(f"Total lines: {len(lines)}")

        # Find lines with only }
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == '}' and i < len(lines) - 1:
                next_line = lines[i+1].strip() if i+1 < len(lines) else ''
                # If next line doesn't start with a keyword or }, might be an issue
                if next_line and not (next_line.startswith('//') or next_line.startswith('/*') or
                                     next_line.startswith('}') or next_line.startswith('function') or
                                     next_line.startswith('if') or next_line.startswith('for') or
                                     next_line.startswith('while') or next_line.startswith('}') or
                                     next_line.startswith('else') or next_line.startswith('catch') or
                                     next_line.startswith('const') or next_line.startswith('var') or
                                     next_line.startswith('let') or next_line.startswith('return')):
                    print(f"Line {i+1}: {repr(line)} -> Next: {repr(next_line[:60])}")

        browser.close()

run_tests()
