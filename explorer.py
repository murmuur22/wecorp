"""Directory-first WE document explorer. Public output is static; no web write API."""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit, quote, unquote
from html.parser import HTMLParser
import html
import json
import os
import posixpath
import re
import string
import markdown
import bleach

CODE = Path(__file__).resolve().parent
DEFAULT_SOURCE = CODE / 'explorer-workspace/public'
DEFAULT_STATE = CODE / 'explorer-workspace/state'


def document(path):
    text = Path(path).read_text()
    meta = {}
    if text.startswith('---\n'):
        if '\n---\n' not in text[4:]:
            raise ValueError(f'Malformed frontmatter: {path}')
        raw, text = text[4:].split('\n---\n', 1)
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError('Optional frontmatter must be JSON; ordinary Markdown needs no frontmatter') from error
        if not isinstance(meta, dict):
            raise ValueError('Frontmatter must be an object')
        for key in ('published', 'listed'):
            if key in meta and not isinstance(meta[key], bool):
                raise ValueError(f'{key} must be true or false')
    return meta, text.lstrip('\n')


def route(relative):
    p = PurePosixPath(relative)
    if p.suffix == '.md':
        p = p.parent if p.name == 'index.md' else p.with_suffix('')
    value = str(p)
    return '/' if value in ('', '.') else '/' + quote(value, safe='/@-_.') + '/'


def assign_keys(items, used=None):
    used = set(used or ())
    for item in items:
        candidates = [c for c in item['label'].lower() if c in string.ascii_lowercase + string.digits]
        candidates += list(string.ascii_lowercase + string.digits)
        key = next((c for c in candidates if c not in used), '')
        item['key'] = key
        if key:
            used.add(key)
    return used


