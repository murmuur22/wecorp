"""Actual terminal renderer and operator commands for the directory prototype."""
from pathlib import Path
import argparse
import os
import sys
import shlex
import subprocess
import json
from rich.text import Text
from rich.markdown import Markdown
from cli import console, TERMINAL, CODE_THEME
import explorer as ex
import sitegen


def row(c, left, right='', right_style='#999999'):
    text = Text(left + ' ' * max(1, c.width - len(left) - len(right)))
    text.append(right, style=right_style)
    c.print(text)


def tokens(c, items, selected=-1):
    line = Text()
    for i, item in enumerate(items):
        key = 'Esc' if item['key'] == 'escape' else item['key'] or '·'
        start = len(line)
        line.append('[')
        line.append(key, style='#0a0a0a on #eeeeee')
        line.append(' ' + item['label'] + ']')
        if i == selected:
            line.stylize('#0a0a0a on #eeeeee', start, len(line))
        line.append(' ')
    c.print(line)


def render_terminal(catalog, path, c=None, raw=True, selected=-1):
    c = c or console()
    model = catalog.model(path)
    row(c, model['brand'] + ' / DOCUMENT TERMINAL', 'DEMO / LOCAL')
    c.rule(style='#666666')
    c.print(Text('wecorp.network' + model['url']))
    tokens(c, model['controls'] + model['pins'])
    c.rule(style='#666666')
    c.print(Text('ls /' + (model['directory'] + '/' if model['directory'] != '.' else '')))
    tokens(c, model['entries'], selected)
    c.rule(style='#666666')
    row(c, 'cat ' + model['source'], 'RAW MARKDOWN' if raw else 'RENDERED')
    c.print()
    if raw:
        c.print(Text(model['body'].rstrip()))
    else:
        c.print(Markdown(model['body'], code_theme=CODE_THEME))
    c.rule(style='#666666')
    prompt = Text('we:' + model['url'] + ' › ')
    prompt.append('/ command · arrows select · Enter opens', style='#777777')
    c.print(prompt)
    c.print()
    c.rule(style='#666666')
    row(c, 'WE CORP / ' + sitegen.version() + ' / FILES, NOT FEEDS.', 'REFERENCE CONTENT / NOT A FINISHED PORTFOLIO', right_style='')
    return model


def source_target(source, relative, exists=False):
    if not relative or relative.startswith('/') or any(x.startswith('.') for x in Path(relative).parts):
        raise ValueError('Use a source-relative path outside hidden/config directories')
    source = Path(source).resolve()
    target = source / relative
    if not target.resolve().is_relative_to(source):
        raise ValueError('Path escapes public source')
    for ancestor in [target, *target.parents]:
        if ancestor == source: break
        if ancestor.is_symlink(): raise ValueError('Symlinks are not allowed')
    if exists and not target.is_file(): raise ValueError('No file at ' + relative)
    return target


def resolve_command(catalog, current, value):
    if value in catalog.routes:
        return value
    base = catalog.model(current)['directory']
    ref = catalog.resolve_reference(value, base)
    path = ref['url'].split('#', 1)[0]
    if path not in catalog.routes:
        raise ValueError('Use a Markdown page or directory')
    return path


def read_key(model, c):
    if not sys.stdin.isatty():
        return c.input('we:' + model['url'] + ' › ').strip()
    import termios
    import tty
    import select
    fd = sys.stdin.fileno(); saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd, termios.TCSANOW)
        c.print(Text('single key / opens command entry / q quits', style='grey70'))
        key = os.read(fd, 1).decode(errors='replace')
        if key in ('\x03', '\x04'): raise EOFError
        if key == '\x1b':
            rest = b''
            while select.select([fd], [], [], .04)[0]: rest += os.read(fd, 1)
            return {'[A':'@previous', '[B':'@next', '[C':'@next', '[D':'@previous'}.get(rest.decode(), 'back')
        if key in ('\r', '\n'): return '@enter'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    if key == '/': return c.input('we:' + model['url'] + ' › ').strip()
    return key.lower()


def help_text(c):
    c.print(Text('KEYBOARD / SAME WORDS IN BOTH INTERFACES', style='bold white'))
    c.print(Text('Displayed keys open items. Arrows select; Enter opens. h Home / u Up / Escape Back.'))
    c.print(Text('r Raw/rendered / k Keys / ? Help / / Command entry. q exits the terminal.'))
    c.print(Text('ls | cd <folder> | open <document.md> | cd .. | home'))
    c.print(Text('Operator commands: edit <page> | new <page> --title ... | head <directory>'))
    c.print(Text('validate | publish | rollback <release> | status. Browser commands only navigate.'))


