---
type: pr
id: PR-0073
title: "Textbook corpus — governance, immutable snapshot, and job reconciliation"
status: done
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

## Implementation notes (2026-03-04)

1. Added baseline/reconciliation script:
   - `scripts/build_textbook_corpus_baseline.py`
   - Copy-only behavior: preserve all original files, never mutate source artifacts.
   - Snapshots manifests, source files, local outputs, reconciliation payloads, and checksums.
2. Added unit tests:
   - `tests/unit/scripts/test_build_textbook_corpus_baseline.py`
   - Coverage includes:
     - local snapshot copying,
     - timeout/running reconciliation to terminal state,
     - fetched succeeded artifact when local output is missing,
     - missing API key fallback behavior.
3. Added CLI alias:
   - `pdm run textbook-corpus-baseline`
4. Executed against Kemi corpus:
   - Source: `/Users/olofs_mba/Documents/Repos/html_to_pdf_handout_templates/Kemi`
   - Output: `.artifacts/textbook_corpus/kemi-baseline`
   - Reconciliation summary:
     - `entries_total=5`
     - `status_succeeded=2`
     - `status_failed=1`
     - `status_canceled=2`
     - `reconcile_attempted=1`
     - `fetched_artifact_count=1`
   - Verified drift closure:
     - `sir_convert_a_lot_manifest_full_ocr.json` entry transitioned from manifest `running`
       to reconciled `succeeded` and fetched output to:
       `raw/outputs/fetched/jobv2_9ae51f803055434caba2f2de26.md`
5. Added immutable-output safety guard:
   - `scripts/build_textbook_corpus_baseline.py` now fails closed if `--output-dir`
     already exists and is non-empty.
   - Explicit override requires `--allow-overwrite`.
   - Unit test:
     `tests/unit/scripts/test_build_textbook_corpus_baseline.py::test_build_baseline_refuses_non_empty_output_without_allow_overwrite`

## Rollback plan

- Remove baseline/reconciliation artifacts created by this slice.
- Reconstruct from source manifests and job IDs.
