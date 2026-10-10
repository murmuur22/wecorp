import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import uuid
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

CODE = Path(__file__).resolve().parent
NAV = [
    ("Home", "h", "home", "/"),
    ("Portfolio", "p", "portfolio", "/@{handle}/"),
    ("Gallery", "g", "gallery", "/@{handle}/gallery/"),
    ("Blog", "b", "blog", "/@{handle}/blog/"),
    ("Work", "w", "work", "/@{handle}/work/"),
    ("Contact", "c", "contact", "/@{handle}/contact/"),
    ("Help", "?", "help", "/@{handle}/help/"),
    ("Back", "escape", "back", "/@{handle}/"),
]
GLOBAL_NAV = [("Home", "h", "home", "/"), ("About", "a", "about", "/about/"), ("Members", "m", "members", "/members/"), ("Help", "?", "help", "/help/")]


def members(root):
    import we
    values = []
    for p in sorted((Path(root) / "content/members").iterdir()):
        if p.is_dir() and (p / "member.json").exists():
            we.token(p.name)
            data = we.read_json(p / "member.json")
            if data.get("handle") != p.name or not isinstance(data.get("listed"), bool):
                raise ValueError("Invalid member metadata")
            values.append(data)
    return values


def entries(root, handle, kind, published=True):
    import we
    result = []
    for p in (we.member_dir(root, handle) / kind).glob("*.md"):
        slug = we.token(p.stem)
        meta, body = we.read_entry(p)
        if not published or meta["published"]:
            result.append({**meta, "slug": slug, "body": body, "html": Markup(we.markdown_html(body)), "url": f"/@{handle}/{'blog' if kind == 'posts' else 'work'}/{slug}/"})
    return sorted(result, key=lambda x: (x.get("date", ""), x["slug"]), reverse=True)


def view_model(root, view, handle=None, item=None):
    import we
    root = Path(root)
    site = we.read_json(root / "content/site.json")
    data = dict(view=view, handle=handle, site=site, member=None, members=members(root), photos=[], posts=[], projects=[], item=None, body="", path="/", title="WE CORP", subtitle=site.get("tagline", "Independent tools. Shared possibilities."))
    nav = NAV if handle else GLOBAL_NAV
    data["nav"] = [{"label": label, "key": key, "command": command, "url": url.format(handle=handle or ""), "active": command == view, "letter": label[0] if key not in ("?", "escape") else ("?" if key == "?" else "Esc")} for label, key, command, url in nav]
    if handle:
        directory = we.member_dir(root, handle)
        data["member"] = we.read_json(directory / "member.json")
        data["photos"] = [x for x in we.gallery(root, handle) if x["published"]]
        data["posts"] = entries(root, handle, "posts")
        data["projects"] = entries(root, handle, "projects")
        suffix = {"portfolio": "", "gallery": "gallery/", "blog": "blog/", "work": "work/", "contact": "contact/", "help": "help/", "photo": f"gallery/{item}/", "post": f"blog/{item}/", "project": f"work/{item}/"}
        if view not in suffix and view != "home":
            raise ValueError("Unknown member view")
        data["path"] = "/" if view == "home" else f"/@{handle}/" + suffix[view]
        data["title"] = {"portfolio": "A practice of my own.", "gallery": "Field of view.", "blog": "Notes from the network.", "work": "Selected work.", "contact": "Start a conversation.", "help": "You already know how.", "photo": "", "post": "", "project": "", "home": "A network of our own."}[view]
        data["subtitle"] = data["member"]["role"]
        if view == "portfolio":
            data["title"] = data["member"].get("headline", data["title"])
            data["body"] = (directory / "bio.md").read_text()
        if view == "photo":
            found = next((x for x in data["photos"] if x["id"] == item), None)
            if not found:
                raise ValueError("Photograph is not published")
            data["item"] = found
            data["title"] = found["title"]
            index = data["photos"].index(found)
            data["previous"] = data["photos"][index - 1]["id"] if index > 0 else None
            data["next"] = data["photos"][index + 1]["id"] if index + 1 < len(data["photos"]) else None
        if view in ("post", "project"):
            found = next((x for x in data["posts" if view == "post" else "projects"] if x["slug"] == item), None)
            if not found:
                raise ValueError("Entry is not published")
            data["item"] = found
            data["title"] = found["title"]
            data["body"] = found["body"]
    else:
        if view not in ("home", "about", "members", "help"):
            raise ValueError("Choose a member first: member murmuur")
        data["path"] = "/" if view == "home" else f"/{view}/"
        data["title"] = {"home": "A network of our own.", "about": "Less dependence. More possibility.", "members": "People, not profiles.", "help": "You already know how."}[view]
    if view in ("home", "about"):
        data["body"] = (root / "content/home.md").read_text()
        if view == "home":
            data["title"] = site.get("title", "A network of our own.")
    data["html"] = Markup(we.markdown_html(data["body"]))
    data["version"] = version()
    return data


