---
type: task
id: TASK-SKRIPT-39-01-02
title: Preserve decimal scores and recover missing DigiExam titles and images
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-09-04'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Valid decimal point values pass unchanged through the neutral exam model into QTI without warnings, while a missing question title uses the existing deterministic fallback and unresolved DigiExam image references produce a valid visible per-item placeholder; both recoverable source defects emit simple Swedish review information instead of failing the conversion
story: ST-SKRIPT-39-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the observed DigiExam ingestion boundaries without broadening the
exam-conversion contract. Valid positive fractional point values pass unchanged
through the source-neutral exam model into PDF and QTI output and emit no
warning. A visible prompt image position that cannot bind to a valid embedded
image remains in the question as a visible QTI-valid placeholder instead of
failing the conversion.

A missing or blank DigiExam question title uses the existing deterministic
`Question N` fallback and remains exportable. The repair emits one item-bound,
non-blocking warning telling the teacher that a title was generated and should
be reviewed before use.

The missing-image repair emits one item-bound, non-blocking warning from a
reusable Swedish message template. It tells the teacher that the source
contained an image position but no usable image and that the image must be
added before the exam is used. The authenticated question view shows the
item-specific message and the existing report view summarizes affected
questions. QTI and PDF carry the placeholder without an invalid image resource
or manifest reference.

This task does not change missing scores, unknown item types, malformed
alternatives or gaps, unreferenced image payloads, answer-key policy, or any
other parser behavior. Unknown item types are owned by `TASK-SKRIPT-39-01-03`.
This task does not add an LLM repair path.

## Contract Inputs

- `ST-SKRIPT-39-01`, `EPIC-SKRIPT-39`, and the existing Exam.net QTI 2.1
  package contract.
- QTI 2.1 outcome semantics: `SCORE`, `MAXSCORE`, and numeric maximums support
  float values; fractional source points therefore require preservation rather
  than rounding.
- Production reproductions on 2026-09-04: one supplied `.dxe` failed before
  enrichment on `maxScore: 10.5`; the other completed six provider requests
  and then failed on an unresolved prompt image in item 11. Local
  counterfactuals isolated those respective boundaries.
- Retained plan:
  `.orchestration/context/sessions/01a06bde-e127-7042-912b-d492fb6c00de/evidence/planning/TASK-SKRIPT-39-01-02/plan.md`.

## Core Vertical And Performance

The integrated vertical is the existing product path:

1. The DigiExam parser accepts a valid fractional `maxScore` and identifies an
   unresolved visible prompt image or missing title without blocking the item
   or exam.
2. Parser contracts, source-neutral and effective IR, correction/replay
   overlays, fingerprints, and JSON artifacts preserve the fractional point
   value and the item-bound image warning.
3. PDF semantics and QTI item contracts preserve fractional points; QTI float
   serialization, response mappings, maximum score, and multi-gap point
   allocation remain numerically consistent.
4. PDF and QTI projections render the same visible missing-image placeholder
   and omit every unresolved image resource.
5. Stored review artifacts project the non-blocking warning to the existing
   authenticated question and report views while target artifacts remain
   exportable.

Both repairs are deterministic and linear in existing item/image traversal.
They make no provider call, enqueue no extra enrichment work, and add no
material performance concern.

## Validation

- Add minimal synthetic regression inputs for the three source shapes; do not
  commit the supplied teacher files.
- Focused domain tests prove fractional scores survive parser, IR,
  correction/replay, fingerprint/artifact serialization, PDF, QTI response
  mapping, maximum score, and gap allocation without a warning or rounding.
- Focused image tests prove unresolved visible image positions across parser,
  PDF, QTI package/manifest validation, and review artifacts become the same
  item-bound non-blocking placeholder warning while valid images remain
  unchanged.
- Focused parser and projection tests prove a missing or blank title becomes
  the stable `Question N` fallback, carries an item-bound non-blocking Swedish
  review warning, and remains valid in PDF, QTI, and review artifacts.
- Focused frontend tests assert the reusable Swedish item message and report
  summary through visible text rather than snapshots.
- Run the affected backend tests, `pdm run lint`, and `pdm run typecheck`.
- Run the affected frontend tests, `pdm run fe-type-check`, `pdm run fe-lint`,
  and `pdm run fe-build`.
- Exercise the authenticated product path through the HuleEdu browser-session
  ceremony: the unchanged decimal-score source succeeds without a point
  warning, and the unchanged missing-image source succeeds with the visible
  item placeholder and Swedish review information. Validate the generated QTI
  packages before any user-coordinated Exam.net import check.
- Close documentation with `pdm run handoff-validate`,
  `pdm run docs-validate`, and `git diff --check`.

## Implementation Evidence

- The final focused backend suite passed 149 tests across the complete exam-conversion domain and product handlers.
- The focused frontend projection suite passed 35 tests; frontend typecheck, lint, and production build passed.
- Repository lint, documentation validation, handoff validation, and diff whitespace validation passed. Full backend typecheck remains at the unrelated existing 10-error `script_bank` baseline.
- The authenticated local browser path converted both unchanged teacher files, accepted the existing answer-key suggestions, downloaded PDF and QTI artifacts, and validated both QTI packages. The fractional source preserved `10.5` in PDF and QTI. The bounded final question-11 proof showed the exact numbered warning, downloaded both artifacts through the authenticated API, confirmed the exact visible placeholder in PDF and QTI, and confirmed that QTI item 11 contains no unresolved image resource.
- Merge `066d51af` is deployed on Hemma. The canonical checkout matches that commit, production web and worker are healthy, public `/healthz` returns HTTP 200, and the running web image contains the exact placeholder copy.
- Teacher source files remain outside the repository. Exam.net import acceptance remains user-coordinated.

## Stop Conditions

- Stop if any layer rounds, truncates, or silently rewrites a valid fractional
  point value.
- Stop if the placeholder leaves an unresolved resource in QTI, makes the
  package invalid, hides which item needs repair, or blocks artifact export.
- Stop if Exam.net rejects an otherwise QTI-valid fractional score or
  placeholder package; report the target-specific mismatch before adding a
  target-only transformation.
- Stop for user direction if implementation requires changing any parser
  policy named out of scope above.
- Stop if either repair increases LLM/provider work.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                     |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Valid positive fractional point values are preserved end to end and emit no warning.                                                                                                      |
| T2  | A visible prompt image position without a usable embedded image becomes a visible QTI-valid placeholder and does not fail the item or conversion.                                         |
| T3  | The missing-image condition remains an item-bound non-blocking warning with simple reusable Swedish teacher text and an explicit add-the-image next action.                               |
| T4  | The authenticated question view shows the item message, the report summarizes affected questions, and PDF/QTI artifacts remain exportable with the placeholder.                           |
| T5  | Both repairs are deterministic and provider-free; no LLM-based repair, extra provider call, or extra enrichment job is introduced.                                                        |
| T6  | Other parser relaxations and unreferenced image-payload policy are outside this task; supplied teacher files remain uncommitted and minimal synthetic fixtures carry regression coverage. |
| T7  | A missing or blank question title uses the existing deterministic `Question N` fallback, emits an item-bound non-blocking Swedish review warning, and does not block export.              |
