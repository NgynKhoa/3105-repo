"""Test multi-source music player: MP3 + YouTube + Spotify + SoundCloud."""
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

        print('=== Test 1: Multi-source playlist on Front ===')
        # Inject playlist with 3 sources
        await page.add_init_script('''
            window.PUBLIC_PLAYLIST = [
              { id: 1, title: 'Test MP3', artist: 'Local', src: 'https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav', cover: '' },
              { id: 2, title: 'NCS Music (YouTube)', artist: 'YouTube test', src: 'https://www.youtube.com/watch?v=jNQXAC15IVL', cover: '' },
              { id: 3, title: 'Spotify example', artist: 'Spotify test', src: 'https://open.spotify.com/track/0e7ipj03S05BNilyuZbArc', cover: '' },
              { id: 4, title: 'No source', artist: 'Empty', src: '', cover: '' },
            ];
        ''')

        await page.goto('http://127.0.0.1:5050/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(5000)

        # Verify MultiPlayer loaded
        has_mp = await page.evaluate('typeof window.MultiPlayer')
        has_tp = await page.evaluate('typeof window.MultiPlayer?.TrackPlayer')
        has_ytapi_loaded = await page.evaluate('!!document.querySelector("script[src*=\\"youtube.com/iframe_api\\"]")')
        print(f'  MultiPlayer namespace: {has_mp}, TrackPlayer: {has_tp}, YT API script injected: {has_ytapi_loaded}')

        # Verify parser
        cases = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'youtube'),
            ('https://youtu.be/dQw4w9WgXcQ', 'youtube'),
            ('https://open.spotify.com/track/0e7ipj03S05BNilyuZbArc', 'spotify'),
            ('https://soundcloud.com/foo/bar', 'soundcloud'),
            ('https://example.com/song.mp3', 'mp3'),
            ('', 'mp3'),
        ]
        for url, expected in cases:
            result = await page.evaluate(f'window.MultiPlayer.parseTrackUrl({url!r})')
            ok = result['type'] == expected
            print(f'  parseTrackUrl({url[:50]!r}) → type={result["type"]} {"✓" if ok else "❌ expected " + expected}')

        # Check first track loaded
        title = await page.text_content('#mpTitle')
        print(f'  Initial #mpTitle: {title!r}')

        # Take screenshot of Now Playing area
        await page.screenshot(path='test_multi_mp3.png', full_page=False, clip={'x': 1100, 'y': 200, 'width': 280, 'height': 380})

        # Click next 3 times → test YT and Spotify detection
        for i in range(3):
            try:
                await page.click('#mpNext', timeout=1500)
                await page.wait_for_timeout(1000)
                title = await page.text_content('#mpTitle')
                print(f'  After click Next #{i+1}: {title!r}')
            except Exception as e:
                print(f'  Next #{i+1} failed: {e}')

        # Errors?
        real_errors = [e for e in errors if 'favicon' not in e.lower()]
        if real_errors:
            print(f'\n⚠ Page errors: {len(real_errors)}')
            for e in real_errors[:5]:
                print(f'  {e[:150]}')
        else:
            print('\n✅ No JS errors')

        await browser.close()

asyncio.run(main())