class Catalog:
    def __init__(self, source):
        source = Path(source)
        if source.is_symlink() or not source.is_dir():
            raise ValueError('Source must be an explicit real public directory')
        self.source = source.resolve()
        self.pages, self.excluded, self.configs, self.assets = {}, set(), {}, {}
        # Dotfolders are configuration/private, never automatically public files.
        for current, dirs, files in os.walk(self.source, followlinks=False):
            current = Path(current)
            for name in dirs + files:
                if (current / name).is_symlink():
                    raise ValueError('Symlinks are not allowed in a publishing source')
            dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
            config = current / '.head/navigation.json'
            if config.exists():
                if config.is_symlink() or config.parent.is_symlink():
                    raise ValueError('Unsafe navigation configuration')
                settings = json.loads(config.read_text())
                if not isinstance(settings, dict) or not set(settings).issubset({'brand', 'pins', 'submenu_depth', 'listed', 'published'}):
                    raise ValueError('Unknown navigation configuration fields')
                depth = settings.get('submenu_depth', 1)
                if not isinstance(depth, int) or isinstance(depth, bool) or not 0 <= depth <= 3:
                    raise ValueError('submenu_depth must be 0–3')
                for flag in ('listed', 'published'):
                    if flag in settings and not isinstance(settings[flag], bool):
                        raise ValueError(f'{flag} must be boolean')
                self.configs[str(current.relative_to(self.source))] = settings
            for name in sorted(files):
                if name.startswith('.') or not name.endswith('.md'):
                    continue
                p = current / name
                relative = p.relative_to(self.source).as_posix()
                if PurePosixPath(relative).parts[0].removesuffix('.md') in ('_ui', '_media', '_files'):
                    raise ValueError('Source uses a reserved output namespace: ' + relative)
                meta, body = document(p)
                if not meta.get('published', True) or not self.settings(str(p.parent.relative_to(self.source))).get('published', True):
                    self.excluded.add(relative)
                    continue
                self.pages[relative] = {'meta': meta, 'body': body, 'url': route(relative)}
        self.directories = {'.'}
        self.routes = {}
        for relative, page in self.pages.items():
            if page['url'] in self.routes:
                raise ValueError('URL collision: ' + page['url'])
            self.routes[page['url']] = relative
            parent = PurePosixPath(relative).parent
            self.directories.update(str(p) for p in [parent, *parent.parents])
        for directory in self.directories:
            url = route(directory)
            if url in self.routes:
                if self.routes[url] != str(PurePosixPath(directory) / 'index.md'):
                    raise ValueError('File/folder URL collision: ' + url)
            else:
                self.routes[url] = None

    def settings(self, directory):
        result = {'brand': 'WE CORP', 'pins': [], 'submenu_depth': 1, 'listed': True, 'published': True}
        p = PurePosixPath(directory)
        origin = '.'
        for parent in reversed([p, *p.parents]):
            key = str(parent)
            settings = self.configs.get(key, {})
            if 'pins' in settings:
                origin = key
            result.update(settings)
        result['pin_origin'] = origin
        return result

    def safe_path(self, relative):
        if relative.startswith('../') or relative == '..' or relative.startswith('/') or any(p.startswith('.') for p in PurePosixPath(relative).parts):
            raise ValueError('Reference escapes public root or points into private configuration: ' + relative)
        path = self.source / relative
        if not path.resolve().is_relative_to(self.source) or not path.exists():
            raise ValueError('Missing or unsafe reference: ' + relative)
        return path

    def resolve_reference(self, value, base):
        split = urlsplit(value)
        if split.scheme or split.netloc:
            if split.scheme not in ('https', 'http', 'mailto'):
                raise ValueError('Unsupported external link scheme')
            return {'url': value, 'external': True}
        if not split.path:
            return {'url': value, 'anchor': True}
        path = unquote(split.path)
        relative = posixpath.normpath(path.lstrip('/') if path.startswith('/') else posixpath.join(base, path))
        if relative in self.excluded:
            raise ValueError('Link points to an excluded/private draft: ' + relative)
        self.safe_path(relative)
        target = self.source / relative
        if target.is_dir():
            if relative not in self.directories:
                raise ValueError('Directory contains no public Markdown pages: ' + relative)
            return {'url': route(relative) + ('#' + split.fragment if split.fragment else ''), 'relative': relative}
        if target.suffix == '.md':
            if relative not in self.pages:
                raise ValueError('Link points to excluded/private Markdown: ' + relative)
            return {'url': route(relative) + ('?' + split.query if split.query else '') + ('#' + split.fragment if split.fragment else ''), 'relative': relative}
        asset = self.asset_reference(relative)
        if asset['kind'] == 'attachment' and split.fragment:
            return {**asset, 'url': asset['url'] + '#' + split.fragment}
        return asset

    def asset_reference(self, relative):
        if relative in self.assets:
            return self.assets[relative]
        import hashlib
        import we
        path = self.safe_path(relative)
        if path.stat().st_size > 80 * 1024 * 1024:
            raise ValueError('Attachment exceeds 80 MiB: ' + relative)
        suffix = path.suffix.lower()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if suffix in ('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'):
            cache = self.source.parent / '.we-photo-cache'
            we.initialize(cache)
            if not (cache / 'content/members/assets').exists():
                we.add_member(cache, 'assets', 'Asset cache', 'Generated derivatives')
            photo = next((x for x in we.gallery(cache, 'assets') if x['sha256'] == digest), None)
            if photo is None:
                photo = we.import_photo(cache, 'assets', path, path.stem, 'Referenced image')
            variants = [{**v, 'local': str(cache / v['file']), 'url': '/_media/' + photo['id'] + '/' + Path(v['file']).name} for v in photo['variants']]
            item = {'relative': relative, 'kind': 'image', 'id': photo['id'], 'url': variants[-1]['url'], 'variants': variants, 'width': photo['width'], 'height': photo['height']}
        elif suffix in ('.pdf', '.txt', '.csv', '.json', '.zip', '.mp3', '.mp4', '.webm', '.ogg'):
            item = {'relative': relative, 'kind': 'attachment', 'url': '/_files/' + digest[:20] + suffix, 'local': str(path), 'name': path.name}
        else:
            raise ValueError('Unsupported attachment type (HTML/SVG/scripts are not published): ' + relative)
        self.assets[relative] = item
        return item

    def listed(self, directory):
        local = self.configs.get(directory, {})
        if not local.get('listed', True):
            return False
        index = self.pages.get(str(PurePosixPath(directory) / 'index.md'))
        return index is None or index['meta'].get('listed', True)

    def directory_entries(self, directory, depth=0):
        entries = []
        for relative, page in self.pages.items():
            path = PurePosixPath(relative)
            if str(path.parent) == directory and page['meta'].get('listed', True):
                entries.append({'label': path.name, 'url': page['url'], 'path': relative, 'kind': 'file', 'children': []})
        for child in sorted(self.directories):
            if child == '.' or str(PurePosixPath(child).parent) != directory or not self.listed(child):
                continue
            entries.append({'label': PurePosixPath(child).name + '/', 'url': route(child), 'path': child, 'kind': 'directory', 'children': self.directory_entries(child, depth - 1) if depth > 0 else []})
        return sorted(entries, key=lambda x: x['label'])

    def model(self, url):
        if url not in self.routes:
            raise ValueError('Unknown public path: ' + url)
        relative = self.routes[url]
        directory = str(PurePosixPath(relative).parent) if relative else unquote(url).strip('/') or '.'
        settings = self.settings(directory)
        body = self.pages[relative]['body'] if relative else '# ' + (PurePosixPath(directory).name if directory != '.' else 'Public documents') + '\n\nChoose a document from the directory above.\n'
        metadata = self.pages[relative]['meta'] if relative else {}
        up = route(str(PurePosixPath(directory).parent)) if directory != '.' else '/'
        controls = [{'label': 'Home', 'key': 'h', 'url': '/', 'action': 'home'}, {'label': 'Up', 'key': 'u', 'url': up, 'action': 'up'}, {'label': 'Back', 'key': 'escape', 'url': up, 'action': 'back'}, {'label': 'Help', 'key': '?', 'url': '', 'action': 'help'}, {'label': 'Raw', 'key': 'r', 'url': '', 'action': 'raw'}, {'label': 'Keys', 'key': 'k', 'url': '', 'action': 'keys'}]
        used = {x['key'] for x in controls} | {'q'}
        pins = []
        for pin in settings['pins']:
            if not isinstance(pin, dict) or not isinstance(pin.get('label'), str) or not isinstance(pin.get('path'), str):
                raise ValueError('Pinned entries need label and path')
            target = self.resolve_reference(pin['path'], settings['pin_origin'])
            children = self.directory_entries(target['relative'], max(0, settings['submenu_depth'] - 1)) if target.get('relative') in self.directories and settings['submenu_depth'] > 0 else []
            pins.append({'label': pin['label'], 'url': target['url'], 'path': target.get('relative', ''), 'kind': 'pin', 'children': children})
        used = assign_keys(pins, used)
        entries = self.directory_entries(directory, settings['submenu_depth'])
        assign_keys(entries, used)
        parser = Rewriter(self, directory)
        rendered = markdown.markdown(body, extensions=['fenced_code', 'tables', 'toc', 'sane_lists'])
        cleaned = bleach.clean(rendered, tags={'h1','h2','h3','h4','p','a','img','strong','em','ul','ol','li','blockquote','pre','code','hr','br','table','thead','tbody','tr','th','td'}, attributes={'*':['id'], 'a':['href','title'], 'img':['src','alt','title']}, protocols={'https','http','mailto'}, strip=True)
        parser.feed(cleaned)
        return {'url': url, 'directory': directory, 'source': relative or '(generated directory index)', 'body': body, 'html': ''.join(parser.output), 'images': parser.images, 'links': parser.links, 'controls': controls, 'pins': pins, 'entries': entries, 'up': up, 'brand': settings['brand'], 'submenu_depth': settings['submenu_depth'], 'title': metadata.get('title') or next((line.lstrip('# ').strip() for line in body.splitlines() if line.startswith('# ')), 'WE document'), 'demo': True}


