---
type: story
id: ST-19-02
title: "FileRef model + resolver + promotion plumbing (session + vault)"
status: ready
owners: "agents"
created: 2026-01-20
epic: "EPIC-19"
acceptance_criteria:
  - "Given a tool run session context, when listing available files, then the platform returns a stable list of FileRefs (no filesystem paths) for that session context."
  - "Given an action includes file refs, when executing, then the platform validates access and stages the referenced files into `/work/input/` and includes them in the request manifest."
  - "Given a tool requests promotion of run artifacts to session files, when the run finalizes, then the platform copies the artifacts to session file storage and exposes them as session FileRefs for subsequent actions."
  - "Given vault files exist (ST-14-36), when a run is started with selected vault FileRefs, then the same resolver stages them into `/work/input/` without a vault-specific code path."
dependencies:
  - "ADR-0039"
  - "ST-19-01"
ui_impact: "No (foundation APIs only)"
data_impact: "No (session promotion uses existing session_files storage; vault storage is in ST-14-36)"
---

## Context

Today, “file identity” is implicit:

- uploaded/session files are addressed by file name (and assumed `/work/input/<name>`)
- tools pass file names through state manually
- there is no stable, platform-validated reference model for “pick a file from this session/run/vault”

This makes multi-step workflows brittle and forces tools and UI to care about internal paths.

## Goal

Introduce a single, end-to-end `FileRef` concept that:

- is stable and user-safe (never a filesystem path),
- can be listed by the platform for UI rendering,
- can be validated and resolved by the platform into concrete staged files under `/work/input`,
- supports promotion targets (session now, vault later) without adding separate one-off pipelines.

## Notes

- This story is “plumbing only”; UI selection/rendering is done in ST-14-24 and ST-14-36.
- “No migration path”: file selection conventions that rely on raw paths should be removed once this is implemented.

## Proposed `FileRef` shape (initial)

- A `FileRef` is a stable string identifier with an explicit source prefix:
  - `session:<name>`
  - `vault:<file_id>` (implemented in ST-14-36)
  - (optional later) `run:<run_id>:<artifact_id>`

The platform is responsible for mapping `FileRef` → bytes → staged `/work/input/<safe_name>`.

## Implementation plan

1) Domain model + protocols

- Add a `FileRef` type and a resolver protocol that can:
  - list available refs for `(tool_id, user_id, session_context)`,
  - validate + resolve refs into staged input files for a run,
  - return a deterministic manifest mapping `ref → /work/input/...`.

2) Session files as a FileRef source

- Define session file refs as `session:<name>` where `<name>` corresponds to the persisted session file name.
- Adjust session file storage protocol semantics to support promotion safely (avoid “replace all” footguns).

3) Promotion primitives

- Add a platform-level “promote artifact → session file” operation:
  - source: run artifact (`run_id` + artifact id/path)
  - target: `(tool_id, user_id, session_context)` session file name
- Promotions must be validated (path safety + access checks) and must be atomic from a user perspective.

4) Runner integration

- Extend `/work/request.json` manifest to include a `ref` field per staged file (so tools can map file refs back to
  actual staged paths deterministically).

## Test plan

- Unit: resolver rejects invalid/unauthorized refs with actionable validation errors.
- Unit/integration: resolving a `session:*` ref stages the correct bytes into `/work/input` and manifests it.
- Unit/integration: promotion copies an artifact into session storage and it becomes resolvable as `session:*`.
