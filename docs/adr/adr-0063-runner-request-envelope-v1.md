---
type: adr
id: ADR-0063
title: "Runner request envelope v1 (request.json)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-20
updated: 2026-01-20
links: ["EPIC-19", "ADR-0024", "ADR-0031", "ADR-0039"]
---

## Context

Runner-based tools currently receive JSON payloads via environment variables:

- `SKRIPTOTEKET_INPUTS`
- `SKRIPTOTEKET_INPUT_MANIFEST`
- `SKRIPTOTEKET_ACTION`

This is fragile (size limits, quoting/encoding issues) and splits the tool author mental model across multiple
channels.

We also need to evolve the request surface to include first-class file references (session/vault) and maintain a
single, stable DX/UX contract.

## Decision

### 1) `/work/request.json` is the runner request envelope

The platform MUST write a single UTF-8 JSON file at:

- `/work/request.json`

This file is the source of truth for runner inputs, action payload (if any), and the file manifest.

### 2) Replace env-var JSON payload transport (no migration path)

The platform MUST stop setting the JSON payload environment variables for runner containers:

- `SKRIPTOTEKET_INPUTS`
- `SKRIPTOTEKET_INPUT_MANIFEST`
- `SKRIPTOTEKET_ACTION`

Tool scripts MUST use `skriptoteket_toolkit` helpers to read the envelope and must not parse `os.environ` directly.

### 3) Request schema (v1)

Minimal shape:

```json
{
  "schema_version": 1,
  "inputs": { "values": { "any": "json" } },
  "action": { "action_id": "string", "input": { "any": "json" }, "state": { "any": "json" } },
  "files": [{ "name": "file.pdf", "path": "/work/input/file.pdf", "bytes": 123, "ref": "session:file.pdf" }]
}
```

Rules:

- `action` is `null` for initial runs.
- For action runs, `action.state` is the server-owned session state snapshot for this turn.
- `files[]` is the canonical manifest for all staged inputs for this run.
- Every `files[].path` MUST be under `/work/input/` and MUST be safe to open by the tool.
- `files[].ref` is optional in v1, but is expected to become required for session/vault sources (see ADR-0064).

`memory.json` remains a separate platform-owned file (existing behavior).

### 4) DX / UX gold standard (invariants)

Tool scripts should be able to follow a single, stable model:

- Tools discover inputs via the toolkit + the manifest only.
- Tools never need to know whether a file came from upload/session/vault; all inputs are just staged files under
  `/work/input/`.
- Tools never need to handle platform file paths outside `/work/input/` for inputs. File identity across turns uses
  `FileRef` values, and the platform resolves/stages refs into `/work/input/`.

## Consequences

- Request parsing becomes predictable and avoids env-var size/quoting issues.
- Enables cohesive evolution of input identity (FileRefs) without new parallel payload channels.
- Requires coordinated breaking cutover: platform + runner toolkit + script bank/templates must be upgraded together.
