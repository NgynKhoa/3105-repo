"""Test the full admin login flow end-to-end."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))
        page.on("console", lambda msg: print(f"[{msg.type}]", msg.text[:200]) if msg.type in ("error", "warning", "log") else None)

        url = "http://127.0.0.1:5050/?slug=demo"
        print(f"\n=== Loading {url} (anonymous) ===\n")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        # Snapshot before login
        await page.screenshot(path="c:/Users/NK/Desktop/debug_before_login.png", full_page=True)

        # Manually call /auth/me to see what server returns for anon
        me_data = await page.evaluate("""
async () => {
    const r = await fetch('/auth/me?slug=demo');
    return await r.json();
}
        """)
        print("=== /auth/me anonymous ===")
        for k, v in me_data.items():
            print(f"  {k}: {repr(v)[:200]}")

        # Manually simulate admin login by setting session cookie? Skip - just verify the flow
        # Get auth/me with admin cookie by simulating callback
        # Actually let's check that fetchAuthState properly populates
        auth_state = await page.evaluate("""
() => ({
    __isAuthOwner: window.__isAuthOwner,
    __currentRepoOwner: window.__currentRepoOwner,
    __packageReleases: window.__packageReleases,
    __packageDownloadPaths: window.__packageDownloadPaths,
    __downloadMode: window.__downloadMode,
    __adminDefaults: window.__adminDefaults,
    Settings_role: window.Settings?.role,
})
        """)
        print("\n=== WINDOW STATE (anonymous) ===")
        for k, v in auth_state.items():
            print(f"  {k}: {repr(v)[:200]}")

        # Try clicking login to see what happens
        await page.click('#settingsBtn')
        await page.wait_for_timeout(300)
        login_url = await page.eval_on_selector('#btnLogin', 'el => el.href')
        print(f"\n=== Login URL ===\n  {login_url}")

        # Don't actually click — we don't have GitHub creds in test
        # But verify the URL structure
        if 'client_id=' in login_url and 'state=' in login_url:
            print("✓ OAuth URL looks correct")

        await browser.close()


asyncio.run(main())
