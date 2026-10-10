"""The real terminal interface. Website navigation uses the same view model."""
import argparse
import http.server
import shlex
import subprocess
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from rich.theme import Theme
from rich.terminal_theme import TerminalTheme
from rich.syntax import PygmentsSyntaxTheme
from pygments.style import Style as PygmentsStyle
from pygments.token import Token

class MonochromeCode(PygmentsStyle):
    background_color = '#151515'
    styles = {Token: '#eeeeee', Token.Comment: '#999999', Token.Keyword: 'bold #eeeeee', Token.String: '#bbbbbb'}

CODE_THEME = PygmentsSyntaxTheme(MonochromeCode)
import we
from sitegen import members, entries

THEME = Theme({"markdown.h1": "bold white", "markdown.h2": "bold white", "markdown.link": "underline white", "markdown.link_url": "grey70", "markdown.code": "white", "markdown.block_quote": "grey70", "repr.str": "white", "repr.number": "white", "repr.bool_true": "white", "repr.bool_false": "grey70"})
TERMINAL = TerminalTheme((10, 10, 10), (238, 238, 238), [(0, 0, 0)] + [(170, 170, 170)] * 7, [(110, 110, 110)] + [(238, 238, 238)] * 7)


def console():
    return Console(record=True, width=104, theme=THEME, highlight=False)


def header(c, path="/", nav=None, demo=False):
    top = Table.grid(expand=True)
    top.add_column(ratio=2)
    top.add_column(justify="right")
    top.add_row(Text("WE CORP", style="bold white"), Text("LOCAL / OPERATOR TERMINAL", style="grey70"))
    top.add_row(Text("NETWORK / TERMINAL 01", style="grey70"), Text("FILES, NOT FEEDS.", style="grey70"))
    c.print(top)
    c.rule(style="grey70")
    c.print(Text("wecorp.network" + path, style="white"))
    if nav:
        text = Text()
        for n in nav:
            text.append("[")
            text.append(n["label"][0], style="black on white")
            text.append(n["label"][1:] + "]  ", style="underline" if n["active"] else "white")
        c.print(text)
    c.rule(style="grey50")
    if demo:
        c.print(Text("DEMONSTRATION / sample copy and reference images, not Robbie's finished portfolio", style="grey70"))
        c.print()


def table(c, columns, rows):
    t = Table(show_edge=False, box=None, padding=(0, 2, 1, 0), header_style="bold white")
    for label in columns:
        t.add_column(label, overflow="fold")
    for row in rows:
        t.add_row(*[Text(str(x)) for x in row])
    c.print(t)


