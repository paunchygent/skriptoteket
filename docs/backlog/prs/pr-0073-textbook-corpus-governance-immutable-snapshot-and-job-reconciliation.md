---
type: pr
id: PR-0073
title: "Textbook corpus — governance, immutable snapshot, and job reconciliation"
status: ready
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-22-01"
tags: ["docs", "data", "operations"]
acceptance_criteria:
  - "A canonical raw corpus package is created with immutable inputs (PDF, raw markdown, manifests, job/result payload snapshots) and checksums."
  - "Manifest drift is reconciled: timed-out/running entries are re-queried by job_id and terminal state is persisted before downstream cleanup."
  - "Docs governance is in place for this track (epic/story/PR task chain with explicit no-silent-autofix policy)."
---

## Problem

Long-running conversion jobs can leave local manifests in non-terminal states even when the server later succeeds.
If cleanup starts from stale local state, provenance and trust break immediately.

## Goal

Create an immutable, reconciled baseline that downstream cleanup and manual restoration can safely build on.

## Non-goals

- No semantic cleanup yet.
- No RAG chunking/embedding yet.

## Implementation plan

1. Snapshot source artifacts and metadata into a deterministic corpus baseline layout.
2. Re-query relevant Sir Convert-a-Lot v2 job IDs and persist terminal status + result metadata.
3. Fetch missing succeeded artifacts from server where local output is absent.
4. Emit checksums + reconciliation report.
5. Document baseline contract and no-destructive-overwrite rules.

## Test plan

- Re-run reconciliation twice and verify idempotent outputs.
- Validate checksums file stability when sources are unchanged.
- `pdm run docs-validate`

## Rollback plan

- Remove baseline/reconciliation artifacts created by this slice.
- Reconstruct from source manifests and job IDs.
