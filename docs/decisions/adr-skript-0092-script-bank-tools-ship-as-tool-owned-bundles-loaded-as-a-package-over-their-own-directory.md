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
status: proposed
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
  Editor and sandbox requests change only the entrypoint and keep the bundle.
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

- No editor or API surface for bundle files: the editor, version views and
  diffs show and edit the entrypoint only, and contributors cannot create
  bundles from the UI.
- No subdirectories, binary data files or code shared between tools.

## Consequences

- The four tools ship as bundles with every file under 500 lines; their
  outputs through the real runner are unchanged.
- Each version row stores its full bundle, so publish and rollback copies
  duplicate it: 8–20 KB per version for the four current bundles.
- An editor save of a bundled tool keeps the bundle it started from; a
  contributor sees only the entrypoint and cannot change sibling modules.
