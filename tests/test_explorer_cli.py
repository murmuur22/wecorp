from pathlib import Path
import subprocess
import sys
import pytest
import explorer as ex
from test_explorer import source

CODE = Path(__file__).parents[1]


def command(source, state, *args, env=None):
    return subprocess.run([sys.executable, str(CODE/'explorer.py'), '--source', str(source), '--state', str(state), *args], capture_output=True, text=True, env=env)


def test_cli_renders_the_same_header_and_ls_rows_and_edits_plain_markdown(source, tmp_path):
    assert hasattr(ex, 'render_terminal'), 'Mirrored directory terminal missing'
    state = tmp_path / 'state'
    result = command(source, state, 'show', '/@murmuur/')
    assert result.returncode == 0, result.stderr
    model = ex.Catalog(source).model('/@murmuur/')
    assert 'WE CORP / DOCUMENT TERMINAL' in result.stdout
    assert 'ls /@murmuur/' in result.stdout
    assert 'cat @murmuur/index.md' in result.stdout
    assert '# murmuur' in result.stdout # terminal defaults to the actual source Markdown
    for item in model['entries']:
        assert ex.button_text(item) in result.stdout
    result = command(source, state, 'new', '@murmuur/writing/first.md', '--title', 'First note')
    assert result.returncode == 0, result.stderr
    assert (source/'@murmuur/writing/first.md').read_text().startswith('# First note')
    result = command(source, state, 'head', '@murmuur', '--depth', '2')
    assert result.returncode == 0
    assert ex.Catalog(source).model('/@murmuur/')['submenu_depth'] == 2
    assert command(source, state, 'publish').returncode == 0
    assert command(source, state, 'status').returncode == 0


def test_terminal_selection_highlights_the_whole_directory_item(source):
    from explorer_terminal import tokens
    from cli import console, TERMINAL
    model=ex.Catalog(source).model('/@murmuur/')
    c=console()
    tokens(c, model['entries'], selected=1)
    captured=c.export_html(theme=TERMINAL, inline_styles=True)
    import re
    assert re.search(r'<span style="[^"]*background-color:[^"]*">[^<]*photography/', captured), 'Selected filename is not highlighted'


def test_cli_rejects_a_selected_source_symlink(source,tmp_path):
    link=tmp_path/'public-link'
    link.symlink_to(source,target_is_directory=True)
    result=command(link,tmp_path/'state','validate')
    assert result.returncode != 0, 'CLI silently resolved an excluded source symlink'
    assert 'symlink' in result.stdout or 'real public directory' in result.stdout


def test_cli_interactive_directory_navigation(source, tmp_path):
    assert hasattr(ex, 'render_terminal'), 'Mirrored directory terminal missing'
    result = subprocess.run([sys.executable, str(CODE/'explorer.py'), '--source', str(source), '--state', str(tmp_path/'state'), 'shell', '/@murmuur/'], input='cd photography\ncd ..\nopen index.md\nquit\n', capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'ls /@murmuur/photography/' in result.stdout
    assert 'href=' not in result.stdout # navigation displays source, not generated HTML
