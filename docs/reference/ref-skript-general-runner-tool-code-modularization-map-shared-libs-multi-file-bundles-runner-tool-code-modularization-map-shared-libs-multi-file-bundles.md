---
type: reference
id: REF-SKRIPT-GENERAL-runner-tool-code-modularization-map-shared-libs-multi-file-bundles
title: Runner/tool code modularization map (shared libs + multi-file bundles)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-runner-tool-code-modularization-map
summary: Runner/tool code modularization map (shared libs + multi-file bundles)
---

## Overview

This document maps two complementary, long-term goals for Skriptoteket tool scripts:

1) **Direction A — shared runner libraries (platform-owned):** reusable Python modules shipped with the runner image.
2) **Direction B — multi-file tool code bundles (tool-owned, per version):** each tool version can contain multiple
   `.py` files (and optional resources), executed via an explicit entrypoint.

This is a **pre-ADR / pre-PRD** mapping doc: it enumerates decisions, constraints, risks, and a sequencing plan. It does
not choose final designs.

## Facts And Semantics

No separate facts and semantics is stated in the source.

### Source: Current state (as of 2026-01-20)


### Tool code representation

- A tool version stores a single Python code blob (`ToolVersion.source_code`) plus an `entrypoint` function name.
- The backend builds a runner workdir archive with:
  - `/work/script.py` (the tool’s `source_code`)
  - `/work/memory.json` (settings/memory)
  - `/work/input/` (uploaded user files; multi-file input is supported)
- The runner loads `/work/script.py` and calls `getattr(module, entrypoint)(input_dir, output_dir)`.

### Shared runner modules

- The runner image already ships small helper modules under `runner/` (e.g. `skriptoteket_toolkit`, `pdf_helper`,
  `tool_errors`) importable from tool scripts.
- These are **platform-controlled**, but the current compatibility/ownership policy is implicit (not formalized).

### Editor/AI coupling

- The admin editor and AI endpoints assume a fixed set of “virtual files” (`tool.py`, `entrypoint.txt`,
  `settings_schema.json`, `input_schema.json`, `usage_instructions.md`).
- “Active file” for AI and edit-ops is a `Literal[...]` union over those virtual file IDs (hard-coded).

### Source: Direction A — shared runner libraries (platform-owned)


### Goal

Keep tool scripts small and maintainable by moving **generic, reusable logic** into runner-shipped modules that tool
authors can import.

This direction is compatible with both:

- single-file tools (today), and
- multi-file tool bundles (Direction B).

### What belongs in shared libs (examples)

Strong candidates:

- Stable env parsing helpers (inputs, action payload, memory/settings).
- UI-contract convenience builders (typed/dict builders with safe defaults).
- Common file patterns that are not tool-specific (e.g. safe CSV reading helpers, common validation helpers).
- “Safe errors” helpers (user-facing errors, deterministic error summaries).

Non-candidates (avoid unless explicitly approved):

- Tool-specific domain logic (belongs in the tool bundle).
- “Too helpful” wrappers that hide important contract constraints (risk: harder debugging + weaker portability).
- Large transitive dependency surfaces without a clear governance story.

### Packaging options (runner image)

We should decide early whether shared libs are:

1) **plain modules** on `sys.path` (current pattern: `runner/*.py`), or
2) an **installed Python package** inside the runner venv (cleaner versioning + testing, clearer import story).

Either can work; the key is to make the compatibility surface explicit and testable.

### Compatibility + governance policy (needs to exist before broad adoption)

Minimum policy elements to define before scaling shared-lib usage:

- **Ownership:** who can change shared libs, and how changes are reviewed.
- **Versioning:** how we communicate breaking changes (ideally a version string exposed to scripts).
- **Deprecation:** how long old APIs remain available and how migration is communicated.
- **Testing:** contract tests that lock expected behavior for the shared-lib API surface.
- **Docs:** one stable reference entrypoint for tool authors (the KB + runner README should match reality).

### Primary risks

- **Global blast radius:** runner image changes affect all tools immediately (unless image is pinned).
- **Unbounded surface area:** “just add one more helper” can turn into a large, unstable API.
- **Security/perf drift:** shared libs may accidentally widen allowed patterns or create slow defaults.

### Source: Direction B — multi-file tool code bundles (tool-owned, per version)


### Goal

Enable tool authors to keep complex tools maintainable by splitting code into multiple `.py` files (and optional
resource files), while preserving:

- reviewability (diffs),
- determinism (hashing, normalized storage),
- runner isolation (no network),
- and tool governance workflows (draft → review → publish).

### Key principle: isolate tool code from user uploads

The runner must never treat uploaded user files as importable modules. Tool code must live in a dedicated directory
that is the only new `sys.path` entry.

### Proposed conceptual model (not final)

#### Tool version data model (domain-level)

- `entrypoint`: explicit module + callable (e.g. `tool.main:run_tool`).
- `files`: list of `{path, content}`:
  - Python: `tool/**/*.py`
  - Optional resources: `tool/resources/**` (e.g. `.json`, `.md`, templates)