def ascii_photo(root, photo, width=60):
    from PIL import Image
    with Image.open(Path(root) / photo["variants"][-1]["file"]) as image:
        image = image.convert("L")
        image.thumbnail((width, max(8, int(width * image.height / image.width * .42))))
        shades = " .:-=+*#%@"
        return '\n'.join(''.join(shades[min(9, value * 10 // 256)] for value in [image.getpixel((x, y)) for x in range(image.width)]) for y in range(image.height))


def render_screen(c, root, view, handle=None, item=None):
    model = we.view_model(root, view, handle, item)
    header(c, model["path"], model["nav"], model["site"].get("demo", False))
    c.print(Text("01 / " + (("@" + handle + " / ") if handle else "") + view.upper(), style="grey70"))
    c.print()
    c.print(Text(model["title"], style="bold white"))
    c.print(Text(model["subtitle"], style="grey70"))
    c.print()
    if view in ("home", "about", "portfolio", "post", "project"):
        c.print(Markdown(model["body"], code_theme=CODE_THEME))
    if view in ("portfolio", "gallery"):
        c.rule("02 / SELECTED FRAMES", style="grey50")
        photos = model["photos"][:3] if view == "portfolio" else model["photos"]
        table(c, ["FRAME", "TITLE", "SIZE", "OPEN"], [(f'{i:02d}', x["title"], f'{x["width"]} × {x["height"]}', f'open {x["id"]}') for i, x in enumerate(photos, 1)])
        c.print(Text("Color photographs live in the browser. Terminal previews use luminance.", style="grey70"))
    if view in ("blog", "work"):
        values = model["posts"] if view == "blog" else model["projects"]
        table(c, ["DATE", "TITLE", "OPEN"], [(x.get("date", ""), x["title"], f'open {x["slug"]}') for x in values])
    if view == "photo":
        c.print(Text(ascii_photo(root, model["item"])))
        c.print(Text(model["item"].get("caption") or model["item"]["alt"]))
        c.print(Text('MARKDOWN / ![' + model['item']['alt'] + '](/' + model['item']['variants'][-1]['file'] + ')', style='grey70'))
        c.print(Text("original retained privately / public derivatives have camera metadata removed", style="grey70"))
    if view == "contact":
        c.print(Text(model["member"].get("contact") or "No public contact address set."))
        c.print(Text(f'wecorp.network / wecorp.network/@{handle}'))
    if view == "members":
        table(c, ["HANDLE", "ROLE"], [("@" + x["handle"], x["role"]) for x in model["members"] if x["listed"]])
        c.print(Text("Unlisted pages are public by address, not password protected.", style="grey70"))
    if view == "help":
        table(c, ["KEY", "WORD", "COMMAND"], [(x["key"], x["label"], x["command"]) for x in model["nav"]])
        c.print(Text("NAVIGATE: home | member <handle> | gallery | blog | work | contact | help | open <id>"))
        c.print(Text("MANAGE: member | post | project | photo | home edit | validate | publish | rollback"))
        c.print(Text("Use help <command> for flags. $EDITOR opens your preferred editor. quit exits."))
    c.rule(style="grey50")
    c.print(Text(f"we{':@' + handle if handle else ''} ›", style="white"))
    c.print(Text(f"WE CORP / {we.version()}                                     FILES, NOT FEEDS.", style="grey70"))
    return model


def parser():
    p = argparse.ArgumentParser(description="WE CORP — static site and mirrored operator terminal")
    p.add_argument('--root', type=Path, default=Path(__file__).parent / 'workspace')
    p.add_argument('--export', type=Path, help='Export actual recorded terminal output as HTML')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('status')
    sub.add_parser('validate')
    sub.add_parser('publish')
    r = sub.add_parser('rollback'); r.add_argument('release')
    s = sub.add_parser('show'); s.add_argument('view', choices=['home', 'about', 'members', 'portfolio', 'gallery', 'blog', 'work', 'contact', 'help', 'photo', 'post', 'project']); s.add_argument('--member'); s.add_argument('--item')
    s = sub.add_parser('shell'); s.add_argument('--member')
    s = sub.add_parser('preview'); s.add_argument('--port', type=int, default=8767)
    m = sub.add_parser('member'); ms = m.add_subparsers(dest='action', required=True)
    ms.add_parser('list')
    a = ms.add_parser('add'); a.add_argument('handle'); a.add_argument('--name', required=True); a.add_argument('--role', required=True); a.add_argument('--listed', choices=['yes', 'no'], default='no')
    a = ms.add_parser('set'); a.add_argument('handle'); a.add_argument('--name'); a.add_argument('--role'); a.add_argument('--headline'); a.add_argument('--listed', choices=['yes', 'no']); a.add_argument('--contact')
    a = ms.add_parser('edit'); a.add_argument('handle')
    for command in ('post', 'project'):
        m = sub.add_parser(command); ms = m.add_subparsers(dest='action', required=True)
        a = ms.add_parser('list'); a.add_argument('handle')
        a = ms.add_parser('new'); a.add_argument('handle'); a.add_argument('slug'); a.add_argument('--title', required=True)
        a = ms.add_parser('import'); a.add_argument('handle'); a.add_argument('slug'); a.add_argument('file', type=Path); a.add_argument('--title', required=True)
        a = ms.add_parser('edit'); a.add_argument('handle'); a.add_argument('slug')
        a = ms.add_parser('set'); a.add_argument('handle'); a.add_argument('slug'); a.add_argument('--title'); a.add_argument('--summary'); a.add_argument('--published', choices=['yes', 'no'])
    m = sub.add_parser('photo'); ms = m.add_subparsers(dest='action', required=True)
    a = ms.add_parser('list'); a.add_argument('handle')
    a = ms.add_parser('import'); a.add_argument('handle'); a.add_argument('files', type=Path, nargs='+'); a.add_argument('--title', required=True); a.add_argument('--alt', required=True)
    a = ms.add_parser('set'); a.add_argument('handle'); a.add_argument('id'); a.add_argument('--title'); a.add_argument('--alt'); a.add_argument('--caption'); a.add_argument('--published', choices=['yes', 'no'])
    a = ms.add_parser('reorder'); a.add_argument('handle'); a.add_argument('ids', nargs='+')
    m = sub.add_parser('home'); ms = m.add_subparsers(dest='action', required=True); ms.add_parser('edit'); a = ms.add_parser('import'); a.add_argument('file', type=Path)
    a = ms.add_parser('set'); a.add_argument('--title'); a.add_argument('--intro'); a.add_argument('--tagline')
    return p


def edit(path):
    editor = shlex.split(os.environ.get('EDITOR', 'nano'))
    if not editor:
        raise ValueError('EDITOR is empty')
    subprocess.run(editor + [str(path)], check=True)


def show_management(c, root, kind, handle):
    if kind == 'member':
        table(c, ['HANDLE', 'NAME', 'ROLE', 'DIRECTORY'], [(x['handle'], x['name'], x['role'], 'listed' if x['listed'] else 'unlisted') for x in members(root)])
    elif kind == 'photo':
        table(c, ['ORDER', 'ID', 'TITLE', 'STATUS', 'WEB SIZES'], [(i, x['id'], x['title'], 'published' if x['published'] else 'draft', ', '.join(str(v['width']) for v in x['variants'])) for i, x in enumerate(we.gallery(root, handle), 1)])
    else:
        table(c, ['DATE', 'SLUG', 'TITLE', 'STATUS'], [(x.get('date', ''), x['slug'], x['title'], 'published' if x['published'] else 'draft') for x in entries(root, handle, 'posts' if kind == 'post' else 'projects', published=False)])


def execute(args, c):
    root = args.root.resolve()
    command = args.command
    if command == 'init':
        we.initialize(root); header(c); c.print(Text('Initialized portable workspace. No demo records added.'))
        return
    if command == 'show':
        render_screen(c, root, args.view, args.member, args.item); return
    if command == 'shell':
        interactive(root, c, args.member); return
    if command == 'preview':
        if not 1024 <= args.port <= 65535:
            raise ValueError('Preview port must be 1024–65535')
        if not (root / 'current').is_symlink():
            raise ValueError('Run publish before preview')
        import functools
        # Only the current public release is served; never source or originals.
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root / 'current'))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler)
        c.print(Text(f'Preview: http://127.0.0.1:{args.port} / loopback only / Ctrl-C stops'))
        try:
            server.serve_forever()
        finally:
            server.server_close()
        return
    header(c, f'/@{args.handle}/' if hasattr(args, 'handle') else '/operator/')
    c.print(Text('OPERATION / ' + command.upper() + (' ' + args.action.upper() if hasattr(args, 'action') else ''), style='bold white'))
    c.print()
    if command == 'member':
        if args.action == 'add':
            we.add_member(root, args.handle, args.name, args.role, listed=args.listed == 'yes')
            c.print(Text(f'Created public member address /@{args.handle}/; default unlisted.'))
        elif args.action == 'set':
            path = we.member_dir(root, args.handle) / 'member.json'; data = we.read_json(path)
            for key in ('name', 'role', 'headline', 'contact', 'listed'):
                value = getattr(args, key)
                if value is not None:
                    data[key] = value == 'yes' if key == 'listed' else value
            we.write_json(path, data); c.print(Text('Member metadata saved. Publish to update the public site.'))
        elif args.action == 'edit':
            edit(we.member_dir(root, args.handle) / 'bio.md')
        show_management(c, root, 'member', None)
    elif command in ('post', 'project'):
        kind = 'posts' if command == 'post' else 'projects'
        if args.action in ('new', 'import'):
            if args.action == 'import':
                # Read before creating anything so a missing source leaves no draft.
                body = args.file.read_text()
            path = we.create_entry(root, args.handle, kind, args.slug, args.title)
            if args.action == 'import':
                meta, _ = we.read_entry(path); we.write_entry(path, meta, body)
            c.print(Text(f'Draft saved: {path.relative_to(root)}'))
        elif args.action == 'edit':
            path = we.entry_path(root, args.handle, kind, args.slug); edit(path); we.read_entry(path)
        elif args.action == 'set':
            updates = {k: getattr(args, k) for k in ('title', 'summary', 'published') if getattr(args, k) is not None}
            if 'published' in updates:
                updates['published'] = updates['published'] == 'yes'
            we.set_entry(root, args.handle, kind, args.slug, **updates)
            c.print(Text('Entry metadata saved. Drafts never enter a public build.'))
        show_management(c, root, command, args.handle)
    elif command == 'photo':
        if args.action == 'import':
            for source in args.files:
                item = we.import_photo(root, args.handle, source, args.title if len(args.files) == 1 else source.stem, args.alt)
                c.print(Text(f'Imported {source.name} → {item["id"]} / {item["width"]} × {item["height"]}'))
                c.print(Text('Original preserved / EXIF removed / orientation corrected / responsive WebP / DRAFT', style='grey70'))
                table(c, ['DERIVATIVE', 'DIMENSIONS', 'BYTES'], [(Path(x['file']).name, f'{x["width"]} × {x["height"]}', x['bytes']) for x in item['variants']])
        elif args.action == 'set':
            updates = {k: getattr(args, k) for k in ('title', 'alt', 'caption', 'published') if getattr(args, k) is not None}
            if 'published' in updates: updates['published'] = updates['published'] == 'yes'
            we.set_photo(root, args.handle, args.id, **updates)
            c.print(Text('Photograph metadata saved. Publish to update the public site.'))
        elif args.action == 'reorder':
            we.reorder_photos(root, args.handle, args.ids)
            c.print(Text('Gallery order saved; all IDs retained exactly once.'))
        show_management(c, root, 'photo', args.handle)
    elif command == 'home':
        if args.action == 'edit': edit(root / 'content/home.md')
        elif args.action == 'set':
            path = root / 'content/site.json'; data = we.read_json(path)
            data.update({k: getattr(args, k) for k in ('title', 'intro', 'tagline') if getattr(args, k) is not None})
            we.write_json(path, data)
        else: (root / 'content/home.md').write_text(args.file.read_text())
        c.print(Text('Homepage content saved. Publish when ready.'))
    elif command == 'validate':
        counts = we.validate(root)
        table(c, ['CONTENT', 'VALIDATED'], counts.items())
        c.print(Text('Content valid. No publication performed.'))
    elif command == 'publish':
        release = we.publish(root)
        c.print(Text(f'Published local release: {release}'))
        c.print(Text('current → releases/' + release))
        c.print(Text('Static files only. Original media, drafts and source content excluded.'))
        c.print(Text('No remote server contacted. No DNS or VPS deployment performed.', style='grey70'))
    elif command == 'rollback':
        we.rollback(root, args.release)
        c.print(Text('Restored public release: ' + args.release))
        c.print(Text('Source content unchanged; this rolls back public output, not your working files.'))
    elif command == 'status':
        counts = we.validate(root)
        current = root / 'current'
        c.print(Text('Current: ' + (current.resolve().name if current.is_symlink() else 'not published')))
        table(c, ['CONTENT', 'COUNT'], counts.items())
        table(c, ['RETAINED RELEASE'], [(p.name,) for p in sorted((root / 'releases').iterdir()) if p.is_dir() and not p.name.startswith('.')])
    c.rule(style='grey50')
    c.print(Text('Changes are local until a separately configured deployment exists.', style='grey70'))


def read_terminal_command(c, root, view, handle, item):
    prompt = f"we{':@' + handle if handle else ''} › "
    if not sys.stdin.isatty():
        return c.input(prompt).strip()
    import termios
    import tty
    import select
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd, termios.TCSANOW)
        c.print(Text(prompt + '(single key / type a command with / / q quits)', style='grey70'))
        key = os.read(fd, 1).decode(errors='replace')
        if key == '\x03': raise KeyboardInterrupt
        if key == '\x04': raise EOFError
        if key == '\x1b':
            sequence = b''
            while select.select([fd], [], [], .04)[0]:
                sequence += os.read(fd, 1)
            if sequence in (b'[C', b'[D') and view == 'photo':
                model = we.view_model(root, view, handle, item)
                target = model.get('next' if sequence == b'[C' else 'previous')
                return 'open ' + target if target else ''
            return 'back' if not sequence else ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    if key == '/':
        return c.input(prompt).strip()
    if key in ('q', '?'):
        return key
    keys = {n['key'] for n in we.view_model(root, view, handle, item)['nav']}
    return key.lower() if key.lower() in keys else ''


