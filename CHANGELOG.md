# Changelog

## Unreleased — directory prototype, source version 0.2.0

- Added a separate directory-driven prototype without migrating the original workspace.
- Matched browser/CLI shell: pinned header, current-directory ls row, source label, document, prompt and footer; browser Raw mode displays source Markdown.
- Added automatic Markdown/folder discovery, explicit public-root boundaries, inherited .head JSON configuration, pinned links and bounded submenu depth.
- Added deterministic collision-free displayed shortcuts across both bars, browser arrow/Enter fallback for large directories, typing/modifier guards and a persistent shortcut toggle.
- Added raw/rendered browser viewing, standard relative Markdown link rewriting, referenced attachment copying and a page-local keyboard-accessible photo viewer.
- Reused private-original/photo-derivative processing; unlinked assets and draft/config/source files are excluded from public output.
- Added real CLI document creation/editing, photo copying, header configuration, dry-run/new-destination directory import, validation, local publish/status/rollback and preview.
- Added directory/static-output refusal tests, real Chromium interaction/responsive tests and a real-TTY keyboard test, plus actual workflow/screenshots.

- Added a standalone demo setup with explicit `--download-photos` consent and input preflight before creating a workspace.
- Fixed attachment-fragment preservation and rejection of selected source-root symlinks through CLI/publication entry points, with reproduced regression tests and independent review.
- Prepared an illustrated public README, portable authoring guide and screenshot/reference-image credits; private workspaces and notes are excluded from the source publication.

No VPS/network deployment, remote upload, automatic destructive synchronization, Obsidian wiki syntax or image-logo support is implied.

## Earlier local prototype — source baseline 0.1.0

- Added a file-first static WE Corp website: landing/about, member portfolio, gallery/detail, blog/article, project index/case study, contact, directory and help.
- Shared browser/terminal navigation manifest, paths, page titles and content. Strict grayscale chrome and code blocks; color photographs on web, luminance previews in terminal.
- Added browser word controls, keyboard shortcuts, command navigation, photo arrows, focus states and mobile layouts.
- Added a real operator CLI and interactive shell with immediate single-key navigation in a real TTY and command entry via `/`.
- Added homepage/member edits, member listing control, editable/importable Markdown posts/projects and draft/published visibility.
- Added photo/batch import preserving original bytes, orientation/color normalization, metadata-stripped responsive WebP derivatives, captions, alt text, ordering and visibility.
- Added sanitized local photo embedding in Markdown.
- Added content validation, staged static builds, atomic local publication, retained-release rollback and loopback-only preview.
- Added automated storage/photo/CLI/static-publication/real-browser/real-PTY tests and executed workflow/screenshots.
- Added explicitly labeled sample content and local Unsplash reference photos. No user photo library read.

No remote deployment, GitHub publication, infrastructure changes or real portfolio content migration.
