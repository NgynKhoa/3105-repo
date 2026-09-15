"""Test Dashboard Music panel: badge type + auto-detect URL input."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await ctx.new_page()

        logs = []
        errors = []
        page.on('console', lambda msg: logs.append(f'[{msg.type}] {msg.text}'))
        page.on('pageerror', lambda e: errors.append(str(e)))

        print('=== Test 2: Dashboard Music panel ===')
        # Mock authenticated: visit /dashboard. Will redirect to login. Skip auth for test.
        # Use admin mode with localStorage prefill.
        await page.goto('http://127.0.0.1:5050/dashboard', wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(2000)

        # Check if dashboard rendered or login required
        on_login = await page.evaluate('location.pathname.includes("/auth") || document.querySelector("form[action*=github]") ? true : false')
        print(f'  on login page? {on_login}')

        if on_login:
            print('  ⚠ Skipping dashboard test — requires auth. Re-test manually.')
            await browser.close()
            return

        # Inject test playlist with 3 types
        await page.evaluate('''
            // Override playlist directly via localStorage then reload
            const pl = [
              { id: 1, title: 'Demo MP3',  artist: 'Local',         src: 'https://example.com/file.mp3',     cover: '' },
              { id: 2, title: 'YT Song',   artist: 'YouTuber',      src: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', cover: '' },
              { id: 3, title: 'Spotify',   artist: 'Spotify Band',  src: 'https://open.spotify.com/track/0e7ipj03S05BNilyuZbArc', cover: '' },
            ];
            localStorage.setItem('admin_playlist', JSON.stringify(pl));
        ''')
        await page.reload(wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)

        # Click Music tab
        try:
            await page.click('button.dash-tab[data-tab="music"]', timeout=2000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f'  Music tab not clickable: {e}')

        # Test auto-detect via onTrackUrlInput
        url_input = await page.query_selector('#trackUrlInput')
        if url_input:
            await url_input.fill('https://www.youtube.com/watch?v=abc123XYZ45')
            await page.wait_for_timeout(500)
            hint = await page.text_content('#trackUrlHint') or ''
            print(f'  Hint after YT paste: {hint!r}')
            cover = await page.evaluate('document.getElementById("trackCoverInput").value')
            print(f'  Cover auto-filled: {bool(cover)} ({cover[:80]!r})')

            await url_input.fill('https://open.spotify.com/track/abc123')
            await page.wait_for_timeout(500)
            hint = await page.text_content('#trackUrlHint') or ''
            print(f'  Hint after Spotify paste: {hint!r}')

            await url_input.fill('https://example.com/test.mp3')
            await page.wait_for_timeout(500)
            hint = await page.text_content('#trackUrlHint') or ''
            print(f'  Hint after MP3 paste: {hint!r}')

        # Take screenshot
        await page.screenshot(path='test_dash_music.png', full_page=True)

        await browser.close()

asyncio.run(main())
