"""Test admin login flow end-to-end."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))
        page.on("console", lambda msg: print(f"[{msg.type}]", msg.text[:200]) if msg.type in ("error", "warning", "log") else None)

        # Step 1: Open with ?slug=demo
        url = "http://127.0.0.1:5050/?slug=demo"
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        # Step 2: Check state BEFORE login
        pre_login = await page.evaluate("""
() => ({
    authBtn_visible: getComputedStyle(document.getElementById('btnLogin')).display,
    isOwner: window.__isAuthOwner,
    adminThemeGroup_visible: getComputedStyle(document.getElementById('adminThemeGroup')).display,
    pkgCount: document.getElementById('packageCount').textContent,
})
        """)
        print("=== PRE-LOGIN ===")
        print(pre_login)

        # Step 3: Click login button
        await page.click('#settingsBtn')
        await page.wait_for_timeout(300)
        print("Settings opened, taking screenshot")
        await page.screenshot(path="c:/Users/NK/Desktop/debug_login_btn.png")

        # Look for login link
        login_link = await page.query_selector('#btnLogin')
        if login_link:
            print("Login link found, navigating to OAuth...")
            # Get href
            href = await login_link.get_attribute('href')
            print(f"Login URL: {href}")
        else:
            print("Login link NOT FOUND")
            await browser.close()
            return

        # Step 4: Navigate to OAuth directly (don't actually authorize)
        # Just check the URL structure
        print(f"\n=== CHECKING OAUTH REDIRECT URL ===")
        if 'github.com/login/oauth' in href:
            print("OK: OAuth URL points to GitHub")
        if 'client_id=Ov23linCuHLxlwtKemzL' in href:
            print("OK: client_id present")
        if 'state=' in href:
            print("OK: state present (CSRF protection)")

        # Step 5: Simulate the OAuth callback redirect
        # In real flow: github redirects back to /auth/github/callback?code=xxx
        # For test: we'll directly check the redirect by making a GET
        await page.goto(f"http://127.0.0.1:5050/auth/github/login", wait_until="networkidle", timeout=10000)
        # This SHOULD redirect to github.com
        final_url = page.url
        print(f"\nAfter /auth/github/login: {final_url[:100]}")

        # Save screenshot of the GitHub auth page
        await page.screenshot(path="c:/Users/NK/Desktop/debug_github_auth.png", full_page=False)

        await browser.close()


asyncio.run(main())
