"""WE Corp local, file-first site publisher. No network writes or public admin API."""
from pathlib import Path
import json
import os
import re
import tempfile
import hashlib
import shutil
import warnings
from sitegen import view_model, publish, rollback, validate, build, version
from PIL import Image, ImageOps, ImageCms


def gallery(root, handle):
    return read_json(member_dir(root, handle) / "gallery.json")


def import_photo(root, handle, source, title, alt):
    directory = member_dir(root, handle)
    source = Path(source)
    if not alt.strip():
        raise ValueError("Describe the photograph with --alt before importing")
    if not source.is_file() or source.stat().st_size > 80 * 1024 * 1024:
        raise ValueError("Photo must be a file under 80 MiB")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    photo_id = digest[:12]
    items = gallery(root, handle)
    if any(x["id"] == photo_id for x in items):
        raise ValueError("This photograph is already in this member's gallery")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source) as opened:
            if opened.format not in ("JPEG", "PNG", "WEBP", "TIFF"):
                raise ValueError("Use JPEG, PNG, WebP or TIFF; export RAW/HEIC first")
            if opened.width * opened.height > 50_000_000:
                raise ValueError("Photo exceeds the prototype's 50 megapixel limit")
            opened.load()
            image = ImageOps.exif_transpose(opened)
            if image.info.get("icc_profile"):
                import io
                try:
                    profile = ImageCms.ImageCmsProfile(io.BytesIO(image.info["icc_profile"]))
                    image = ImageCms.profileToProfile(image, profile, ImageCms.createProfile("sRGB"), outputMode="RGB")
                except (ValueError, OSError, ImageCms.PyCMSError) as e:
                    raise ValueError("Invalid color profile; export an sRGB image first") from e
            elif image.mode in ("RGBA", "LA"):
                rgba = image.convert("RGBA")
                image = Image.new("RGB", image.size, "white")
                image.paste(rgba, mask=rgba.getchannel("A"))
            else:
                image = image.convert("RGB")
    root = Path(root)
    original = Path("originals") / handle / (photo_id + source.suffix.lower())
    destination = root / "media" / handle / photo_id
    if destination.exists() or (root / original).exists():
        raise ValueError("Unreferenced existing photo files; inspect before retrying")
    destination.parent.mkdir(parents=True, exist_ok=True)
    (root / original).parent.mkdir(parents=True, exist_ok=True)
    variants = []
    staging = Path(tempfile.mkdtemp(prefix=".photo-", dir=destination.parent))
    try:
        sizes = sorted(set(min(image.width, n) for n in (480, 960, 1600, 2400)))
        for size in sizes:
            prepared = image.copy()
            prepared.thumbnail((size, 2400), Image.Resampling.LANCZOS)
            # Construct fresh pixels: neither camera EXIF nor profiles survive.
            clean = Image.new("RGB", prepared.size)
            clean.paste(prepared)
            name = f"{size}.webp"
            clean.save(staging / name, "WEBP", quality=88, method=6)
            variants.append({"file": str(Path("media") / handle / photo_id / name), "width": clean.width, "height": clean.height, "bytes": (staging / name).stat().st_size})
        (root / original).write_bytes(raw)
        os.replace(staging, destination)
        item = {"id": photo_id, "title": title, "alt": alt, "caption": "", "published": False, "original": str(original), "sha256": digest, "width": image.width, "height": image.height, "variants": variants}
        items.append(item)
        write_json(directory / "gallery.json", items)
        return item
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(destination, ignore_errors=True)
        (root / original).unlink(missing_ok=True)
        raise


def reorder_photos(root, handle, ids):
    items = gallery(root, handle)
    if len(ids) != len(set(ids)) or set(ids) != {x["id"] for x in items}:
        raise ValueError("Reorder must contain every gallery ID exactly once, including drafts")
    by_id = {x["id"]: x for x in items}
    write_json(member_dir(root, handle) / "gallery.json", [by_id[i] for i in ids])


