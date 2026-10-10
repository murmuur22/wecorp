# WE / directory prototype — source 0.2.0

A separate working local prototype beside the original structured portfolio. **No migration of the first workspace and no remote deployment.**

## Open it

Local preview: http://127.0.0.1:8768/ ; portfolio: http://127.0.0.1:8768/@murmuur/ . Only reachable on the machine running the preview.

From a fresh clone, see the [README quick start](../README.md#try-it-locally) to install dependencies and explicitly download the demo photographs.

```sh
cd wecorp
uv sync --locked
uv run python explorer.py shell /@murmuur/
# If the preview is not already listening:
uv run python explorer.py preview --port 8768
```

Do not start a duplicate listener. Preview binds 127.0.0.1 and serves only the selected static output, not the authoring tree.

## The same shell in both interfaces

1. Identity and location, then **header bar**: Home, Up, Back, Help, Raw, Keys and configured pinned entries.
2. **Directory bar**: `ls` path and the current directory's eligible Markdown files/folders.
3. `cat` source filename and the **document**: raw Markdown in the terminal by default, HTML in the browser by default.
4. Command line and footer.

The same catalog/model assigns labels, paths, keys and ordering. Font, width, line rhythm, grayscale colors and shell structure are matched. Browser Raw mode shows the same source text as the CLI. Native-terminal font settings still affect the actual terminal; browser images and modal viewer do not become full-color images in a plain text terminal. Screenshots of CLI are HTML renders of **actual recorded Rich output**, not Terminal.app captures or invented transcripts.

## Keyboard navigation

- Printed single keys open entries across both bars without collisions. Keys are chosen deterministically for the current directory; changing filenames/entries can change assignments. No promise of globally permanent keys.
- Browser arrows select directory entries, Enter opens. Right on a folder summary opens its menu. Tab/Enter remain standard accessible controls.
- `h` Home, `u` parent directory, Escape previous page/fallback Up, `?` Help, `r` raw/rendered, `k` single-key toggle, `/` command entry.
- Extra entries without available letters display `·`; arrows, Enter and clicks still work. Real browser test exercised 50 similarly named documents.
- Single-key shortcuts do not activate while typing or intercept Ctrl/Meta/Alt browser commands. The browser toggle persists locally and can be re-enabled by clicking Keys.
- Terminal uses immediate keys in a TTY; arrows/Enter select/open. `/` enters a complete command; `q` exits. Piped sessions take newline-terminated commands.
- Browser images: click or keyboard-activate to open the page-local viewer; left/right move among referenced images; Escape closes and returns focus.

## Your source tree

```text
explorer-workspace/
  public/                  deliberately selected public authoring root
    index.md
    about.md
    .head/navigation.json
    @murmuur/
      index.md
      contact.md
      .head/navigation.json
      photography/
        index.md
        city-at-night.md
        images/street.jpg
      writing/independence.md
  state/
    releases/RELEASE/
    current -> releases/RELEASE/
  .we-photo-cache/          private prepared-media cache, outside public source
```

`index.md` is the directory's landing page. `note.md` becomes `/note/`; folders without index.md get a generated landing page only if they contain eligible Markdown documents. Ordinary Markdown requires no frontmatter. Optional metadata is JSON between `---` delimiters:

```md
---
{"published": false}
---
# A working draft
```

**The selected root is public authoring material by default.** Do not point it at your entire private vault. `published:false` excludes a page; folder `.head` can also set `published:false`. `listed:false` removes a page/folder from automatic parent navigation, not from public access by URL. Dotfiles/config are not served.

## Relative links, images and downloads

```md
![An accurate description](images/street.jpg)
[Another note](../writing/independence.md#files-not-feeds)
[Another website](https://example.com)
[Download a guide](attachments/guide.pdf)
```

The publisher resolves each reference from the source document's directory, rewrites internal .md links into site URLs, preserves anchors, and copies only supported referenced assets. It validates target files/pages, but does not yet validate that every fragment names an existing heading.

Images stay organized in your source tree. Their originals are not served; source images are normalized into metadata-stripped responsive WebP derivatives using the existing photo pipeline. No upscaling; long edge capped at 2400 px. Every embedded photo needs alt text. Image ordering follows Markdown ordering, not an implicit image-folder listing. Unlinked images do not appear or enter public output.

Reference photos in this demo are local Unsplash examples retained from the previous task, **not murmuur's photography**. All text is example copy. Replace and review before publication.

Supported downloads: PDF, TXT, CSV, JSON, ZIP, MP3, MP4, WebM, Ogg. HTML/SVG/scripts are not published as attachments. Remote image embeds are rejected; external text hyperlinks are allowed. Raw HTML is sanitized. Symlinks, references outside the approved root, links to drafts/private configuration, missing targets and reserved-output URL collisions fail the build.

Standard Markdown links are implemented. Obsidian `[[wikilinks]]`, transclusions and vault plugins are **not** implemented.

## Pinned header and submenu depth

A `.head/navigation.json` applies to its directory and descendants; nearer settings override inherited fields. Pinned paths resolve from the directory that defines that pins list, not from the currently viewed document.

```json
{
  "brand": "WE CORP",
  "pins": [
    {"label": "About", "path": "about.md"},
    {"label": "Manual", "path": "manual/"}
  ],
  "submenu_depth": 1
}
```

Depth 0 disables dropdowns; 1–3 builds bounded recursive directory menus. Text branding is shared across both renderers; image-logo configuration and YAML settings are deferred.

```sh
uv run python explorer.py head @murmuur --depth 2
uv run python explorer.py head @murmuur --listed no
```

## Edit and publish from the terminal

```sh
uv run python explorer.py new @murmuur/writing/new-note.md --title 'New note'
EDITOR=nvim uv run python explorer.py edit @murmuur/writing/new-note.md
uv run python explorer.py photo-import ./camera.jpg @murmuur/photography/images/camera.jpg
uv run python explorer.py validate
uv run python explorer.py publish
uv run python explorer.py status
uv run python explorer.py rollback RELEASE_ID
```

Use an installed editor; Neovim was not installed on this host during verification. `$EDITOR` is respected and defaults to nano. Editor integration was exercised with a real deterministic editor subprocess, not a claimed Neovim UI test.

Photo import preserves original bytes in the authoring tree. Reference the file in Markdown before publishing. New files/photos refuse overwrite. Publishing stages a full static release then switches the local `current` symlink. A failed build retains the previous selection. Rollback changes published output only; source files are unchanged.

## Import an existing public directory

```sh
uv run python explorer.py import-tree /path/to/public-directory /path/to/new-destination
uv run python explorer.py import-tree /path/to/public-directory /path/to/new-destination --apply
```

The default is a real dry-run report; the destination is not created. Apply copies eligible Markdown, required referenced files and navigation configs into a **new, previously absent** destination, retaining organization. Existing destinations are refused; no automatic deletion/overwriting sync is implemented. Source trees and originals are not modified by import. Image preparation may populate a private cache during validation/dry run.

Select a custom working tree with `--source ABSOLUTE_DIR --state ABSOLUTE_STATE_DIR` before the command. State must be outside source. Remote transport/VPS installation is not implemented.

## Verification and screenshots

```sh
uv run pytest -q
node --check explorer-ui/assets/explorer.js
uv run python capture_explorer.py
```

Tests cover discovery, collision-free keys, 50-entry keyboard fallback, rewritten Markdown links/anchors, unlisted/draft handling, image normalization, referenced downloads, import planning/application, failed-build preservation, rollback, CLI edits and real browser/TTY navigation. Chromium at 320/390/1140 px; original prototype remains covered too.

Captures: `artifacts/explorer/screenshots/`; comparison boards: `artifacts/explorer/01-mirrored-interface.jpg` through `05-publishing.jpg`. `capture-result.json` records real workflow/readback results. Full screenshots retain content beyond overview crops.

Prototype limits: no public deployment, multiwriter/concurrent-source guarantees, off-host backups, power-loss qualification, full accessibility/security audit or Safari qualification. This is a public document publisher, not a live filesystem endpoint or network enrollment system.