class Rewriter(HTMLParser):
    def __init__(self, catalog, base):
        super().__init__(convert_charrefs=True)
        self.catalog, self.base = catalog, base
        self.output, self.images, self.links = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        field = 'href' if tag == 'a' else 'src' if tag == 'img' else None
        if field and attrs.get(field):
            ref = self.catalog.resolve_reference(attrs[field], self.base)
            attrs[field] = ref['url']
            if tag == 'img':
                if ref.get('external'):
                    raise ValueError('Remote images are not published; keep referenced images in your public source')
                if ref.get('kind') != 'image':
                    raise ValueError('An image reference must point to a supported photo')
                if not attrs.get('alt', '').strip():
                    raise ValueError('Referenced images require descriptive alt text')
                index = len(self.images)
                self.images.append({**ref, 'alt': attrs['alt']})
                attrs.update({'data-image': str(index), 'tabindex': '0', 'role': 'button', 'aria-label': 'Open image: ' + attrs['alt'], 'srcset': ', '.join(v['url'] + ' ' + str(v['width']) + 'w' for v in ref['variants']), 'sizes': '(max-width: 800px) 94vw, 960px', 'width': str(ref['width']), 'height': str(ref['height']), 'loading': 'lazy'})
            elif ref.get('kind') == 'attachment':
                attrs['download'] = ref['name']
            elif ref.get('external'):
                attrs['rel'] = 'noopener noreferrer'
            self.links.append(ref)
        self.output.append('<' + tag + ''.join(' ' + name + '="' + html.escape(value or '', quote=True) + '"' for name, value in attrs.items()) + '>')

    def handle_endtag(self, tag):
        self.output.append('</' + tag + '>')

    def handle_data(self, data):
        self.output.append(html.escape(data))


