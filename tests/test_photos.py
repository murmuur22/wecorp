import hashlib
from PIL import Image
import pytest
import we
from test_core import site


def test_photo_import_preserves_original_and_prepares_private_web_derivatives(site, tmp_path):
    assert hasattr(we, "import_photo"), "Photo pipeline missing"
    source = tmp_path / "camera.jpg"
    photo = Image.new("RGB", (2800, 1400), "orange")
    exif = Image.Exif()
    exif[270] = "PRIVATE CAMERA NOTE"
    exif[274] = 6
    photo.save(source, exif=exif)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    item = we.import_photo(site, "murmuur", source, "Camera test", "An orange test frame")
    assert hashlib.sha256((site / item["original"]).read_bytes()).hexdigest() == before
    assert item["published"] is False
    assert item["width"] == 1400 and item["height"] == 2800
    assert max(v["width"] for v in item["variants"]) <= 1400
    for variant in item["variants"]:
        with Image.open(site / variant["file"]) as img:
            assert not img.getexif()
            assert "exif" not in img.info
            assert max(img.size) <= 2400
    with pytest.raises(ValueError):
        we.import_photo(site, "murmuur", source, "Copy", "Duplicate")
    with pytest.raises(ValueError):
        we.import_photo(site, "murmuur", source, "No alt", "")


def test_gallery_reorder_and_visibility(site, tmp_path):
    assert hasattr(we, "reorder_photos"), "Gallery ordering missing"
    items = []
    for n, color in enumerate(["red", "blue"]):
        p = tmp_path / f"{n}.png"
        Image.new("RGB", (64, 32), color).save(p)
        items.append(we.import_photo(site, "murmuur", p, color, color))
    ids = [item["id"] for item in items]
    we.reorder_photos(site, "murmuur", ids[::-1])
    assert [x["id"] for x in we.gallery(site, "murmuur")] == ids[::-1]
    with pytest.raises(ValueError):
        we.reorder_photos(site, "murmuur", ids[:1])
    we.set_photo(site, "murmuur", ids[0], published=True, caption="Updated")
    assert we.gallery(site, "murmuur")[1]["caption"] == "Updated"
    assert we.gallery(site, "murmuur")[1]["published"] is True
