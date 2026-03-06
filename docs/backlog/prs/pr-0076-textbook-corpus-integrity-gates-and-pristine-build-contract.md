---
type: pr
id: PR-0076
title: "Textbook corpus — integrity gates and pristine build contract"
status: done
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-22-01"
tags: ["data", "quality", "validation"]
acceptance_criteria:
  - "Pristine build is blocked if critical unresolved issues remain."
  - "Integrity validators cover section continuity, page-anchor continuity, task numbering continuity, and answer-key mapping coverage."
  - "Build outputs include machine-readable validation report and human-readable checklist."
---

## Problem

Without hard gates, a corpus can look clean but still be broken for retrieval and teaching use.

## Goal

Define and enforce deterministic quality gates that must pass before the corpus is considered pristine.

## Non-goals

- No embedding/vector ingestion in this slice.

## Implementation plan

1. Implement integrity validators with strict failure levels.
2. Define acceptance thresholds and unresolved-issue policy.
3. Produce `pristine` artifact only when validators pass.
4. Emit report outputs for audit and manual verification.
5. Add regression tests for validator behavior.

## Test plan

- Unit tests for each validator.
- End-to-end dry run from mechanical + manual patches to pristine build.
- Negative tests that ensure gate failures block promotion.

## Implementation evidence

Implemented:

- `scripts/build_textbook_corpus_integrity_gates.py`
- `tests/unit/scripts/test_build_textbook_corpus_integrity_gates.py`

Validation commands:

- `pdm run ruff check scripts/build_textbook_corpus_integrity_gates.py tests/unit/scripts/test_build_textbook_corpus_integrity_gates.py`
- `pdm run pytest -q tests/unit/scripts/test_build_textbook_corpus_integrity_gates.py`
- `pdm run python scripts/build_textbook_corpus_integrity_gates.py validate --input-markdown '.artifacts/textbook_corpus/manual-kemi/applied/Syntes 1 - hela boken (1).full_ocr.restored.md' --issue-ledger '.artifacts/textbook_corpus/mechanical-kemi/ledgers/Syntes 1 - hela boken (1).full_ocr.issue-ledger.jsonl' --manual-queue '.artifacts/textbook_corpus/manual-kemi/resolved-manual-queue.jsonl' --output-dir '.artifacts/textbook_corpus/integrity-kemi'`
- `pdm run python scripts/build_textbook_corpus_integrity_gates.py build-pristine --input-markdown '.artifacts/textbook_corpus/manual-kemi/applied/Syntes 1 - hela boken (1).full_ocr.restored.md' --issue-ledger '.artifacts/textbook_corpus/mechanical-kemi/ledgers/Syntes 1 - hela boken (1).full_ocr.issue-ledger.jsonl' --manual-queue '.artifacts/textbook_corpus/manual-kemi/resolved-manual-queue.jsonl' --output-dir '.artifacts/textbook_corpus/integrity-kemi'`

Observed runtime behavior:

- Validator emitted machine-readable artifacts under `.artifacts/textbook_corpus/integrity-kemi/reports/`.
- Full restored textbook now passes all critical gates (`critical=0`) with non-blocking warnings (`warning=10`).
- Pristine promotion succeeded and wrote:
  - `.artifacts/textbook_corpus/integrity-kemi/pristine/Syntes 1 - hela boken (1).full_ocr.restored.pristine.md`
  - `.artifacts/textbook_corpus/integrity-kemi/pristine/Syntes 1 - hela boken (1).full_ocr.restored.pristine-report.json`
- Manual restoration packet status is complete (`approved=63`, `proposed=0`) in `.artifacts/textbook_corpus/manual-kemi/validate-report.json`.

## Rollback plan

- Remove pristine/gate outputs from this slice.
- Keep prior restoration state and rerun after fixes.
