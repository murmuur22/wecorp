# Verification and scope

This is a local single-operator prototype, source version **0.2.0**. Source publication is not a production deployment or a GitHub Release.

## Executed from a clean publication checkout

- `uv sync --locked` installed a fresh isolated environment.
- `uv run pytest -q`: **42 tests passed**. The suite includes real Chromium and PTY input, original/derivative image checks, static publication, import dry-run/application, link rewriting, draft/unlisted behavior, failed-build preservation and rollback.
- `node --check explorer-ui/assets/explorer.js` and `node --check static/site.js` passed.
- The documented `uv run python setup_explorer_demo.py --download-photos` command actually downloaded its reference photographs, built the sample directory and published local static output without relying on the developer's existing workspace.
- `uv run python explorer.py validate` reported **16 public pages, 5 referenced assets and 1 excluded draft** for that fresh demo.
- Keyboard tests include 50 similarly named documents, entries without a single-letter key, disabled shortcuts, typing guards and long filenames at mobile widths.
- Responsive/browser tests cover 320/390/1140 px for the directory prototype and the earlier structured prototype's desktop/mobile sizes. Viewer tests exercise previous/next, Escape and focus return. Basic document links work without JavaScript.

The screenshot boards were captured from the working prototype. CLI panels render actual recorded Rich output, not native terminal-window photographs. Fonts in a user's terminal can change the exact appearance.

## Boundaries

- Browser command entry is navigation only; there is no public system-command execution or editing API.
- Preview listens only on loopback and serves the selected generated release, not authoring sources, configuration or original photographs.
- Public-source selection is explicit. Ordinary Markdown inside it is eligible by default. Do not select a private vault. Draft/private flags exclude output; unlisted pages remain public by URL.
- Standard relative Markdown links and anchors are rewritten, but existence of every heading fragment is not yet validated.
- Local directory import applies only to a new destination. No destructive ongoing synchronization or remote transport is implemented.
- Rollback restores published output, not source files; retained local releases are not off-host backups.
- No concurrent-writer, power-loss, hostile multi-tenant, comprehensive accessibility/security, Windows or Safari qualification is claimed.
- No VPS installation, DNS changes, remote test/build runners, deployed organization network or production access is implied.
- Obsidian wikilinks/transclusions/plugins, YAML settings and image-logo configuration are deferred.
- Reference photos and sample text are not the author's finished portfolio. See [image credits](image-credits.md).

Tests and syntax checks establish the behaviors exercised above, not a general security certification. No project-wide license has been selected.
