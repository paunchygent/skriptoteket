---
type: adr
id: ADR-SKRIPT-0090
title: Skriptoteket-owned exam conversion boundary with Sir Convert generic extraction
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-28'
status: accepted
deciders:
- user-lead
links:
  governing:
  - EPIC-SKRIPT-39
  - ADR-SKRIPT-0066
---

## Context

ADR-SKRIPT-0066 (proposed) makes Sir Convert-a-Lot v2 the canonical conversion
engine and forbids new conversion engines inside Skriptoteket. Operating the
Exam Converter lane across that boundary has produced documented coupling
cost: ten mirrored schema-version constants, a recorded hard
`digiexam_migration_bundle_v2` to `v3` contract break with no shim, and a
still-proposed cross-repo handoff contract, while the exam domain itself is
pure-Python logic whose only infrastructure needs are pymupdf, weasyprint,
standard-library packaging, and an OpenAI-compatible HTTP endpoint — none of
the heavy OCR, layout-model, or GPU stack that motivated the central engine.
EPIC-SKRIPT-39 records the accepted planning contract for porting the domain.

## Decision

The exam-conversion domain — source parsing (DigiExam `.dxe`, Word, PDF), the
source-neutral exam authoring IR, advisory answer-key enrichment behind
teacher review, and export to the proven Exam.net QTI contract, the
Exam.net-profile PDF, and DOCX — is Skriptoteket-owned and runs inside the
Skriptoteket backend.

Sir Convert-a-Lot remains the canonical service for heavy document
conversion (OCR, tables, formulas, layout models) and speech-to-text. The
exam lane consumes it only through the generic text-extraction contract for
scanned or layout-hard sources. Exam-specific cross-repo schemas and client
coupling retire with the EPIC-SKRIPT-39 cutover.

This narrows ADR-SKRIPT-0066's "no new conversion engines inside
Skriptoteket" rule: that rule continues to govern general document
conversion; it no longer covers the exam-conversion domain.

## Non-Decisions

- No general document-conversion engine moves into Skriptoteket; the
  ST-37-04 simple-conversion carve-out is unchanged.
- No exam-creator authoring UI is authorized; that is a later epic.
- No change to Sir Convert-a-Lot's ownership of heavy OCR, GPU runtime, or
  STT lanes.
- No student-response grading capability.

## Consequences

- Skriptoteket gains the exam domain code, its tests, and its docs corpus;
  the common exam path loses one network hop and one deploy dependency.
- The cross-repo exam schema surface (mirrored constants, migration-bundle
  contract) is retired with the cutover; remaining coupling is the generic
  extraction contract only.
- The Hemma Qwen answer-key sidecar becomes a retirement candidate; its
  retirement is governed cleanup inside EPIC-SKRIPT-39, not a silent side
  effect.
- Sir Convert-a-Lot's exam lane retires lane-by-lane behind parity proof;
  until then both implementations exist and the parity gate is the only
  accepted reason for that duplication.
- Follow-up work requiring separate backlog authority: EPIC-SKRIPT-39
  stories, sir-convert-a-lot exam-lane retirement tasks, and the sidecar
  retirement.

## Proposed Amendment Pointer (not accepted)

- Proposed ADR-SKRIPT-0091 would narrow only the "No exam-creator
  authoring UI is authorized" non-decision above to the native editable
  exam workspace slice (ST-SKRIPT-39-04). Until ADR-SKRIPT-0091 is
  accepted, that non-decision stands unchanged; every other section of
  this ADR is unaffected.