def set_photo(root, handle, photo_id, **updates):
    items = gallery(root, handle)
    item = next((x for x in items if x["id"] == photo_id), None)
    if item is None:
        raise ValueError("Unknown photo ID")
    if not set(updates).issubset({"title", "alt", "caption", "published"}):
        raise ValueError("Unknown photograph field")
    if "alt" in updates and not updates["alt"].strip():
        raise ValueError("Alt text cannot be blank")
    item.update(updates)
    write_json(member_dir(root, handle) / "gallery.json", items)


def token(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", value):
        raise ValueError("Use 1–48 lowercase letters, digits or hyphens, starting with a letter or digit")
    return value


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def initialize(root):
    root = Path(root)
    for folder in ("content/members", "originals", "media", "releases"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    if not (root / "content/site.json").exists():
        write_json(root / "content/site.json", {"name": "WE CORP", "tagline": "Tools for a life of your own.", "demo": False})
    if not (root / "content/home.md").exists():
        (root / "content/home.md").write_text("# Technology belongs to the people who use it.\n\nBuild, share, and take your work with you.\n")


def member_dir(root, handle):
    directory = Path(root) / "content/members" / token(handle)
    if not (directory / "member.json").is_file():
        raise ValueError(f"Unknown member: {handle}")
    return directory


def add_member(root, handle, name, role, listed=False):
    initialize(root)
    directory = Path(root) / "content/members" / token(handle)
    if directory.exists():
        raise ValueError("Member already exists")
    directory.mkdir()
    write_json(directory / "member.json", {"handle": handle, "name": name, "role": role, "listed": listed, "contact": ""})
    (directory / "bio.md").write_text(f"# {name}\n\n{role}\n")
    (directory / "posts").mkdir()
    (directory / "projects").mkdir()
    write_json(directory / "gallery.json", [])


def entry_path(root, handle, kind, slug):
    if kind not in ("posts", "projects"):
        raise ValueError("Entry kind must be posts or projects")
    return member_dir(root, handle) / kind / (token(slug) + ".md")


def write_entry(path, metadata, body):
    path = Path(path)
    text = "---\n" + json.dumps(metadata, indent=2, ensure_ascii=False) + "\n---\n\n" + body.rstrip() + "\n"
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".entry-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_entry(path):
    text = Path(path).read_text()
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"Entry needs JSON frontmatter between --- delimiters: {Path(path).name}")
    head, body = text[4:].split("\n---\n", 1)
    metadata = json.loads(head)
    if not isinstance(metadata, dict) or not isinstance(metadata.get("title"), str) or not isinstance(metadata.get("published"), bool):
        raise ValueError("Entry needs a title and boolean published field")
    return metadata, body


def create_entry(root, handle, kind, slug, title):
    from datetime import date
    path = entry_path(root, handle, kind, slug)
    if path.exists():
        raise ValueError("Entry already exists")
    write_entry(path, {"title": title, "date": date.today().isoformat(), "published": False, "summary": ""}, "Write your story here.\n")
    return path


def set_entry(root, handle, kind, slug, **updates):
    path = entry_path(root, handle, kind, slug)
    metadata, body = read_entry(path)
    for key, value in updates.items():
        if key not in ("title", "summary", "published", "date"):
            raise ValueError("Unknown entry field")
        metadata[key] = value
    write_entry(path, metadata, body)


def markdown_html(text):
    import bleach
    import markdown
    rendered = markdown.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])
    def attributes(tag, name, value):
        if tag == "a":
            return name in ("href", "title")
        if tag == "img":
            if name in ("alt", "title"):
                return True
            if name == "src":
                return bool(re.fullmatch(r"/media/[a-z0-9][a-z0-9-]{0,47}/[a-f0-9]{12}/[0-9]+\.webp", value))
        return False
    return bleach.clean(rendered, tags={"h1", "h2", "h3", "h4", "p", "a", "img", "strong", "em", "ul", "ol", "li", "blockquote", "pre", "code", "hr", "br", "table", "thead", "tbody", "tr", "th", "td"}, attributes=attributes, protocols={"https", "http", "mailto"}, strip=True)


if __name__ == "__main__":
    import sys
    from cli import main
    sys.exit(main())
