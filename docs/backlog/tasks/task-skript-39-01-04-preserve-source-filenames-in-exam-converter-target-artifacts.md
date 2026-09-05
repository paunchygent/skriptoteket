---
type: task
id: TASK-SKRIPT-39-01-04
title: Preserve source filenames in Exam Converter target artifacts
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-09-05'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: independent-reviewer
  decided_at: '2026-09-05'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent review approved the source-derived PDF/QTI naming vertical after maximum-length outer-bundle and Vault-collision repairs plus RFC 5987 download-header handling; reviewed merge 3a1b7239 was deployed to Hemma and public job fc587793-3e9a-4cb6-9ba1-915034354211 proved the exact Unicode source-derived filenames and download headers.
task_kind: story
acceptance_criteria:
  - PDF and QTI artifacts downloaded or saved to Mina filer use sanitized filenames derived from the original uploaded DigiExam filename across first-pass and correction-replay paths
story: ST-SKRIPT-39-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Give every Exam Converter PDF and QTI target a backend-authoritative filename
that identifies its uploaded DigiExam source. Remove the final `.dxe` suffix
from the sanitized upload name and emit `<source stem> - Exam.net.pdf` and
`<source stem> - QTI.zip`.

Apply the same names to first-pass artifacts, correction replay, authenticated
and public downloads, and authenticated Mina filer saves. Truncate only the
source stem when required to keep the complete filename within 255 characters.
Retain existing Mina filer collision disambiguation.

Keep artifact keys, content types, bytes, outer bundle naming, bundle-internal
entry names, and QTI validation bindings unchanged. The frontend continues to
consume the producer-owned manifest filename without reconstructing it.

## Contract Inputs

- `ST-SKRIPT-39-01` and its in-process DigiExam-to-Exam.net artifact vertical.
- Existing preserved `source_filename`, source-derived outer bundle filename,
  named-artifact manifest, authenticated/public download routes, and shared
  Vault save service.
- Existing filename sanitization and Vault collision-disambiguation behavior.
- Retained plan:
  `.orchestration/context/sessions/01a071b4-b080-731c-8d40-1a77373ad9e0/evidence/planning/TASK-SKRIPT-39-01-04/plan.md`.

## Core Vertical And Performance

1. The upload filename remains the stored source-filename authority.
2. Named PDF and QTI artifacts derive their filenames once from that source.
3. First-pass and replay manifests expose those names unchanged.
4. Authenticated and public downloads use the manifest names; authenticated
   Mina filer saves persist the same names with existing collision handling.

Filename derivation is constant-time, performs no extra I/O, and introduces no
provider or LLM work.

## Validation

- Unit-test spaces, Unicode, multiple dots, uppercase `.DXE`, and names long
  enough to require source-stem truncation while preserving target suffixes.
- Prove first-pass and correction-replay manifests use source-derived PDF and
  QTI names without changing artifact bytes or bundle-internal entry names.
- Prove authenticated and public download headers use the source-derived names.
- Prove Mina filer saves use the same names and retain collision
  disambiguation.
- Run focused backend tests, `pdm run lint`, and `pdm run typecheck`.
- Run focused frontend tests only if frontend code changes.
- Close with `pdm run handoff-validate`, `pdm run docs-validate`, and
  `git diff --check`.

## Stop Conditions

- Stop if the stored source filename is unavailable or cannot be sanitized.
- Stop if either result exceeds 255 characters or loses its complete fixed
  target suffix.
- Stop if the change alters target bytes, artifact keys, outer bundle naming,
  bundle-internal entry names, or QTI validation bindings.
- Stop if any consumer adds an independent filename rewrite.

## Closeout Evidence

- Implementation commit `aab1031b` was independently approved and merged to
  `main` as `3a1b7239`.
- Focused filename, producer/replay, authenticated/public download,
  Content-Disposition, Mina filer save/collision, and shared naming tests passed:
  35 tests. Repository lint, docs validation, handoff validation, and
  `git diff --check` passed. Typecheck retained exactly the unrelated existing
  10-error `script_bank` baseline; frontend typecheck passed.
- Hemma deployed `3a1b72390300d97245c3cac7e174bdff0a74103f`; web and worker
  were healthy, migrations completed, the seating-export readiness gate passed,
  and public `/healthz` returned HTTP 200.
- Public production job `fc587793-3e9a-4cb6-9ba1-915034354211` used a
  disposable synthetic keyed source named `Samhällskunskap slutprov.DXE`. It
  completed without a teacher file or provider work, exposed
  `Samhällskunskap slutprov - Exam.net.pdf` and
  `Samhällskunskap slutprov - QTI.zip`, and returned matching RFC 5987 download
  headers with non-empty artifacts.
- Retained proof lives under session
  `01a071b4-b080-731c-8d40-1a77373ad9e0` at
  `evidence/live/TASK-SKRIPT-39-01-04/production/`; command captures `0001`–`0006`
  record lint, focused tests, typecheck baseline, docs/handoff validation, and
  production proof.
- Residual risk: the pre-existing generic outer-bundle download route still uses
  a quoted filename header for quote-containing source names. That route and
  bundle filename behavior are outside this PDF/QTI target-artifact contract.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------------ |
| T1  | PDF and QTI filenames preserve the sanitized upload stem and append ` - Exam.net.pdf` or ` - QTI.zip`.                         |
| T2  | One backend named-artifact policy governs first-pass, replay, authenticated/public downloads, and Mina filer saves.            |
| T3  | Long names truncate only the source stem; the complete filename stays within 255 characters and keeps its fixed target suffix. |
| T4  | Existing Vault collision disambiguation remains unchanged.                                                                     |
| T5  | Artifact identity, bytes, outer bundle naming, bundle-internal names, and QTI validation bindings remain unchanged.            |
| T6  | The change adds no provider work, I/O, database migration, or frontend filename reconstruction.                                |
