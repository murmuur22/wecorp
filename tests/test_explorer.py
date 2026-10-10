from pathlib import Path
import pytest


def module():
    import importlib
    assert (Path(__file__).parents[1] / 'explorer.py').exists(), 'Directory explorer is not implemented'
    return importlib.import_module('explorer')


@pytest.fixture
def source(tmp_path):
    p = tmp_path / 'public'
    p.mkdir()
    (p / 'index.md').write_text('# A network of our own\n\nA public front door.\n')
    (p / 'about.md').write_text('# About\n\nAn independent practice.\n')
    member = p / '@murmuur'; member.mkdir()
    (member / 'index.md').write_text('# murmuur\n\nA portfolio.\n')
    (member / '.head').mkdir()
    (member / '.head/navigation.json').write_text('{"listed":false}')
    (member / 'photography').mkdir()
    (member / 'photography/index.md').write_text('# Photography\n\n[About](../../about.md#about)\n')
    (p / '.head').mkdir()
    (p / '.head/navigation.json').write_text('{"brand":"WE CORP", "pins":[{"label":"About", "path":"about.md"}],"submenu_depth":1}')
    (p / 'draft.md').write_text('---\n{"published":false}\n---\n# Do not publish\n')
    return p


def test_directory_discovery_shared_chrome_shortcuts_and_unlisted_pages(source):
    ex = module()
    catalog = ex.Catalog(source)
    home = catalog.model('/')
    assert home['source'] == 'index.md'
    assert '@murmuur/' not in [x['label'] for x in home['entries']]
    assert 'draft.md' not in [x['label'] for x in home['entries']]
    member = catalog.model('/@murmuur/')
    assert 'photography/' in [x['label'] for x in member['entries']]
    assert member['up'] == '/'
    photo = catalog.model('/@murmuur/photography/')
    assert photo['up'] == '/@murmuur/'
    assert photo['pins'][0]['url'] == '/about/'
    assert 'href="/about/#about"' in photo['html']
    keys = [x['key'] for x in photo['controls'] + photo['pins'] + photo['entries'] if x.get('key')]
    assert len(keys) == len(set(keys))
    assert ex.chrome_lines(photo) == ex.chrome_lines(catalog.model('/@murmuur/photography/'))


def test_navigation_handles_duplicate_initials_and_large_directories(source):
    ex = module()
    for i in range(50):
        (source / f'alpha-{i:02}.md').write_text(f'# Alpha {i}\n')
    model = ex.Catalog(source).model('/')
    keys = [x['key'] for x in model['controls'] + model['pins'] + model['entries'] if x.get('key')]
    assert len(keys) == len(set(keys))
    assert any(not x['key'] for x in model['entries']) # arrows + Enter remain the fallback
    assert [x['label'] for x in model['entries']] == sorted(x['label'] for x in model['entries'])


def test_images_and_attachments_are_rewritten_but_unlinked_files_stay_private(source, tmp_path):
    ex = module()
    from PIL import Image
    assets = source / '@murmuur/photography/images'; assets.mkdir()
    frame = assets / 'street.jpg'
    image = Image.new('RGB', (2600, 1300), 'orange')
    tags = Image.Exif(); tags[270] = 'PRIVATE CAMERA NOTE'; image.save(frame, exif=tags)
    (assets / 'unlinked.txt').write_text('DO NOT COPY')
    (source / 'guide.txt').write_text('A public download.')
    (source / '@murmuur/photography/index.md').write_text('# Frames\n\n![Street](images/street.jpg)\n\n[Guide](../../guide.txt)\n')
    catalog = ex.Catalog(source)
    model = catalog.model('/@murmuur/photography/')
    assert len(model['images']) == 1
    assert 'srcset=' in model['html'] and 'data-image=' in model['html']
    assert '/_media/' in model['html'] and '/_files/' in model['html']
    assert 'images/street.jpg' not in model['html']
    assert '@murmuur/photography/images/unlinked.txt' not in catalog.assets
    for variant in model['images'][0]['variants']:
        with Image.open(variant['local']) as prepared:
            assert not prepared.getexif()
            assert max(prepared.size) <= 2400
    assert frame.is_file() and Image.open(frame).getexif()[270] == 'PRIVATE CAMERA NOTE'
    (source / 'about.md').write_text('![External tracker](https://example.test/pixel.png)')
    with pytest.raises(ValueError, match='Remote image'):
        ex.Catalog(source).model('/about/')


def test_directory_publish_import_plan_and_rollback(source, tmp_path):
    ex = module()
    assert hasattr(ex, 'publish_directory'), 'Directory publishing not implemented'
    state = tmp_path / 'state'
    first = ex.publish_directory(source, state)
    current = (state / 'current').resolve()
    assert (current / '@murmuur/photography/index.html').is_file()
    assert not (current / 'draft').exists()
    assert not (current / '.head').exists()
    html = (current / '@murmuur/index.html').read_text()
    assert 'id="header-bar"' in html and 'id="directory-bar"' in html
    assert 'id="document"' in html
    destination = tmp_path / 'imported'
    plan = ex.import_directory(source, destination, apply=False)
    assert not destination.exists()
    assert 'draft.md' not in plan['copy']
    ex.import_directory(source, destination, apply=True)
    assert (destination / '@murmuur/photography/index.md').is_file()
    assert (destination / '.head/navigation.json').is_file()
    with pytest.raises(ValueError):
        ex.import_directory(source, destination, apply=True)
    (source / 'about.md').write_text('# Changed\n')
    second = ex.publish_directory(source, state)
    assert first != second
    ex.rollback_directory(state, first)
    assert (state / 'current').resolve().name == first
    (source / 'about.md').write_text('[Broken](missing.md)')
    with pytest.raises(ValueError):
        ex.publish_directory(source, state)
    assert (state / 'current').resolve().name == first


def test_reserved_output_namespace_cannot_be_shadowed_by_source(source):
    ex = module()
    (source/'_ui.md').write_text('# A conflicting document\n')
    with pytest.raises(ValueError, match='reserved'):
        ex.Catalog(source)


def test_linked_attachment_keeps_its_media_fragment(source):
    ex = module()
    (source/'recording.mp4').write_bytes(b'unit-test attachment; no media decoding in this test')
    (source/'about.md').write_text('[Recording excerpt](recording.mp4#t=30)')
    catalog=ex.Catalog(source)
    model=catalog.model('/about/')
    assert '#t=30' in model['html'], 'Attachment rewriting lost the media fragment'
    assert all('#' not in asset['url'] for asset in catalog.assets.values())


def test_publication_rejects_a_symlink_selected_source(source,tmp_path):
    ex = module()
    link=tmp_path/'public-link'
    link.symlink_to(source,target_is_directory=True)
    with pytest.raises(ValueError,match='symlink|real public directory'):
        ex.publish_directory(link,tmp_path/'symlink-state')


def test_colliding_urls_and_private_links_fail_before_publication(source):
    ex = module()
    (source / '@murmuur.md').write_text('# Collision\n')
    with pytest.raises(ValueError, match='collision'):
        ex.Catalog(source)
    (source / '@murmuur.md').unlink()
    (source / 'about.md').write_text('[Private](draft.md)')
    with pytest.raises(ValueError, match='excluded|private|draft'):
        ex.Catalog(source).model('/about/')