Domain invariants (examples):

- Paths are relative, normalized, and must not escape the bundle root.
- Max file count and max total bytes (limits must be settings-driven).
- Deterministic ordering and deterministic hashing across the full bundle.

#### Runner filesystem layout

Example layout inside the runner workdir:

```
/work/
  tool/
    __init__.py
    main.py
    helpers/
      __init__.py
      parse.py
    resources/
      prompt.md
      schema.json
  input/            # user uploads (not importable)
  output/           # artifacts
  memory.json
  result.json
```

#### Runner execution model

High-level behavior:

- Add `/work` (or `/work/tool-root`) to `sys.path` so imports like `import tool.helpers.parse` work.
- Import the entrypoint module and resolve the callable.
- Call the same function signature as today: `func(input_dir: str, output_dir: str)`.

### Editor/AI implications (largest scope)

Multi-file tool bundles require a shift from “virtual files as a fixed enum” to “editor-managed file set”:

- UI: file tree/tabs, create/rename/delete, per-file dirty state, per-file diff.
- Persistence: working copy and checkpoints become a **map of files**, not one blob.
- Lint/intelligence: start with per-file syntax + entrypoint checks; optionally grow into cross-file signals.
- AI: `active_file` must become a general file path (not a `Literal[...]` union); prompt budgeting needs deterministic
  file-selection rules (active file + selected related files, or user-chosen set).

### Migration strategy (required; avoid long-lived dual paths)

To honor “no legacy support/shims”, multi-file implementation should:

- add a migration that converts all existing tool versions from `source_code` → `files=[tool/main.py]` and rewrites the
  entrypoint format if needed
- remove the old single-blob column and old code paths once migration is complete

### Primary risks

- **Scope explosion in the editor:** multi-file UX + working copy + compare + AI context all expand.
- **Review complexity:** reviewers need good defaults (what file opens, what diffs are shown).
- **Security pitfalls:** import path hijacking if the wrong directories land on `sys.path`.
- **DB growth:** storing N files per version increases DB size; limits and retention must be explicit.

### Source: How Directions A and B fit together (recommended framing)


- Direction A provides a **stable “standard library”** for Skriptoteket tool authors.
- Direction B provides **tool-local modularity** when a tool is inherently complex or needs reusable internal modules.
- A tool bundle should prefer importing shared libs for cross-tool patterns, and use its own modules for tool-specific
  complexity.

Rule of thumb:

- Shared libs: “many tools need this, and it’s stable”.
- Bundle modules: “only this tool needs this, or it evolves rapidly”.

### Source: Pre-ADR decision checklist


Before writing ADRs/PRDs, we should explicitly decide:

### Shared runner libs (Direction A)

- What is the allowed surface area? (small toolkit only vs broader standard library)
- Packaging choice: raw modules vs installed package.
- Compatibility policy: versioning/deprecation/testing guarantees.
- Release cadence: how runner image updates are rolled out and pinned.

### Multi-file bundles (Direction B)

- Entrypoint format: `module:function` (recommended) vs other encodings.
- Bundle root naming: `tool` package name and how we prevent import collisions.
- Allowed file types + size limits.
- Editor UX scope for v1 (MVP): minimal file tabs vs full file tree + rename/delete.
- AI context rules: which files get included by default and how budgets apply.

### Source: Suggested implementation sequencing (roadmap)


This sequencing keeps value flowing while containing blast radius:

1) **Harden Direction A first (small, high leverage):**
   - formalize shared-lib compatibility policy
   - add runner contract tests for toolkit behavior
   - expand the toolkit only where it clearly replaces repeated tool boilerplate
2) **Introduce Direction B backend+runner support next (no big editor UX yet):**
   - new storage model + runner bundle execution path
   - migration from single-file versions
   - keep editor UI “single main file” initially if needed for transition, but plan removal of the old schema quickly
3) **Ship full multi-file editor UX + AI file-path refactor:**
   - dynamic file sets, diffs, working copy, AI active_file as path
4) **Optimize storage/retention and scale:**
   - enforce bundle size budgets
   - evaluate compression or external storage if DB size becomes a constraint

### Source: Candidate ADR/PRD breakdown (for later)


Potential ADR set (suggested split):

- **ADR: Shared runner libraries compatibility policy** (Direction A)
- **ADR: Tool code bundles + entrypoint resolution** (Direction B, backend+runner contract)
- **ADR: Tool editor multi-file UX + AI file context model** (Direction B, frontend+LLM protocol)

Potential PRD scope (suggested):

- A “Tool authoring vNext” PRD that explicitly covers:
  - multi-file tool code authoring
  - governance/review ergonomics for multi-file diffs
  - migration/compat rules for existing tools
  - runner-image update policy for shared libs

## Decisions And Interpretation

No separate decisions and interpretation is stated in the source.
