from pathlib import Path
from contextlib import contextmanager
import http.server
import functools
import threading
import pytest
from playwright.sync_api import sync_playwright
import we
from PIL import Image


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def web(tmp_path):
    we.initialize(tmp_path)
    we.add_member(tmp_path, 'murmuur', 'murmuur', 'Photographer')
    we.add_member(tmp_path, 'guest', 'Guest', 'Writer', listed=True)
    for n, color in enumerate(('orange', 'blue')):
        source = tmp_path / f'{n}.png'
        Image.new('RGB', (700, 450), color).save(source)
        photo = we.import_photo(tmp_path, 'murmuur', source, f'Frame {n}', f'{color} test frame')
        we.set_photo(tmp_path, 'murmuur', photo['id'], published=True)
    we.create_entry(tmp_path, 'murmuur', 'posts', 'first', 'First note')
    we.set_entry(tmp_path, 'murmuur', 'posts', 'first', published=True)
    we.create_entry(tmp_path, 'murmuur', 'projects', 'first', 'First project')
    we.set_entry(tmp_path, 'murmuur', 'projects', 'first', published=True)
    we.publish(tmp_path)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(tmp_path / 'current')))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    yield tmp_path, f'http://127.0.0.1:{server.server_port}'
    server.shutdown(); server.server_close(); thread.join()


def test_real_keyboard_navigation_command_line_and_photo_arrows(browser, web):
    root, url = web
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(url + '/@murmuur/')
    page.keyboard.press('g'); page.wait_for_url('**/gallery/')
    page.keyboard.press('/')
    assert page.locator('#command').evaluate('(e)=>e === document.activeElement')
    page.keyboard.type('blog')
    assert page.url.endswith('/gallery/') # shortcut must not fire while typing
    page.keyboard.press('Enter'); page.wait_for_url('**/blog/')
    page.locator('.entry').first.click(); page.wait_for_url('**/blog/first/')
    page.keyboard.press('Escape'); page.wait_for_url('**/blog/')
    page.locator('[data-command=gallery]').click()
    page.locator('.photo-card').first.click()
    page.wait_for_load_state('load') # Deferred keyboard listeners belong to the new document.
    first_url = page.url
    page.keyboard.press('ArrowRight')
    page.wait_for_function('(old)=>location.href !== old', arg=first_url)
    page.wait_for_load_state('load')
    page.keyboard.press('ArrowLeft'); page.wait_for_url(first_url)
    page.keyboard.press('Escape'); page.wait_for_url('**/gallery/')
    page.keyboard.press('?'); page.wait_for_url('**/help/')
    page.locator('#command').fill('photo set murmuur malicious --published yes')
    page.locator('#command-form button').click()
    assert 'Editing happens' in page.locator('#command-feedback').inner_text()
    assert not errors
    page.close()


@pytest.mark.parametrize('width', [320, 390, 1440])
def test_all_public_views_have_no_horizontal_overflow_and_images_load(browser, web, width):
    root, url = web
    photo = we.gallery(root, 'murmuur')[0]
    page = browser.new_page(viewport={'width': width, 'height': 900})
    for path in ('/', '/about/', '/members/', '/help/', '/@murmuur/', '/@murmuur/gallery/', '/@murmuur/gallery/' + photo['id'] + '/', '/@murmuur/blog/', '/@murmuur/blog/first/', '/@murmuur/work/', '/@murmuur/work/first/', '/@murmuur/contact/', '/@murmuur/help/'):
        response = page.goto(url + path)
        assert response.status == 200
        assert page.locator('h1').count() >= 1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path)
        for image in page.locator('img').all():
            image.scroll_into_view_if_needed()
            image.evaluate('(img)=>img.decode()')
            assert image.evaluate('(img)=>img.naturalWidth > 0')
    page.close()


def test_unlisted_member_is_accessible_but_not_in_directory_and_source_is_private(browser, web):
    root, url = web
    page = browser.new_page()
    page.goto(url + '/members/')
    assert page.locator('a[href="/@murmuur/"]').count() == 0
    assert page.locator('a[href="/@guest/"]').count() == 1
    page.goto(url + '/')
    page.locator('#handle').fill('murmuur')
    page.locator('.member-jump button').click()
    page.wait_for_url('**/@murmuur/')
    for path in ('/content/site.json', '/originals/', '/we.py', '/admin', '/@murmuur/blog/private-working-note/'):
        response = page.request.get(url + path)
        assert response.status == 404
    page.close()


def test_basic_site_without_javascript(browser, web):
    root, url = web
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(url + '/@murmuur/')
    page.locator('[data-command=gallery]').click()
    assert page.url.endswith('/gallery/')
    page.locator('.photo-card').first.click()
    assert page.locator('.single-photo img').is_visible()
    context.close()