def interactive(source, state, start, c):
    current, history, raw, enabled, selected = start, [], True, True, -1
    while True:
        try:
            catalog = ex.Catalog(source)
            if sys.stdout.isatty():
                c.clear()
            model = render_terminal(catalog, current, c, raw, selected)
            line = read_key(model, c)
            if not line: continue
            if line in ('quit', 'exit', 'q'): return
            aliases = {x['key']: x for x in model['controls'] + model['pins'] + model['entries'] if x.get('key')}
            if enabled and line in aliases:
                item = aliases[line]
                line = item.get('action') or 'open-url ' + item['url']
            if line == 'keys': enabled = not enabled; continue
            if line in ('help', '?'): help_text(c); continue
            if line == 'raw': raw = not raw; continue
            if line == 'ls': continue
            if line in ('@next', '@previous'):
                if model['entries']:
                    selected = (selected + (1 if line == '@next' else -1)) % len(model['entries'])
                continue
            if line == '@enter':
                if selected < 0: continue
                line = 'open-url ' + model['entries'][selected]['url']
            destination = None
            if line == 'home': destination = '/'
            elif line in ('up', 'cd ..'): destination = model['up']
            elif line == 'back':
                current = history.pop() if history else model['up']; selected = -1; continue
            elif line.startswith('open-url '): destination = line[9:]
            elif line.startswith(('cd ', 'open ', 'cat ')):
                parts = shlex.split(line)
                if len(parts) != 2: raise ValueError('Quote paths containing spaces')
                destination = resolve_command(catalog, current, parts[1])
            else:
                args = parser().parse_args(['--source', str(source), '--state', str(state), *shlex.split(line)])
                execute(args, c); continue
            if destination != current:
                if destination not in catalog.routes: raise ValueError('No public document at ' + destination)
                history.append(current); current = destination; selected = -1
        except (EOFError, KeyboardInterrupt):
            return
        except SystemExit:
            c.print(Text('Invalid command. Type help.'))
        except (ValueError, OSError) as error:
            c.print(Text('ERROR / ' + str(error), style='bold white'))


def parser():
    p = argparse.ArgumentParser(description='WE / directory-first static publisher and mirrored terminal')
    p.add_argument('--source', type=Path, default=ex.DEFAULT_SOURCE)
    p.add_argument('--state', type=Path, default=ex.DEFAULT_STATE)
    p.add_argument('--export', type=Path, help='Export actual recorded CLI output as HTML')
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('show'); s.add_argument('path', nargs='?', default='/'); s.add_argument('--rendered', action='store_true')
    s = sub.add_parser('shell'); s.add_argument('path', nargs='?', default='/')
    sub.add_parser('validate'); sub.add_parser('publish'); sub.add_parser('status')
    s = sub.add_parser('rollback'); s.add_argument('release')
    s = sub.add_parser('preview'); s.add_argument('--port', type=int, default=8768)
    s = sub.add_parser('new'); s.add_argument('path'); s.add_argument('--title', required=True)
    s = sub.add_parser('edit'); s.add_argument('path')
    s = sub.add_parser('photo-import'); s.add_argument('file', type=Path); s.add_argument('destination')
    s = sub.add_parser('head'); s.add_argument('directory'); s.add_argument('--depth', type=int); s.add_argument('--listed', choices=['yes','no']); s.add_argument('--pin', nargs=2, action='append', metavar=('LABEL','PATH')); s.add_argument('--brand')
    s = sub.add_parser('import-tree'); s.add_argument('input', type=Path); s.add_argument('destination', type=Path); s.add_argument('--apply', action='store_true')
    return p


