---
type: pr
id: PR-0075
title: "Textbook corpus — multi-agent manual restoration and verification workflow"
status: done
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-22-01"
tags: ["data", "quality", "manual-review"]
acceptance_criteria:
  - "Semantically important changes are applied through issue-scoped manual patch files, not direct bulk rewrites."
  - "Each manual patch has source references, rationale, and verifier approval metadata before apply."
  - "Patch application is deterministic and reversible."
---

## Problem

The most important textbook corruption cannot be solved safely by script alone. We need real manual labor with strong controls.

## Goal

Establish a multi-agent manual restoration lane that is auditable, conflict-safe, and meaning-preserving.

## Non-goals

- No one-shot full-file manual rewrites.
- No self-approval (same agent cannot author and verify the same patch).

## Implementation plan

1. Define issue packet schema and assignment strategy (non-overlapping ranges/IDs).
2. Define manual patch schema (`manual_fixes/*.yaml`) with provenance fields.
3. Implement verifier workflow and deterministic apply order.
4. Add rejection/rework loop for disputed patches.
5. Emit restoration report with accepted/rejected patch counts.

## Test plan

- Schema validation tests for patch files.
- Apply/revert determinism tests.
- Simulated conflict tests to verify non-overlap enforcement.

## Implementation notes (2026-03-04)

1. Added manual restoration workflow script:
   - `scripts/build_textbook_corpus_manual_restoration_workflow.py`
   - Subcommands:
     - `generate-packets`
     - `validate-patches`
     - `apply-patches`
2. Added patch/packet contracts:
   - Deterministic issue IDs and packet IDs.
   - Patch YAML schema with required provenance/review fields.
   - Approval rule enforced: no self-approval (`author != verifier` for approved patches).
3. Added deterministic conflict guards:
   - Duplicate issue IDs across files are invalid.
   - Duplicate patch IDs across files are invalid.
   - Duplicate line numbers across approved patches fail apply.
   - `expected_original` mismatch fails apply (protects against drift).
4. Added tests:
   - `tests/unit/scripts/test_build_textbook_corpus_manual_restoration_workflow.py`
   - Coverage includes packet generation, self-approval rejection, deterministic apply, and conflict blocking.
5. Added CLI alias:
   - `pdm run textbook-corpus-manual`
6. Executed on Kemi manual queue:
   - Input queue:
     `.artifacts/textbook_corpus/mechanical-kemi/ledgers/Syntes 1 - hela boken (1).full_ocr.manual-queue.jsonl`
   - Workflow output:
     `.artifacts/textbook_corpus/manual-kemi`
   - Results:
     - `generate-packets`: `generated_packets=8`, `issues=63`
     - `validate-patches`: `validated=63`, `valid=63`, `invalid=0`, `cross_file_errors=0`
     - `apply-patches` (all templates still `proposed`): `applied=0`, `failures=0`
     - Reversibility evidence:
       `input_sha256 == output_sha256 == 5c09b366464b3f8472f12e6d508cbd48fe19a1e5093210544044d03d5c5c7196`

## Rollback plan

- Revert applied manual patch artifacts from this slice.
- Rebuild from mechanical baseline and patch queue.