def version():
    import tomllib
    return tomllib.loads((CODE / "pyproject.toml").read_text())["project"]["version"]


def validate(root):
    import we
    count = {"members": 0, "photos": 0, "entries": 0}
    we.read_json(Path(root) / "content/site.json")
    for member in members(root):
        handle = member["handle"]
        count["members"] += 1
        for kind in ("posts", "projects"):
            count["entries"] += len(entries(root, handle, kind, published=False))
        ids = set()
        for photo in we.gallery(root, handle):
            if not isinstance(photo.get("published"), bool) or not photo.get("alt", "").strip() or not re_photo(photo.get("id", "")) or photo["id"] in ids:
                raise ValueError("Invalid or duplicate photo metadata")
            ids.add(photo["id"])
            count["photos"] += 1
            for variant in photo["variants"]:
                p = Path(root) / variant["file"]
                expected = Path(root) / "media" / handle / photo["id"]
                if p.is_symlink() or p.resolve().parent != expected.resolve() or not p.is_file():
                    raise ValueError("Photo derivative is missing or unsafe")
    return count


def re_photo(value):
    import re
    return bool(re.fullmatch(r"[a-f0-9]{12}", value))


def build(root, output):
    import we
    root, output = Path(root), Path(output)
    validate(root)
    output.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(CODE / "templates"), autoescape=select_autoescape())
    template = env.get_template("page.html")
    sitemap = []
    def page(view, handle=None, item=None):
        model = view_model(root, view, handle, item)
        destination = output / model["path"].lstrip("/") / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(template.render(**model))
        sitemap.append(model["path"])
    for v in ("home", "about", "members", "help"):
        page(v)
    for member in members(root):
        handle = member["handle"]
        for v in ("portfolio", "gallery", "blog", "work", "contact", "help"):
            page(v, handle)
        for photo in we.gallery(root, handle):
            if not photo["published"]:
                continue
            page("photo", handle, photo["id"])
            for variant in photo["variants"]:
                target = output / variant["file"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / variant["file"], target)
        for kind, v in (("posts", "post"), ("projects", "project")):
            for entry in entries(root, handle, kind):
                page(v, handle, entry["slug"])
    shutil.copytree(CODE / "static", output / "assets", dirs_exist_ok=True)
    (output / "robots.txt").write_text("User-agent: *\nAllow: /\n")
    (output / "404.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>WE / Not found</title><body style="background:#111;color:#eee;font:18px monospace;padding:4rem"><h1>404 / Nothing here.</h1><a style="color:inherit" href="/">[Home]</a></body></html>')
    (output / "build.json").write_text(json.dumps({"version": version(), "pages": len(sitemap), "built": datetime.now(timezone.utc).isoformat()}))
    return sitemap


def activate(root, release_id):
    root = Path(root)
    target = root / "releases" / release_id
    if not target.is_dir() or target.is_symlink() or not (target / "build.json").is_file():
        raise ValueError("Unknown complete release")
    temporary = root / (".current-" + uuid.uuid4().hex)
    temporary.symlink_to(Path("releases") / release_id)
    os.replace(temporary, root / "current")


def publish(root):
    root = Path(root)
    release_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    staged = Path(tempfile.mkdtemp(prefix=".build-", dir=root / "releases"))
    try:
        build(root, staged)
        destination = root / "releases" / release_id
        os.replace(staged, destination)
        activate(root, release_id)
        return release_id
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise


def rollback(root, release_id):
    import we
    we.token(release_id)
    activate(root, release_id)
