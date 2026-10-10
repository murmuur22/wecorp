from pathlib import Path
import functools
import http.server
import threading
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright
import explorer as ex
from test_explorer import source


@pytest.fixture(scope='module')
def explorer_browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def explorer_web(source, tmp_path):
    frames = source/'@murmuur/photography/images'; frames.mkdir()
    for color in ('orange','blue'):
        Image.new('RGB',(800,500),color).save(frames/(color+'.png'))
    (source/'@murmuur/photography/frames.md').write_text('# Frames\n\n![Orange frame](images/orange.png)\n\n![Blue frame](images/blue.png)\n\n[About](../../about.md#about)\n')
    ex.publish_directory(source, tmp_path/'state')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*_): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(tmp_path/'state/current')))
    thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    yield source, f'http://127.0.0.1:{server.server_port}'
    server.shutdown(); server.server_close(); thread.join()


def test_keyboard_assignments_arrows_up_command_typing_and_disable(explorer_browser, explorer_web):
    source, url = explorer_web
    page = explorer_browser.new_page()
    errors=[]; page.on('pageerror', lambda e:errors.append(str(e)))
    page.goto(url+'/@murmuur/')
    model = ex.Catalog(source).model('/@murmuur/')
    key = next(e['key'] for e in model['entries'] if e['label']=='photography/')
    page.keyboard.press(key); page.wait_for_url('**/@murmuur/photography/')
    page.keyboard.press('ArrowDown')
    assert page.locator('.selected').count()==1
    assert page.locator('.selected').evaluate('(e)=>e===document.activeElement')
    page.keyboard.press('Enter'); page.wait_for_url('**/@murmuur/photography/frames/')
    page.keyboard.press('u'); page.wait_for_url('**/@murmuur/')
    page.keyboard.press('/')
    page.keyboard.type('cd photography')
    assert page.url.endswith('/@murmuur/')
    page.keyboard.press('Enter'); page.wait_for_url('**/@murmuur/photography/')
    page.keyboard.press('r')
    assert page.locator('.raw').is_visible()
    assert '# Photography' in page.locator('.raw').inner_text()
    page.keyboard.press('k')
    page.keyboard.press('h')
    assert page.url.endswith('/photography/')
    page.locator('[data-action=keys]').click()
    page.keyboard.press('h'); page.wait_for_url(url+'/')
    assert not errors
    page.close()


def test_image_viewer_arrows_escape_and_focus_return(explorer_browser, explorer_web):
    source,url = explorer_web
    page = explorer_browser.new_page()
    page.goto(url+'/@murmuur/photography/frames/')
    page.locator('[data-image="0"]').click()
    assert page.locator('#viewer').is_visible()
    assert page.locator('#viewer-image').get_attribute('alt')=='Orange frame'
    page.keyboard.press('ArrowRight')
    assert page.locator('#viewer-image').get_attribute('alt')=='Blue frame'
    page.locator('#viewer-image').evaluate('(e)=>e.decode()')
    page.keyboard.press('ArrowLeft')
    assert page.locator('#viewer-image').get_attribute('alt')=='Orange frame'
    page.keyboard.press('Escape')
    assert not page.locator('#viewer').is_visible()
    assert page.locator('[data-image="0"]').evaluate('(e)=>e===document.activeElement')
    page.close()


@pytest.mark.parametrize('width',[320,390,1140])
def test_chrome_document_and_linked_images_fit_all_widths(explorer_browser, explorer_web, width):
    source,url = explorer_web
    page = explorer_browser.new_page(viewport={'width':width,'height':900})
    for route in ('/','/@murmuur/','/@murmuur/photography/','/@murmuur/photography/frames/','/about/'):
        assert page.goto(url+route).status==200
        assert page.locator('#header-bar').is_visible()
        assert page.locator('#directory-bar').is_visible()
        assert page.locator('#document').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (width,route)
        for image in page.locator('.markdown img').all():
            image.scroll_into_view_if_needed(); image.evaluate('(e)=>e.decode()')
    page.close()


def test_dynamic_large_directory_can_be_navigated_without_letter_keys(explorer_browser, source, tmp_path):
    for n in range(50): (source/f'alpha-{n:02}.md').write_text(f'# Alpha {n}\n')
    state=tmp_path/'large-state'; ex.publish_directory(source,state)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*_): pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(state/'current')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    page=explorer_browser.new_page()
    try:
        page.goto(f'http://127.0.0.1:{server.server_port}/')
        model=ex.Catalog(source).model('/')
        target_index=next(i for i,e in enumerate(model['entries']) if not e['key'])
        for _ in range(target_index+1): page.keyboard.press('ArrowDown')
        target=model['entries'][target_index]
        page.keyboard.press('Enter');page.wait_for_url('**'+target['url'])
    finally:
        page.close();server.shutdown();server.server_close();thread.join()


def test_relative_links_unlisted_pages_and_private_source_are_correct(explorer_browser, explorer_web):
    source,url=explorer_web
    page=explorer_browser.new_page()
    page.goto(url+'/@murmuur/photography/frames/')
    assert page.locator('.markdown a').get_attribute('href')=='/about/#about'
    page.locator('.markdown a').click();page.wait_for_url('**/about/#about')
    page.goto(url+'/')
    assert page.locator('#directory-bar').get_by_text('@murmuur/').count()==0
    for path in ('/.head/navigation.json','/draft/','/@murmuur/photography/images/orange.png','/explorer.py'):
        assert page.request.get(url+path).status==404
    page.close()


def test_long_filenames_wrap_without_breaking_small_screen_navigation(explorer_browser, explorer_web, tmp_path):
    source,url=explorer_web
    name='a-very-long-photography-collection-with-a-name-that-should-not-break-the-navigation-bar.md'
    (source/name).write_text('# A long filename\n')
    # The fixture server serves its current symlink, so publish a new complete release.
    ex.publish_directory(source, source.parent/'state')
    page=explorer_browser.new_page(viewport={'width':320,'height':900})
    try:
        page.goto(url+'/')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'A filename pushes the navigation outside the viewport'
        entry=page.locator('.entry-token').filter(has_text=name)
        assert entry.is_visible()
    finally:page.close()


def test_no_javascript_documents_and_links_work(explorer_browser, explorer_web):
    source,url=explorer_web
    context=explorer_browser.new_context(java_script_enabled=False)
    page=context.new_page();page.goto(url+'/@murmuur/photography/frames/')
    page.locator('.markdown a').click()
    assert page.url.endswith('/about/#about')
    context.close()
