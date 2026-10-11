---
type: adr
id: ADR-SKRIPT-0092
title: Script-bank tools ship as tool-owned bundles loaded as a package over their
  own directory
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-11'
status: accepted
deciders:
- user
links:
  governing:
  - TASK-SKRIPT-REP-0037
---

## Context

Four script-bank tools (`gruppgenerator`, `html_to_pdf_preview`,
`markdown_to_docx`, `yrkesgenerator`) had grown past the 500-line file limit.
A tool version stored one `source_code` text, the request factory wrote it to
`/work/script.py`, and the runner loaded that one file, so a tool could not be
split into modules. TASK-SKRIPT-REP-0037 authorizes tool-owned bundles; the
runner modularization map reference ("Direction B") already called bundles
tool-owned per version.

## Decision

A tool version carries a bundle: its entrypoint plus the tool's own modules and
data files. The tool owns the bundle; the shared runner gains no tool code.

- **Storage.** `tool_versions.source_code` stays the entrypoint.
  `tool_versions.bundle_files` (JSONB, not null, default `{}`, migration
  `d4be51baf417`) maps each other file's name to its text. A file name is a
  plain name matching `[A-Za-z0-9_][A-Za-z0-9_.-]*`: no directories, text only.
  A single-file tool has an empty bundle. `content_hash` covers the bundle
  files in name order; for an empty bundle it is the previous hash.
- **Lifecycle.** Every operation that derives a version from another copies the
  bundle: creating a draft from a version (unless the command sets
  `bundle_files`), saving a draft, request-changes, publish and rollback.
- **Editor and API (D6).** The editor boot response carries the selected
  version's `bundle_files`. The editor and version views list the entrypoint
  first, then every bundle file, and let a contributor view, edit and diff each
  one. Create-draft and save requests send the whole map; an omitted
  `bundle_files` keeps the bundle the version started from, and a sent map
  replaces it and recomputes `content_hash`. The local working copy, its
  checkpoints and its restore diffs carry the map.
- **Sandbox (D6).** A sandbox run sends the editor's unsaved bundle map in its
  snapshot; the snapshot size limit counts the serialized map.
  `sandbox_snapshots.bundle_files` (JSONB, not null, default `{}`, migration
  `e3b7a1c5d9f2`) stores it, and the run executes that edited bundle. Later
  sandbox actions on the same snapshot run the stored snapshot bundle, not the
  saved draft. Bundle file names are validated where a snapshot or version is
  created; execution uses the stored map as given.
- **Script bank.** An entry whose `source_filename` is `<tool>/tool.py` is a
  bundle: the seeder stores `tool.py` as the entrypoint and every other file
  directly in `<tool>/` as the bundle, and reseeds when the bundle changes.
- **Runner.** The request factory writes the bundle to `/work/bundle/<name>`
  beside the unchanged `/work/script.py`. The runner loads `/work/script.py` as
  the package `tool_script` whose only submodule search location is
  `/work/bundle`, and registers it in `sys.modules`. `sys.path` is unchanged:
  `/work`, `input/` and the other work files stay unimportable, and only the
  tool's own bundle is reachable, through relative imports
  (`from .roster import parse_roster_file`).
- **Tool code.** Bundle modules import each other only with relative imports,
  which mypy resolves in the repository through the namespace package
  `skriptoteket.script_bank.scripts.<tool>`. A data file is read by a bundle
  module with `Path(__file__).with_name(...)`, never by the entrypoint, whose
  `__file__` is `/work/script.py`.

## Non-Decisions

- No UI to create, rename or delete bundle files: contributors edit the files
  a version already has, and cannot turn a single-file tool into a bundle from
  the UI.
- No subdirectories, binary data files or code shared between tools.

## Consequences

- The four tools ship as bundles with every file under 500 lines; their
  outputs through the real runner are unchanged.
- Each version row stores its full bundle, so publish and rollback copies
  duplicate it: 8–20 KB per version for the four current bundles.
- A contributor sees and edits every file of a bundled tool; an editor save
  stores the edited entrypoint and sibling files as one new version.
- Sandbox snapshots created before migration `e3b7a1c5d9f2` hold an empty
  bundle, so their later actions run without the saved version's bundle.
- Deploy order: the `skriptoteket-runner` image must be rebuilt before bundled
  versions are seeded. The previous runner loads `/work/script.py` as a plain
  module, so a bundle's relative imports fail there. The new runner runs
  single-file tools unchanged, so rebuilding the runner first is safe.
