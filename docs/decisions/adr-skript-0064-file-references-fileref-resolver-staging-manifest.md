---
type: adr
id: ADR-SKRIPT-0064
title: File references (FileRef) + resolver + staging manifest
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0064
---

## Context

### Source: Context

Today, “file identity” is implicit:

- tools assume inputs live at `/work/input/<name>`
- later steps pass file names through state manually
- there is no stable, platform-validated reference model for “pick a file from this session/vault”

This makes multi-step workflows brittle and pushes internal path conventions into tool scripts and UI.

## Decision

### Source: Decision



## Non-Decisions

The source does not provide a separate non-decisions section; no additional non-decisions is recorded.

## Consequences

### Source: Consequences

- Enables safe UI pickers for “files available in this session/vault” without path leakage.
- Eliminates tool-side branching on file source; tools operate on staged inputs under `/work/input/` only.
- Requires tightening session file storage semantics to support per-file promotion safely (avoid “replace all”
  footguns).

### Source: 1) `FileRef` is a stable, opaque string identifier (Option A)

A `FileRef` is a string with an explicit source prefix:

- `session:<name>` — session-scoped persisted file name
- `vault:<file_id>` — per-user vault file id (UUID)
- (optional later) `run:<run_id>:<artifact_key>` — run artifact addressing (not required for the initial foundation)

`FileRef` values are identifiers, not paths. The UI must never expose runner filesystem paths.

### Source: 2) The platform resolves refs and stages bytes into `/work/input/`

The platform MUST:

- validate each requested `FileRef` (grammar + authorization)
- load bytes from the source storage (session storage, vault storage)
- stage files into `/work/input/<safe_name>` for the run
- emit a deterministic manifest mapping `ref → /work/input/...` in the request envelope (`/work/request.json`)

Tools never “fetch” refs directly. Tools only read staged files from `/work/input/` and use refs for identity across
turns.

### Source: 3) Uploads are session refs immediately (single mental model)

Uploaded input files are session-scoped persisted files (ADR-0039). Therefore:

- uploaded files MUST be addressable as `session:<safe_name>` for the current `(tool_id, user_id, context)`
- the request manifest SHOULD include `ref` for uploaded files (not only for vault files)

### Source: 4) Resolver responsibilities (protocol-level)

The file ref resolver boundary must support:

- listing available refs for a `(tool_id, user_id, context)` without returning filesystem paths
- resolving a list of refs into staged run inputs under `/work/input/`
- returning the manifest entries required for tools to map refs back to local paths deterministically

### Source: 5) Promotions (hybrid semantics)

- Tools MAY request promotions from run artifacts → session files (required for multi-step workflows).
- Vault persistence is explicitly user-initiated (ADR-0059) and MUST NOT be tool-auto-triggered.

Both cases share the same security and validation model (path safety, access checks, quotas, and atomicity).
