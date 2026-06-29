---
type: review
id: REV-PR-0408
title: "Review: PR-0408 Exam Converter frontend design implementation alignment"
status: approved
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
reviewer: "ruthless_review_agent"
prs:
  - PR-0408
links:
  - ST-21-04
  - PR-0406
  - REV-PR-0406
  - docs/mockups/pr-0406-answer-key-review-small-screen/README.md
  - docs/mockups/pr-0406-answer-key-review-desktop/README.md
  - docs/reference/ref-exam-converter-ui-content-model-v1.md
  - /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md
---

## TL;DR

No blocking findings remain after the Task 374 remediation rereview. Sir Convert
now preserves keyed sibling advisory candidates without gating free-text/open-
writing rows, and Skriptoteket proves both preserved-pending and producer-
validation replay states without local review-state inference.

## Problem Statement

This review checks whether PR-0408 now aligns the authenticated Exam Converter
frontend with the governed desktop and small-screen answer-key review designs,
including the late product clarification that free-text/open-writing rows are
not gated answer-key review items and must not show warning status.

## Proposed Solution

The implementation keeps keyed closed-response review for MCQ/choice plus
Lucktext/gap-fill/open-cloze items, excludes open-ended rows from actionable
answer-key review state, preserves desktop and phone task surfaces, and renders
advisory accept/edit actions as the mockup's primary/secondary detail controls.

## Artifacts to Review

| Artifact | Focus |
|---|---|
| `docs/backlog/prs/pr-0408-st-21-04-exam-converter-frontend-design-implementation-alignment.md` | Updated acceptance, especially keyed closed-response versus open-ended no-key state |
| `docs/reference/ref-exam-converter-ui-content-model-v1.md` | UI content model and small/desktop mockup authority |
| `docs/mockups/pr-0406-answer-key-review-small-screen/README.md` and `index.html`/`styles.css` | Small-screen exact copy, state, and button treatment |
| `docs/mockups/pr-0406-answer-key-review-desktop/README.md` and `index.html`/`styles.css` | Desktop layout, detail actions, and symbolic navigation authority |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/digiexamIrQuestionReviewProjection.ts` | Open-ended follow-up non-actionability and keyed review type classification |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.ts` | Compact review-state mapping for open-ended versus keyed items |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts` | Adapter proof for Lucktext keyed review and open-ended exclusion |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts` | Mounted UI proof for free-text manual-key and unsupported-type regressions |
| `frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterAdvisoryAnswerKeyPanel.vue` | Advisory `Acceptera`/`Ändra` controls |
| `.artifacts/pr-0408-exam-converter-design-proof/20260629T174933Z/manifest.redacted.json` | Fresh browser/PNG proof after the free-text and button-treatment remediation |
| `docs/backlog/reviews/review-pr-0408-exam-converter-design-proof-helper-remediation.md` | Separate proof-helper approval boundary |

## Key Decisions

| Decision | Rationale | Approve? |
|---|---|---|
| Treat open-ended/free-text rows as non-gated for answer-key review. | PR-0408 now explicitly says these rows must not ask for facit, show warning status, or block `Kontrollera facit`. | Yes |
| Keep Lucktext/gap-fill/open-cloze keyed and actionable. | The latest contract clarifies that keyed closed-response review includes Lucktext/gap-fill/open-cloze, while only open-ended/free-text is excluded. | Yes |
| Use local mockup-style primary/secondary detail controls for advisory accept/edit. | The mockup source defines `Acceptera`/`Ändra` as local primary/secondary controls, not the app's shadowed CTA primitive. | Yes |
| Require fresh visual proof after the parent patch before final closeout. | The retained proof manifest postdates the free-text and button-treatment remediation and captures desktop plus phone surfaces; the Task 374/PR-0408 rereview now adds automated proof for the production post-accept sibling-candidate replay failure. | Yes |

## Review Checklist

- [x] Governing PR-0408 authority and design references were checked.
- [x] Free-text/open-ended compact review-state handling was inspected.
- [x] IR manual follow-up handling for open-ended rows was inspected.
- [x] Lucktext/gap-fill keyed behavior was checked for accidental regression.
- [x] Mounted UI tests were audited for the reported warning-state regression.
- [x] Advisory `Acceptera`/`Ändra` controls were compared with mockup source and CSS.
- [x] Fresh browser proof artifact was inspected for final visual closeout.

## Review Feedback

**Reviewer:** ruthless_review_agent
**Date:** 2026-06-29
**Verdict:** approved after Task 374 rereview

Superseded approval note: the previously blocking `Fritext`/open-ended row state is resolved in code:
open-ended IR follow-ups no longer become actionable row attention, compact
review-state rows with `item_type=open_ended` normalize to `Klart`/`complete`
with no reason label, and mounted UI coverage now proves that
`Kontrollera`, `Frågetypen behöver kontrolleras`, and the warning triangle are
not shown for the reported free-text case.

The advisory action treatment is acceptable for code review as a mockup-aligned
primary/secondary pair rather than the previous app CTA primitive. The current
implementation no longer uses `btn-primary`/`btn-cta` for the advisory
`Acceptera` control, and the mockup CSS defines these controls as local
`primary`/`secondary` action buttons rather than the app's shadowed primary CTA.

### Required Changes

- Completed: Sir Convert Task 374 preserves bounded first-pass advisory candidates for
  untouched keyed items when correction apply/replay returns
  `answer_key_review_state`.