def interactive(root, c, handle=None):
    view, item = ('portfolio' if handle else 'home'), None
    while True:
        render_screen(c, root, view, handle, item)
        try:
            line = read_terminal_command(c, root, view, handle, item)
        except (EOFError, KeyboardInterrupt):
            c.print(); break
        if not line:
            continue
        try:
            parts = shlex.split(line)
            command = parts[0].lower()
            if len(parts) == 1:
                aliases = {x['key']: x['command'] for x in we.view_model(root, view, handle, item)['nav']}
                command = aliases.get(command, command)
            if command in ('quit', 'exit', 'q'): break
            if command == 'member' and len(parts) == 2:
                we.member_dir(root, parts[1]); handle, view, item = parts[1], 'portfolio', None
            elif command == 'back':
                if view in ('photo', 'post', 'project'): view = {'photo': 'gallery', 'post': 'blog', 'project': 'work'}[view]
                elif view == 'portfolio': handle, view = None, 'home'
                else: view = 'portfolio' if handle else 'home'
                item = None
            elif command in ('home', 'about', 'members', 'portfolio', 'gallery', 'blog', 'work', 'contact', 'help') and len(parts) == 1:
                view, item = command, None
                if view in ('home', 'about', 'members'): handle = None
            elif command == 'open' and len(parts) == 2:
                view, item = ('photo' if view in ('gallery', 'photo') else 'project' if view in ('work', 'project') else 'post'), parts[1]
            elif command == 'help' and len(parts) > 1:
                try: parser().parse_args(['--root', str(root), *parts[1:], '--help'])
                except SystemExit: pass
            else:
                try:
                    args = parser().parse_args(['--root', str(root), *parts]); execute(args, c)
                except SystemExit:
                    c.print(Text('Invalid command. Type help.'))
            # Validate the destination before the next rendering cycle.
            we.view_model(root, view, handle, item)
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            c.print(Text('ERROR / ' + str(error), style='bold white'))
            view, item = ('portfolio' if handle else 'home'), None


def main(argv=None):
    args = parser().parse_args(argv)
    c = console()
    try:
        execute(args, c)
        returncode = 0
    except KeyboardInterrupt:
        c.print(Text('Stopped.')); returncode = 130
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        c.print(Text('ERROR / ' + str(error), style='bold white')); returncode = 1
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(c.export_html(theme=TERMINAL, inline_styles=True))
    return returncode
