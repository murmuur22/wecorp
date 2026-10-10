import importlib.util
from pathlib import Path
import pytest
import we


@pytest.fixture
def site(tmp_path):
    we.initialize(tmp_path)
    we.add_member(tmp_path, "murmuur", "murmuur", "Photographer", listed=False)
    return tmp_path


def test_markdown_can_embed_local_photo_derivatives_without_remote_trackers():
    rendered = we.markdown_html('![City](/media/murmuur/abcdefabcdef/960.webp)')
    assert '<img' in rendered and 'src="/media/murmuur/abcdefabcdef/960.webp"' in rendered
    assert 'src="https://' not in we.markdown_html('![Tracker](https://example.test/pixel.png)')
    assert 'src="/media/../' not in we.markdown_html('![Bad](/media/../content/site.json)')


def test_markdown_lifecycle_and_sanitization(site):
    assert hasattr(we, "create_entry"), "Markdown entry lifecycle missing"
    we.create_entry(site, "murmuur", "posts", "first", "First <post>")
    metadata, body = we.read_entry(site / "content/members/murmuur/posts/first.md")
    assert metadata["published"] is False
    assert metadata["title"] == "First <post>"
    assert body.strip()
    we.set_entry(site, "murmuur", "posts", "first", published=True)
    assert we.read_entry(site / "content/members/murmuur/posts/first.md")[0]["published"]
    rendered = we.markdown_html('# Hello\n\n<script>alert(1)</script>\n\n[bad](javascript:alert(1))')
    assert "<script>" not in rendered
    assert 'href="javascript:' not in rendered
    assert "<h1>Hello</h1>" in rendered
    with pytest.raises(ValueError):
        we.create_entry(site, "murmuur", "posts", "../escape", "No")


def test_member_creation_is_portable_and_handle_is_validated(tmp_path):
    source = Path(__file__).parents[1] / "we.py"
    assert source.exists(), "The CLI/storage implementation does not exist yet"
    spec = importlib.util.spec_from_file_location("we", source)
    we = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(we)
    we.initialize(tmp_path)
    we.add_member(tmp_path, "murmuur", "murmuur", "Photographer", listed=False)
    member = we.read_json(tmp_path / "content/members/murmuur/member.json")
    assert member["name"] == "murmuur"
    assert member["listed"] is False
    assert (tmp_path / "content/members/murmuur/bio.md").exists()
    with pytest.raises(ValueError):
        we.add_member(tmp_path, "../escape", "No", "No")
    with pytest.raises(ValueError):
        we.add_member(tmp_path, "murmuur", "No", "No")
