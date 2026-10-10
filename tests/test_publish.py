import pytest
import we
from test_core import site
from PIL import Image


def test_static_publish_excludes_drafts_and_originals_and_rolls_back(site, tmp_path):
    assert hasattr(we, "publish"), "Static publish missing"
    we.create_entry(site, "murmuur", "posts", "private-draft", "Private draft")
    we.create_entry(site, "murmuur", "posts", "hello", "Hello <world>")
    we.set_entry(site, "murmuur", "posts", "hello", published=True)
    p = tmp_path / "photo.png"
    Image.new("RGB", (128, 80), "purple").save(p)
    item = we.import_photo(site, "murmuur", p, "Demo photo", "Purple sample")
    first = we.publish(site)
    current = (site / "current").resolve()
    assert current.name == first
    assert (current / "@murmuur/index.html").is_file()
    assert not (current / "@murmuur/blog/private-draft").exists()
    assert not (current / "originals").exists()
    assert not (current / item["variants"][0]["file"]).exists()
    assert "Hello &lt;world&gt;" in (current / "@murmuur/blog/index.html").read_text()
    assert 'href="/@murmuur/"' not in (current / "members/index.html").read_text()
    we.set_photo(site, "murmuur", item["id"], published=True)
    second = we.publish(site)
    assert second != first
    assert ((site / "current").resolve() / item["variants"][0]["file"]).is_file()
    we.rollback(site, first)
    assert (site / "current").resolve().name == first
    with pytest.raises(ValueError):
        we.rollback(site, "../escape")
    (site / "content/members/murmuur/posts/broken.md").write_text("invalid frontmatter")
    with pytest.raises(ValueError):
        we.publish(site)
    assert (site / "current").resolve().name == first


def test_shared_navigation_and_view_model(site):
    assert hasattr(we, "view_model"), "Shared view model missing"
    view = we.view_model(site, "gallery", "murmuur")
    assert view["path"] == "/@murmuur/gallery/"
    keys = [n["key"] for n in view["nav"]]
    assert len(keys) == len(set(keys))
    assert [x["label"] for x in view["nav"]] == ["Home", "Portfolio", "Gallery", "Blog", "Work", "Contact", "Help", "Back"]