def execute(args, c):
    if args.source.is_symlink():
        raise ValueError('Source must be an explicit real public directory')
    source, state = args.source.resolve(), args.state.resolve()
    if args.command == 'show':
        catalog = ex.Catalog(source)
        path = args.path if args.path in catalog.routes else resolve_command(catalog, '/', args.path)
        render_terminal(catalog, path, c, not args.rendered); return
    if args.command == 'shell': interactive(source, state, args.path, c); return
    c.print(Text('WE CORP / DOCUMENT TERMINAL', style='bold white'))
    c.rule(style='#666666')
    c.print(Text('OPERATION / ' + args.command.upper()))
    if args.command == 'validate':
        catalog, models = ex.inspect_directory(source)
        c.print(Text(f'{len(models)} public pages / {len(catalog.assets)} referenced assets / {len(catalog.excluded)} excluded drafts'))
        c.print(Text('Valid relative links. Nothing published.'))
    elif args.command == 'publish':
        release = ex.publish_directory(source, state)
        c.print(Text('Published local release: ' + release))
        c.print(Text('Only generated pages and referenced supported assets. Source/originals/config are not served.'))
    elif args.command == 'rollback':
        ex.rollback_directory(state, args.release)
        c.print(Text('Restored public output: ' + args.release))
        c.print(Text('Source Markdown is unchanged.'))
    elif args.command == 'status':
        c.print(Text('Current: ' + ((state/'current').resolve().name if (state/'current').is_symlink() else 'not published')))
        if (state/'releases').exists():
            for path in sorted((state/'releases').iterdir()):
                if not path.name.startswith('.'): c.print(Text(path.name))
    elif args.command == 'new':
        path = source_target(source, args.path)
        if path.suffix != '.md': raise ValueError('New documents must be Markdown')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as f: f.write('# ' + args.title + '\n\nWrite here.\n')
        c.print(Text('Created ' + args.path + '. Edit with your preferred editor.'))
    elif args.command == 'edit':
        path = source_target(source, args.path, exists=True)
        if path.suffix != '.md': raise ValueError('edit accepts Markdown documents')
        editor = shlex.split(os.environ.get('EDITOR', 'nano'))
        if not editor: raise ValueError('EDITOR is empty')
        subprocess.run(editor + [str(path)], check=True)
        ex.document(path)
        c.print(Text('Saved source document. Publish when ready.'))
    elif args.command == 'photo-import':
        from PIL import Image
        import shutil
        path = source_target(source, args.destination)
        if path.exists(): raise ValueError('Photo destination exists; no overwrite')
        with Image.open(args.file) as img: img.verify()
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.file, path)
        c.print(Text('Original copied into source: ' + args.destination))
        c.print(Text('Reference it in Markdown with descriptive alt text. Unlinked files are not published.'))
    elif args.command == 'head':
        import we
        directory = source if args.directory in ('.','/') else source_target(source, args.directory)
        if not directory.is_dir(): raise ValueError('Header directory does not exist')
        target = directory/'.head/navigation.json'
        if target.is_symlink() or target.parent.is_symlink(): raise ValueError('Unsafe header path')
        data = json.loads(target.read_text()) if target.exists() else {}
        if args.depth is not None:
            if not 0 <= args.depth <= 3: raise ValueError('Submenu depth must be 0–3')
            data['submenu_depth'] = args.depth
        if args.listed is not None: data['listed'] = args.listed == 'yes'
        if args.pin is not None: data['pins'] = [{'label': label, 'path': path} for label,path in args.pin]
        if args.brand is not None: data['brand'] = args.brand
        we.write_json(target, data)
        c.print(Text('Header config saved: ' + str(target.relative_to(source))))
    elif args.command == 'import-tree':
        plan = ex.import_directory(args.input, args.destination, apply=args.apply)
        c.print(Text('APPLIED / new directory only' if args.apply else 'DRY RUN / no destination created'))
        for relative in plan['copy']: c.print(Text('  + ' + relative))
        c.print(Text(f'{plan["pages"]} Markdown pages / {plan["referenced_assets"]} assets / {len(plan["excluded_drafts"])} excluded drafts'))
    elif args.command == 'preview':
        import http.server
        import functools
        if not (state/'current').is_symlink(): raise ValueError('Publish first')
        if not 1024 <= args.port <= 65535: raise ValueError('Preview port must be 1024–65535')
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(state/'current'))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler)
        c.print(Text(f'http://127.0.0.1:{args.port}/ / loopback only'))
        try: server.serve_forever()
        finally: server.server_close()
    c.rule(style='#666666')
    c.print(Text('LOCAL ONLY / no remote deployment or source deletion'))


def main(argv=None):
    args = parser().parse_args(argv)
    c = console()
    code = 0
    try:
        execute(args, c)
    except KeyboardInterrupt:
        code = 130
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        c.print(Text('ERROR / ' + str(error), style='bold white')); code = 1
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(c.export_html(theme=TERMINAL, inline_styles=True))
    return code
