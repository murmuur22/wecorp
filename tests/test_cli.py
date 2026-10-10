from pathlib import Path
import subprocess
import sys
import json
import pytest
import we
from test_core import site

CODE = Path(__file__).parents[1]


def invoke(root, *args):
    return subprocess.run([sys.executable, str(CODE / 'we.py'), '--root', str(root), *args], capture_output=True, text=True)


def test_cli_manages_member_post_and_renders_mirrored_navigation(site, tmp_path):
    assert (CODE / 'cli.py').exists(), 'Real CLI missing'
    added = invoke(site, 'member', 'add', 'guest', '--name', 'Guest', '--role', 'Writer')
    assert added.returncode == 0, added.stderr
    assert we.read_json(site / 'content/members/guest/member.json')['listed'] is False
    assert invoke(site, 'member', 'set', 'guest', '--listed', 'yes', '--contact', 'hello@example.test').returncode == 0
    assert we.read_json(site / 'content/members/guest/member.json')['listed'] is True
    assert invoke(site, 'post', 'new', 'guest', 'welcome', '--title', 'Welcome').returncode == 0
    assert invoke(site, 'post', 'set', 'guest', 'welcome', '--published', 'yes').returncode == 0
    result = invoke(site, 'show', 'gallery', '--member', 'murmuur')
    assert result.returncode == 0, result.stderr
    for word in ('Home', 'Portfolio', 'Gallery', 'Blog', 'Work', 'Contact', 'Help', 'Back'):
        assert f'[{word}]' in result.stdout
    assert invoke(site, 'member', 'add', '../bad', '--name', 'Bad', '--role', 'No').returncode != 0
    assert invoke(site, 'publish').returncode == 0
    assert invoke(site, 'status').returncode == 0


def test_shell_accepts_shared_shortcut_words(site):
    result = subprocess.run([sys.executable, str(CODE / 'we.py'), '--root', str(site), 'shell', '--member', 'murmuur'], input='g\n?\nquit\n', capture_output=True, text=True)
    assert 'Field of view.' in result.stdout, 'Terminal shortcut g does not mirror website Gallery'
    assert 'You already know how.' in result.stdout


def test_cli_can_change_homepage_and_portfolio_headlines(site):
    result = invoke(site, 'home', 'set', '--title', 'Our own front door', '--intro', 'Make room to live.')
    assert result.returncode == 0, 'Homepage headline cannot be managed from CLI'
    assert we.view_model(site, 'home')['title'] == 'Our own front door'
    result = invoke(site, 'member', 'set', 'murmuur', '--headline', 'A changed practice')
    assert result.returncode == 0
    assert we.view_model(site, 'portfolio', 'murmuur')['title'] == 'A changed practice'


def test_browser_and_terminal_chrome_are_strictly_grayscale(site):
    import re
    from cli import console, render_screen, TERMINAL
    we.create_entry(site, 'murmuur', 'posts', 'code', 'Code')
    path = we.entry_path(site, 'murmuur', 'posts', 'code')
    meta, _ = we.read_entry(path)
    we.write_entry(path, {**meta, 'published': True}, '```python\nprint("hello")\n```')
    c = console()
    render_screen(c, site, 'post', 'murmuur', 'code')
    combined = (CODE / 'static/site.css').read_text() + c.export_html(theme=TERMINAL, inline_styles=True)
    for color in re.findall(r'#[0-9a-fA-F]{6}', combined):
        assert color[1:3].lower() == color[3:5].lower() == color[5:7].lower(), color


def test_interactive_shell_navigation(site):
    assert (CODE / 'cli.py').exists(), 'Interactive CLI missing'
    result = subprocess.run([sys.executable, str(CODE / 'we.py'), '--root', str(site), 'shell', '--member', 'murmuur'], input='gallery\nhelp\nquit\n', capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'Field of view.' in result.stdout
    assert 'You already know how.' in result.stdout
