"""Exercise real CLI workflows, capture browser/terminal output, and assemble evidence."""
from pathlib import Path
import subprocess
import sys
import json
import shutil
import tempfile
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
import we

CODE = Path(__file__).resolve().parent
OUT = CODE / 'artifacts'
SHOTS = OUT / 'screenshots'
BASE = 'http://127.0.0.1:8767'


def run_cli(root, name, *args, env=None):
    target = OUT / 'terminal' / (name + '.html')
    result = subprocess.run([sys.executable, str(CODE / 'we.py'), '--root', str(root), '--export', str(target), *args], capture_output=True, text=True, env=env)
    (OUT / 'terminal' / (name + '.txt')).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{args}: {result.stdout}\n{result.stderr}')
    return target


def sheet(name, title, items):
    cell_w, cell_h = 740, 625
    columns = 2
    rows = (len(items) + 1) // 2
    canvas = Image.new('RGB', (columns * cell_w + 60, rows * cell_h + 110), '#101010')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 20)
    small = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 14)
    draw.text((30, 22), title, font=font, fill='#eee')
    draw.text((30, 57), 'WE CORP / working local prototype / real browser + recorded CLI output', font=small, fill='#999')
    for i, (label, file) in enumerate(items):
        x = 30 + (i % columns) * cell_w
        y = 95 + (i // columns) * cell_h
        draw.text((x, y), label, font=small, fill='#ddd')
        with Image.open(file) as image:
            image = image.convert('RGB')
            # Preserve full-page evidence; fit within the contact-sheet panel.
            image.thumbnail((cell_w - 25, cell_h - 55), Image.Resampling.LANCZOS)
            canvas.paste(image, (x, y + 28))
        draw.rectangle((x, y + 28, x + cell_w - 25, y + cell_h - 25), outline='#444')
    target = OUT / (name + '.jpg')
    canvas.save(target, quality=94)
    return target


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    (OUT / 'terminal').mkdir(exist_ok=True)
    proof = Path(tempfile.mkdtemp(prefix='workflow-', dir=OUT))
    shutil.copytree(CODE / 'workspace/content', proof / 'content')
    shutil.copytree(CODE / 'workspace/originals', proof / 'originals')
    shutil.copytree(CODE / 'workspace/media', proof / 'media')
    (proof / 'releases').mkdir()
    terminal = {}
    def cli(name, *args, **kwargs):
        terminal[name] = run_cli(proof, name, *args, **kwargs)
    cli('cli-member-add', 'member', 'add', 'demo-guest', '--name', 'Demo Guest', '--role', 'Writer / demonstration member')
    cli('cli-member-set', 'member', 'set', 'demo-guest', '--listed', 'yes', '--contact', 'guest@example.test', '--headline', 'A page of my own.')
    cli('cli-home-set', 'home', 'set', '--title', 'Our own front door.', '--intro', 'Make room to live.')
    cli('cli-post-new', 'post', 'new', 'demo-guest', 'first-note', '--title', 'A small beginning')
    external = proof / 'external-note.md'
    external.write_text('## Written in my own editor\n\nA Markdown file can travel without an account.\n\n**This is demonstration content.**\n')
    cli('cli-markdown-import', 'post', 'import', 'demo-guest', 'from-my-editor', str(external), '--title', 'A file of my own')
    editor = proof / 'demo_editor.py'
    editor.write_text('from pathlib import Path\nimport sys\np=Path(sys.argv[1]); p.write_text(p.read_text()+"\\nSaved by the deterministic editor test.\\n")\nprint("Editor save verified:",p.name)\n')
    import os
    import shlex
    env = {**os.environ, 'EDITOR': shlex.join([sys.executable, str(editor)])}
    cli('cli-markdown-edit', 'post', 'edit', 'demo-guest', 'from-my-editor', env=env)
    assert 'Saved by the deterministic editor test.' in we.read_entry(proof / 'content/members/demo-guest/posts/from-my-editor.md')[1]
    cli('cli-post-publish', 'post', 'set', 'demo-guest', 'from-my-editor', '--published', 'yes', '--summary', 'Edited outside the browser, ready for publication.')
    cli('cli-member-bio-edit', 'member', 'edit', 'demo-guest', env=env)
    cli('cli-home-edit', 'home', 'edit', env=env)
    cli('cli-home-import', 'home', 'import', str(CODE / 'workspace/content/home.md'))
    sources = sorted((CODE / 'demo-inputs').glob('*.jpg'))[:2]
    cli('cli-photo-import', 'photo', 'import', 'demo-guest', *map(str, sources), '--title', 'Reference import', '--alt', 'Reference city photograph / demonstration')
    photos = we.gallery(proof, 'demo-guest')
    cli('cli-photo-caption', 'photo', 'set', 'demo-guest', photos[0]['id'], '--title', 'City / after hours', '--caption', 'A reference photograph, not original portfolio work.', '--alt', 'A reference view of buildings and city streets', '--published', 'yes')
    cli('cli-photo-reorder', 'photo', 'reorder', 'demo-guest', *[x['id'] for x in photos[::-1]])
    cli('cli-photo-hide', 'photo', 'set', 'demo-guest', photos[0]['id'], '--published', 'no')
    cli('cli-project-new', 'project', 'new', 'demo-guest', 'field-study', '--title', 'A field study')
    cli('cli-project-set', 'project', 'set', 'demo-guest', 'field-study', '--published', 'yes')
    cli('cli-validate', 'validate')
    cli('cli-publish', 'publish')
    first = (proof / 'current').resolve().name
    cli('cli-publish-second', 'publish')
    cli('cli-rollback', 'rollback', first)
    assert (proof / 'current').resolve().name == first
    cli('cli-status', 'status')
    for view in ('home', 'portfolio', 'gallery', 'blog', 'work', 'contact', 'help'):
        if view == 'home': cli('cli-home', 'show', view)
        else: cli('cli-' + view, 'show', view, '--member', 'murmuur')
    cli('cli-photo', 'show', 'photo', '--member', 'murmuur', '--item', we.gallery(proof, 'murmuur')[0]['id'])
    cli('cli-post', 'show', 'post', '--member', 'murmuur', '--item', 'a-network-of-our-own')
    screenshot_manifest = []
    photo_id = we.gallery(CODE / 'workspace', 'murmuur')[0]['id']
    pages = [
        ('web-home', '/'), ('web-about', '/about/'), ('web-members', '/members/'), ('web-portfolio', '/@murmuur/'),
        ('web-gallery', '/@murmuur/gallery/'), ('web-photo', f'/@murmuur/gallery/{photo_id}/'),
        ('web-blog', '/@murmuur/blog/'), ('web-post', '/@murmuur/blog/a-network-of-our-own/'),
        ('web-work', '/@murmuur/work/'), ('web-project', '/@murmuur/work/we-field-node/'),
        ('web-contact', '/@murmuur/contact/'), ('web-help', '/@murmuur/help/'),
    ]
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        page.on('pageerror', lambda e: errors.append(str(e)))
        for name, route in pages:
            response = page.goto(BASE + route)
            assert response.status == 200
            page.evaluate('async()=>{await Promise.all([...document.images].map(i=>i.decode())); await document.fonts.ready;}')
            destination = SHOTS / (name + '.png')
            page.screenshot(path=str(destination), full_page=True)
            screenshot_manifest.append({'name': name, 'path': str(destination.relative_to(CODE)), 'source': BASE + route, 'kind': 'real browser'})
        page.goto(BASE + '/@murmuur/gallery/')
        page.keyboard.press('/')
        page.locator('#command').fill('blog')
        page.screenshot(path=str(SHOTS / 'web-command.png'), full_page=True)
        page.locator('#command-form button').click(); page.wait_for_url('**/blog/')
        mobile = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
        for name, route in [('web-mobile-home', '/'), ('web-mobile-gallery', '/@murmuur/gallery/')]:
            mobile.goto(BASE + route)
            mobile.evaluate('async()=>await Promise.all([...document.images].map(i=>i.decode()))')
            mobile.screenshot(path=str(SHOTS / (name + '.png')), full_page=True)
        terminal_page = browser.new_page(viewport={'width': 1150, 'height': 850})
        for name, html in terminal.items():
            terminal_page.goto(html.as_uri())
            terminal_page.add_style_tag(content='body{margin:0;padding:30px;background:#0a0a0a;color:#eeeeee}pre{font:14px/1.65 Menlo,monospace;margin:0} code{font:inherit}')
            destination = SHOTS / (name + '.png')
            terminal_page.screenshot(path=str(destination), full_page=True)
            screenshot_manifest.append({'name': name, 'path': str(destination.relative_to(CODE)), 'source': str(html.relative_to(CODE)), 'kind': 'HTML render of actual recorded Rich CLI output, not a terminal-app screenshot'})
        browser.close()
    assert not errors, errors
    we.write_json(OUT / 'screenshots.json', screenshot_manifest)
    sheets = [
        sheet('01-front-door', '01 / THE FRONT DOOR', [('Landing page', SHOTS/'web-home.png'), ('Member portfolio', SHOTS/'web-portfolio.png'), ('About / actual boundaries', SHOTS/'web-about.png'), ('CLI / member portfolio', SHOTS/'cli-portfolio.png')]),
        sheet('02-photography', '02 / PHOTOGRAPHY', [('Gallery / color inside a grayscale shell', SHOTS/'web-gallery.png'), ('Frame detail / caption / next & previous', SHOTS/'web-photo.png'), ('CLI / import, resize & preserve originals', SHOTS/'cli-photo-import.png'), ('CLI / gallery order', SHOTS/'cli-photo-reorder.png')]),
        sheet('03-writing', '03 / WRITING & WORK', [('Blog index', SHOTS/'web-blog.png'), ('Markdown article', SHOTS/'web-post.png'), ('Project index', SHOTS/'web-work.png'), ('Project case study', SHOTS/'web-project.png')]),
        sheet('04-publishing', '04 / THE OPERATOR WORKFLOW', [('CLI / new member', SHOTS/'cli-member-add.png'), ('CLI / Markdown import', SHOTS/'cli-markdown-import.png'), ('CLI / local publication', SHOTS/'cli-publish.png'), ('CLI / rollback', SHOTS/'cli-rollback.png')]),
        sheet('05-navigation', '05 / PARTICIPATION & NAVIGATION', [('Help / shared vocabulary', SHOTS/'web-help.png'), ('Contact / business-card addresses', SHOTS/'web-contact.png'), ('Public directory / unlisted members omitted', SHOTS/'web-members.png'), ('CLI / same shortcuts & commands', SHOTS/'cli-help.png')]),
    ]
    we.write_json(OUT / 'workflow-result.json', {'commands_exercised': len(terminal), 'browser_pages_captured': len(pages), 'console_errors': errors, 'source_editor_saved': True, 'rollback_verified': True, 'proof_workspace': str(proof), 'contact_sheets': [str(x.relative_to(CODE)) for x in sheets]})
    print(json.dumps({'commands_exercised': len(terminal), 'browser_pages_captured': len(pages), 'console_errors': errors, 'proof_workspace': str(proof), 'contact_sheets': len(sheets)}, indent=2))


if __name__ == '__main__':
    main()