def button_text(item):
    key = 'Esc' if item.get('key') == 'escape' else item.get('key') or '·'
    return '[' + key + ' ' + item['label'] + ']'


def chrome_lines(model):
    return [model['brand'] + ' / DOCUMENT TERMINAL', 'wecorp.network' + model['url'], ' '.join(button_text(x) for x in model['controls'] + model['pins']), 'ls /' + (model['directory'] + '/' if model['directory'] != '.' else ''), ' '.join(button_text(x) for x in model['entries']), 'cat ' + model['source']]


def inspect_directory(source):
    catalog = Catalog(source)
    models = {url: catalog.model(url) for url in sorted(catalog.routes)}
    return catalog, models


def build_directory(source, destination):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from markupsafe import Markup
    import shutil
    import sitegen
    catalog, models = inspect_directory(source)
    destination = Path(destination)
    env = Environment(loader=FileSystemLoader(CODE / 'explorer-ui'), autoescape=select_autoescape())
    template = env.get_template('page.html')
    for url, model in models.items():
        target = destination / unquote(url).strip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        images = [{key: image[key] for key in ('id', 'url', 'alt', 'width', 'height')} for image in model['images']]
        payload = {key: model[key] for key in ('url', 'directory', 'source', 'up', 'controls', 'pins', 'entries')}
        payload['images'] = images
        target.write_text(template.render(**model, rendered=Markup(model['html']), payload=payload, version=sitegen.version()))
    for asset in catalog.assets.values():
        if asset['kind'] == 'image':
            for variant in asset['variants']:
                target = destination / variant['url'].lstrip('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(variant['local'], target)
        else:
            target = destination / asset['url'].lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(asset['local'], target)
    shutil.copytree(CODE / 'explorer-ui/assets', destination / '_ui', dirs_exist_ok=True)
    (destination / 'build.json').write_text(json.dumps({'version': sitegen.version(), 'pages': len(models), 'referenced_assets': len(catalog.assets)}))
    (destination / '404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>WE / not found</title><body style="background:#0a0a0a;color:#eee;font:14px monospace;padding:24px">404 / no public document at this path.<p><a href="/" style="color:inherit">[h Home]</a></p></body></html>')
    return {'pages': len(models), 'referenced_assets': len(catalog.assets), 'excluded_drafts': len(catalog.excluded)}


def publish_directory(source, state):
    import tempfile
    import shutil
    import uuid
    from datetime import datetime, timezone
    from sitegen import activate
    if Path(source).is_symlink():
        raise ValueError('Source must be an explicit real public directory')
    source, state = Path(source).resolve(), Path(state).resolve()
    if state.is_relative_to(source):
        raise ValueError('Generated output must live outside the public source')
    (state / 'releases').mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix='.build-', dir=state / 'releases'))
    release = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    try:
        build_directory(source, staged)
        os.replace(staged, state / 'releases' / release)
        activate(state, release)
        return release
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise


def rollback_directory(state, release):
    import we
    from sitegen import activate
    we.token(release)
    activate(state, release)


def import_directory(source, destination, apply=False):
    import shutil
    import tempfile
    catalog, models = inspect_directory(source)
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Import destination must be absent; existing source directories are never overwritten')
    copy = sorted(set(catalog.pages) | set(catalog.assets) | {str(PurePosixPath(key) / '.head/navigation.json') for key in catalog.configs})
    plan = {'copy': copy, 'pages': len(catalog.pages), 'referenced_assets': len(catalog.assets), 'excluded_drafts': sorted(catalog.excluded), 'destination': str(destination), 'apply': apply}
    if apply:
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.import-', dir=destination.parent))
        try:
            for relative in copy:
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(catalog.source / relative, target)
            inspect_directory(staging)
            os.replace(staging, destination)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return plan


def render_terminal(*args, **kwargs):
    from explorer_terminal import render_terminal as render
    return render(*args, **kwargs)


if __name__ == '__main__':
    from explorer_terminal import main
    raise SystemExit(main())
