---
type: adr
id: ADR-0059
title: "User file vault for reusable uploads"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-12
---

## Context

Users often re-upload the same input files. We already store run artifacts and session files, but there is no
user-scoped library for reusable inputs, and the runner remains network-isolated.

## Decision

- Add a user file vault with explicit save/delete controls.
- Persist file metadata in a new table (e.g., `user_files`) keyed by `(user_id, file_id)` with name, size, source, and
  storage path; enforce size caps and retention rules.
- Provide API endpoints to list, create (save), delete (soft), and restore vault files.
- In the tool run UI, allow selecting vault files as inputs (respecting `input_schema` file constraints).
- Allow users to save **run artifacts** into the vault via an explicit action (no auto-saving).
- Deletion is **soft delete**: set `deleted_at`, hide from pickers, and allow restore within a retention window.
- A background cleanup job purges soft-deleted vault files after the retention window expires.
- Retention window is configurable; default value TBD (do not hardcode yet).
- Selected vault files are staged into `/work/input/` at run time; UI never exposes internal filesystem paths.
- Vault access is strictly per-user unless a future sharing model is introduced.

## Consequences

- Reduces repeated uploads and enables workflows that reuse common inputs.
- Adds storage and lifecycle management responsibilities (retention, deletion, quotas), including copying artifacts
  into the vault storage namespace and running a purge job for soft-deleted files.
- Action-form selection of vault files can be added later with first-class file references (ST-14-24).
