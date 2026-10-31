"""Dashboard browser checks; all API writes are intercepted."""
import json
import pathlib
import sys
import threading
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server, WSGIRequestHandler
class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass
from playwright.sync_api import sync_playwright
from admin.app import app

server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=QuietHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors, writes = [], []
        fail = [False]
        page.on("pageerror", lambda e: errors.append(str(e)))
        def handle(route):
            request = route.request
            if not request.url.startswith(base):
                route.abort()
                return
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                writes.append({"url": request.url, "data": request.post_data_json})
                route.fulfill(status=401 if fail[0] else 200,
                    json={"ok": not fail[0], "error": "test denied"} if fail[0] else {"ok": True, "settings": {}})
            elif "/api/sync/" in request.url or "/api/admin-settings" in request.url or "/api/public/admin-settings" in request.url:
                route.fulfill(json={"ok": True, "settings": {}})
            else:
                route.continue_()
        page.route("**/*", handle)
        page.goto(base + "/dashboard", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        for tab in page.locator(".dash-tab[data-tab]").all():
            name = tab.get_attribute("data-tab")
            tab.click()
            assert page.locator("#panel-" + name).is_visible(), name
            print("PASS tab", name)
        page.locator('.dash-tab[data-tab="boxes"]').click()
        page.wait_for_timeout(400)
        page.evaluate("createBoxOnCanvas({key:'test-box',title:'Test box',x:40,y:40,w:300,h:200,type:'content'})")
        rows=page.locator('#layersList .layer-row')
        assert rows.count() > 0
        assert not errors, errors
        page.locator('#boxesSearch').fill('no-matching-box-123')
        assert page.locator('#layersList .layer-row:visible').count() == 0
        page.locator('#boxesSearch').fill('')
        rows.first.click()
        assert page.locator('#layersList .layer-row.selected').count() == 1
        assert page.locator('.inspector-category').is_visible()
        width=page.locator('#inspTabContent input[data-prop="w"]')
        assert width.bounding_box()['width'] >= 80
        page.locator('.inspector-ratio input').check()
        selected=page.evaluate('previewSelectedKey')
        before=page.evaluate('previewBoxesData[previewSelectedKey].w / previewBoxesData[previewSelectedKey].h')
        width.fill('480');width.press('Tab')
        actual=page.evaluate('previewBoxesData[previewSelectedKey]')
        assert actual['w'] == 480
        assert abs(actual['h'] - 480/before) <=1
        assert not page.locator('#inspTabBar').count()
        page.locator('.inspector-category').select_option('style')
        assert page.locator('#inspTabContent input[data-prop="borderWidth"]').count()
        page.locator('.inspector-category').select_option('transform')
        page.screenshot(path='_inspector_improved.png',full_page=True)
        print('PASS inspector readable fields, ratio resize, category navigation')
        page.locator('#boxesFocus').click()
        assert 'boxes-focus' in page.locator('#panel-boxes').get_attribute('class')
        page.keyboard.press('Escape')
        assert 'boxes-focus' not in page.locator('#panel-boxes').get_attribute('class')
        if not page.locator('#panel-boxes').evaluate("el=>el.classList.contains('boxes-live')"):
            page.locator('#boxesLiveToggle').click()
        page.wait_for_timeout(400)
        assert page.locator('#panel-boxes').evaluate("el=>el.classList.contains('boxes-live')")
        assert page.locator('#previewIframe').evaluate("el=>getComputedStyle(el).visibility") == 'visible'
        page.locator('#boxesTemplatesToggle').click()
        assert page.locator('.boxes-template').count() == 3
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('.boxes-template').nth(1).click()
        assert page.evaluate("previewBoxesData['test-box'].w") == 1200
        page.evaluate("() => {for(const key of ['music-player','masthead','packages','blog-section','moon-widget'])if(!previewBoxesData[key])createBoxOnCanvas({key,title:key,x:150,y:70,w:250,h:180,type:'content'});previewBoxesData['packages'].rotation=25;previewBoxesData['packages'].marginL=50}")
        for template in range(3):
            page.locator('#boxesTemplatesToggle').click()
            page.once('dialog', lambda dialog: dialog.accept())
            page.locator('.boxes-template').nth(template).click()
            geometry=page.evaluate("Object.entries(previewBoxesData).filter(([,d])=>!d.hidden).map(([key,d])=>({key,...d}))")
            assert all(d.get('rotation') == 0 and d.get('marginL') == 0 for d in geometry)
            assert next(d for d in geometry if d['key']=='masthead')['y'] == 24
            for i,a in enumerate(geometry):
                assert a['x'] >=24 and a['x']+a['w']<=1224
                for b in geometry[i+1:]:
                    assert a['x']+a['w']<=b['x'] or b['x']+b['w']<=a['x'] or a['y']+a['h']<=b['y'] or b['y']+b['h']<=a['y'], (a['key'],b['key'])
        page.wait_for_timeout(300)
        measured=page.evaluate("() => {const doc=document.getElementById('previewIframe').contentDocument;return [...doc.querySelectorAll('[data-box]')].filter(el=>previewBoxesData[el.dataset.box]).map(el=>{const r=el.getBoundingClientRect(),d=previewBoxesData[el.dataset.box];return {key:el.dataset.box,expected:[d.x,d.y,d.w,d.h],actual:[r.x,r.y,r.width,r.height]}})}")
        assert measured
        for item in measured:
            assert all(abs(a-b)<2 for a,b in zip(item['expected'],item['actual'])), item
        assert page.evaluate("getComputedStyle(document.getElementById('previewIframe').contentDocument.getElementById('masthead')).display") == 'flex'
        page.screenshot(path='_boxes_live_verified.png',full_page=True)
        print('PASS iframe measured bounds and original header flex layout')
        print('PASS all templates: bounds, no overlap, stable header, reset offsets')
        page.locator('#boxesLiveToggle').click()
        print('PASS live page and starter layout')
        page.screenshot(path='_boxes_editor_desktop.png',full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        page.locator('.boxes-mobile-nav button[data-pane="layers"]').click()
        assert page.locator('#layersPanel').is_visible()
        assert not page.locator('#canvasWrap').is_visible()
        page.locator('.boxes-mobile-nav button[data-pane="inspector"]').click()
        assert page.locator('#inspectorPanel').is_visible()
        page.locator('.boxes-mobile-nav button[data-pane="canvas"]').click()
        assert page.locator('#canvasWrap').is_visible()
        page.screenshot(path='_boxes_editor_mobile.png',full_page=True)
        page.set_viewport_size({"width":1440,"height":1000})
        page.locator('.dash-tab[data-tab="sizes"]').click()
        print('PASS Boxes search, selection, focus and mobile panes')
        # Clicking the external checklist must leave the selected panel active.
        page.locator('a.dash-tab').evaluate("el => el.addEventListener('click', e => e.preventDefault())")
        page.locator('a.dash-tab').click()
        assert page.locator("#panel-sizes").is_visible()
        for function in ["persistNavLinks", "persistPlaylist", "saveRainAudioUrls"]:
            before = len(writes)
            page.evaluate("async name => await window[name]()", function)
            requests = [r for r in writes[before:] if "/api/admin-settings-merge" in r["url"]]
            assert requests, function
            assert requests[0]["data"]["slug"] == "demo"
            assert "patch" in requests[0]["data"]
            print("PASS save", function)
        result = page.evaluate("async () => {blogPosts = [{id:1,title:'one'}, {id:3,title:'three',hidden:true}]; document.getElementById('postTitle').value='new'; await savePost(); const ids=blogPosts.map(p=>p.id); editPost(3); document.getElementById('postTitle').value='edited'; await savePost(); return {ids,hidden:blogPosts.find(p=>p.id===3).hidden}}")
        assert result == {"ids": [1,3,4], "hidden": True}, result
        print("PASS blog IDs remain unique and editing preserves hidden state")
        page.locator('#blogRichEditor').fill('Browser editor text')
        assert page.locator('#postContent').input_value() == 'Browser editor text'
        page.locator('#blogHtml').click()
        assert page.locator('#postContent').is_visible()
        page.locator('#postContent').fill('<h2>HTML test</h2><p>Body</p>')
        page.locator('#blogHtml').click()
        assert page.locator('#blogRichEditor h2').inner_text() == 'HTML test'
        page.locator('#blogPreviewToggle').click()
        assert page.locator('.blog-preview').is_visible()
        assert page.locator('.blog-preview').get_attribute('sandbox') == ''
        page.locator('#blogPreviewToggle').click()
        page.wait_for_timeout(600)
        assert page.evaluate("!!localStorage.getItem('owen_blog_editor_draft_v1')")
        print('PASS visual editor, HTML, sandboxed preview, draft')
        fail[0] = True
        rejected = page.evaluate("async () => {try {await saveDashboardPatch('demo', {theme:'pink'});return false} catch(e) {return e.message === 'test denied'}}")
        assert rejected
        await_result = page.evaluate("async () => {await savePost();return document.getElementById('postContent').value}")
        assert await_result == '<h2>HTML test</h2><p>Body</p>'
        assert 'L\u01b0u th\u1ea5t b\u1ea1i' in page.locator('.blog-editor-status').inner_text()
        print("PASS rejected save retains content")
        fail[0] = False
        for function in ["saveGeneral", "saveFonts", "saveAllBoxSizes"]:
            page.evaluate("async name => await window[name]()", function)
            print("PASS action", function)
        page.wait_for_timeout(500)
        assert not errors, errors
        print("PASS no browser JavaScript errors")
        page.locator('.dash-tab[data-tab="blog"]').click()
        page.screenshot(path='_blog_editor_desktop.png', full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator('#blogRichEditor').is_visible()
        assert page.evaluate("document.getElementById('panel-blog').getBoundingClientRect().width <= innerWidth")
        page.screenshot(path='_blog_editor_mobile.png', full_page=True)
        print("PASS responsive blog editor")
        browser.close()
finally:
    server.shutdown()
