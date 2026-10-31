"""Same-document blog navigation using the actual application TrackPlayer instances."""
import os,sys,pathlib,threading,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server,WSGIRequestHandler
from playwright.sync_api import sync_playwright
from admin.app import app
class Quiet(WSGIRequestHandler):
    def log(self,*args,**kwargs):pass
youtube=os.environ.get('TEST_YOUTUBE_BLOG')=='1'
public=os.environ.get('TEST_PUBLIC_BLOG')=='1'
original=None
if public:
    original=pathlib.Path('public/blog.html').read_bytes()
    subprocess.run([sys.executable,'tools/build_public.py'],check=True,stdout=subprocess.DEVNULL)
    from flask import Flask,send_from_directory
    app=Flask('blog-static-test');root=pathlib.Path('public').resolve()
    @app.route('/3105-repo/')
    def home():return send_from_directory(root,'index.html')
    @app.route('/3105-repo/<path:name>')
    def asset(name):return send_from_directory(root,name)
server=make_server('127.0.0.1',0,app,threaded=True,request_handler=Quiet)
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}';base=origin+('/3105-repo' if public else '')
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        page=browser.new_page(viewport={'width':1400,'height':900});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route(r):
            if not r.request.url.startswith(origin):
                r.continue_() if youtube else r.abort()
            elif r.request.method not in ['GET','HEAD'] or '/api/sync/' in r.request.url:r.fulfill(json={'ok':True})
            elif '/api/public/' in r.request.url:r.fulfill(json={'ok':True,'settings':{}})
            else:r.continue_()
        page.route('**/*',route)
        page.goto(base+'/',wait_until='domcontentloaded')
        page.wait_for_function('!!window.__blogNavigation && !!window.__mpTrackPlayer && !!window.__rainLightPlayer')
        page.wait_for_timeout(1000)
        # Actual app players + actual repo audio, not a synthetic Audio element.
        page.evaluate("""async src=>{
          window.__originalMusic=window.__mpTrackPlayer;window.__originalRain=window.__rainLightPlayer;
          window.__documentMarker={};
          window.rainEnabled=true;window.heavyRain=false;
          localStorage.setItem('repo_rainAudioLight',src);
          await __mpTrackPlayer.load({src,title:'Continuity test'});
          await __rainLightPlayer.load({src,title:'Rain test'});
          __mpTrackPlayer.audio.loop=true;__rainLightPlayer.audio.loop=true;
          await __mpTrackPlayer.audio.play();await __rainLightPlayer.audio.play();
        }""",base+'/assets/rain.mp3')
        if youtube:
            page.evaluate("() => {window.__adminPlaylist=[{src:'https://www.youtube.com/watch?v=dpxfxxhZ-uQ',title:'YouTube continuity'}];window.__mpRefresh();document.getElementById('mpPlay').click()}")
            page.wait_for_function("__mpTrackPlayer._ytReady && typeof __mpTrackPlayer.ytPlayer?.getPlayerState==='function'",timeout=25000)
            page.evaluate('__mpTrackPlayer.play()')
            page.wait_for_function("__mpTrackPlayer.ytPlayer && typeof __mpTrackPlayer.ytPlayer.getPlayerState==='function' && __mpTrackPlayer.ytPlayer.getPlayerState()===1 && __mpTrackPlayer.ytPlayer.getCurrentTime()>0",timeout=25000)
        page.evaluate("window.__musicClock=()=>__mpTrackPlayer.currentType==='youtube'?__mpTrackPlayer.ytPlayer.getCurrentTime():__mpTrackPlayer.audio.currentTime;window.__musicPaused=()=>__mpTrackPlayer.currentType==='youtube'?[0,2,5,-1].includes(__mpTrackPlayer.ytPlayer.getPlayerState()):__mpTrackPlayer.audio.paused")
        page.wait_for_timeout(400)
        before=page.evaluate('[__musicClock(),__rainLightPlayer.audio.currentTime]')
        if youtube:page.evaluate('window.__originalVideoFrame=__mpTrackPlayer.ytPlayer.getIframe()')
        page.locator('a.settings-nav-link[href*="blog"]').evaluate('a=>a.click()')
        page.locator('#blog-reader .reader-card').first.wait_for()
        page.locator('#blog-reader .reader-card').first.click()
        page.locator('#blog-reader article h1').wait_for()
        page.wait_for_timeout(400)
        actual=page.evaluate("({same:__originalMusic===__mpTrackPlayer&&__originalRain===__rainLightPlayer,paused:[__musicPaused(),__rainLightPlayer.audio.paused],time:[__musicClock(),__rainLightPlayer.audio.currentTime],marker:!!__documentMarker})")
        if youtube:
            page.wait_for_function("__mpTrackPlayer.ytPlayer.getPlayerState()===1",timeout=15000)
            print('YouTube navigation: same player, advancing clock, playback active')
        assert actual['same'] and actual['marker'] and actual['paused']==[False,False],actual
        assert all(a>b for a,b in zip(actual['time'],before)),(before,actual)
        assert page.locator('#blog-reader iframe').count()==0
        if youtube:assert page.evaluate('__originalVideoFrame===__mpTrackPlayer.ytPlayer.getIframe()')
        page.screenshot(path='_single_page_blog.png')
        page.evaluate('history.back()')
        page.locator('#blog-reader .reader-card').first.wait_for()
        page.evaluate('history.back()')
        page.wait_for_function("document.getElementById('blog-reader').hidden")
        assert page.evaluate('!__musicPaused() && !__rainLightPlayer.audio.paused')
        assert not errors,errors
        print('PASS actual app music + rain players keep advancing; list, detail, Back; no new iframe')
        browser.close()
finally:
    server.shutdown()
    if original is not None:pathlib.Path('public/blog.html').write_bytes(original)