- Completed: PR-0408 includes consumer coverage proving both sides of the contract:
  preserved producer `advisory_candidate_pending` renders as `Granska` with
  bounded suggestion detail, while producer `validation_required` renders as
  `Kontrollera` and is not converted back into a pending local suggestion.
- Completed for dev: `.artifacts/playwright-pr-0337-correction-session-live/20260629T193503Z/manifest.redacted.json`
  exercises the production repro sequence locally and proves that after
  accepting `item-001`, untouched sibling `item-002` remains `Granska` with
  advisory detail visible.
- Still required for product closeout: production deploy and fresh production
  proof must exercise the same tracked-DXE sequence: upload, accept one
  advisory key, verify untouched keyed advisory candidates still keep their
  suggestion state, navigate, reload, and verify replay/readback remains
  producer-driven.

### Decision

Approved for the reviewed Task 374 / PR-0408 remediation. Automated evidence is
sufficient to proceed to dev end-to-end proof; it does not replace the required
dev/prod browser proof for PR-0408 product closeout.

### Verification Evidence

| Command or evidence | Result |
|---|---|
| `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts` | Passed locally, 22 tests. |
| `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts` | Reported passed after latest parent patch, 31 tests. |
| `/opt/homebrew/bin/pdm run fe-type-check` | Reported passed after latest parent patch. |
| `/opt/homebrew/bin/pdm run fe-lint` | Reported passed after latest parent patch. |
| `/opt/homebrew/bin/pdm run fe-build` | Reported passed after latest parent patch with existing Vite dynamic/static import and large-chunk warnings. |
| `/opt/homebrew/bin/pdm run docs-validate` | Reported passed after latest parent patch. |
| `/opt/homebrew/bin/pdm run handoff-validate` | Reported passed after latest parent patch. |
| `git diff --check` | Reported passed after latest parent patch. |
| `.artifacts/pr-0408-exam-converter-design-proof/20260629T174933Z/manifest.redacted.json` | Passed; desktop `Frågor`/`Filer`/`Rapport`, phone list/detail/files/report screenshots, and all captured viewports report no horizontal overflow. |

### Residual Risk

- The retained proof uses the fixture data shape for PR-0408 rather than the
  exact mockup item counts, so review should treat visual parity as layout,
  state, symbol, copy, and action-treatment alignment rather than row-count
  identity.

## Changes Made

| Change | Artifact | Description |
|---|---|---|
| 1 | `REV-PR-0408` | Retained independent review recorded for PR-0408 frontend design implementation alignment with decision `approved` for code. |
| 2 | `REV-PR-0408` | Added fresh browser/PNG proof closeout evidence from `.artifacts/pr-0408-exam-converter-design-proof/20260629T174933Z/manifest.redacted.json`. |

## Review Pass 2

Independent cross-repo review of the Task 374 / PR-0408 remediation patch.

### Finding

Sir Convert Task 374 still projects non-keyed free-text rows as answer-key
review warnings and can apply signed advisory candidates before checking
whether an item is choice or gap/open-cloze keyed. See
`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/reviews/review-59-ruthless-review-of-task-374-advisory-candidate-replay.md`.

This keeps PR-0408 blocked because the consumer cannot both consume producer
truth and satisfy the no-warning-gate contract for free-text/open-writing rows
until the producer contract is corrected.

### Evidence

- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedAdvisoryReplaySlice.spec.ts`
  passed: `2 passed`.
- The new consumer spec covers both sides of the replay handshake:
  preserved producer `advisory_candidate_pending` renders as `Granska`, and
  producer `validation_required` renders as `Kontrollera` without locally
  reviving the first-pass suggestion.

### Decision

changes_requested

## Review Pass 3

Independent rereview of the Task 374 / PR-0408 remediation after the prior
changes-requested finding.

### Findings

No blocking findings.

Sir Convert now returns `answer_key_not_applicable` for non-keyed rows before
advisory preservation, only keeps `advisory_candidate_pending` for keyed
choice/gap/open-cloze rows, and emits bounded provenance detail only when a
pending advisory row exists. The Task 374 fixture includes a bogus valid
free-writing advisory candidate and proves it remains `review_complete` with no
provenance detail.

Skriptoteket accepts the new reason vocabulary and the mounted replay spec
proves both sides of the consumer contract: preserved producer pending rows
stay `Granska` with suggestion detail, while producer `validation_required`
stays `Kontrollera` without local suggestion revival.

### Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_bundle_review_state_includes_bounded_pending_advisory_detail tests/sir_convert_a_lot/test_openapi_contract_v2.py::test_service_api_v2_consumer_components_are_published -q`
  passed in Sir Convert: `14 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedAdvisoryReplaySlice.spec.ts src/views/apps/exam-converter-authenticated/answerKeyReviewStateAdapter.spec.ts`
  passed in Skriptoteket: `11 passed`.
- `/opt/homebrew/bin/pdm run fe-type-check` passed.
- `git diff --check` passed in both repositories.
- `/opt/homebrew/bin/pdm run python -m scripts.playwright_pr_0337_correction_session_live --source-dxe /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1776888013-ak7-lag-och-ratt.dxe --base-url http://127.0.0.1:5173 --timeout-seconds 600`
  passed locally with manifest
  `.artifacts/playwright-pr-0337-correction-session-live/20260629T193503Z/manifest.redacted.json`.

Parent-reported supporting evidence:

- Sir Convert `docs-validate` and `handoff-validate` passed.
- Sir Convert `typecheck-all` still fails only unrelated existing
  `tests/* no-any-return` errors; no Task 374 errors.
- Skriptoteket `docs-validate` and `handoff-validate` passed.

### Decision

approved
