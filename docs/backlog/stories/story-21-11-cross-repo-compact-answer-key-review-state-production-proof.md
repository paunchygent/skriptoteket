---
type: story
id: ST-21-11
title: "Cross-repo compact answer-key review state production proof"
status: done
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
epic: "EPIC-21"
dependencies:
  - "ST-21-04"
  - "PR-0406"
  - "ADR-0086"
  - "ADR-0087"
  - "Sir Convert story-57-cross-repo-compact-answer-key-review-state-production-proof"
  - "Sir Convert task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket"
links:
  - "docs/mockups/pr-0406-answer-key-review-small-screen/README.md"
  - "docs/mockups/pr-0406-answer-key-review-desktop/README.md"
acceptance_criteria:
  - "Given Sir Convert Task 373 is approved, when PR-0406 consumes the compact projection, then Skriptoteket renders answer-key review state from one producer-backed adapter instead of local joins over IR, effective IR, completion reports, correction sessions, and readiness reports."
  - "Given the production proof uses a tracked real DXE fixture, when the teacher reviews the conversion, then pending advisory, reviewed complete, teacher modified, and validation-required states render with the agreed compact labels and no stale-AI or accepted-current-state wording."
  - "Given the production proof runs at a phone-sized viewport, when the teacher moves through review, files, and report, then the UI uses a bespoke small-screen task flow with separate list, detail, files, and report surfaces instead of a squeezed desktop workbench."
  - "Given the production proof runs at a desktop viewport, when compact review state exists, then the result band uses actionable `Kontrollera facit` framing and the detail pane exposes symbolic sticky previous/next navigation without visible word labels."
  - "Given the Files view is active at a phone-sized viewport, when generated artifacts render, then no selected-question editor or singular question detail is shown above the files."
  - "Given teacher intents are saved locally, when replay is stale or unavailable, then Skriptoteket shows saved input only as local/readback state and keeps report/file/export readiness blocked until Sir Convert returns fresh projection and target readiness."
  - "Given corrected files are available, when the teacher downloads or saves PDF/QTI, then the actions use replay-scoped Sir Convert artifact references and never original stale job artifacts."
  - "Given final closeout is requested, when production evidence is retained, then the proof bundle shows authenticated browser upload, Sir Convert job/advisory projection, teacher review interactions, correction replay, report/files views, PDF/QTI download/save, reload persistence, desktop/mobile viewport checks, and forbidden browser-authority checks."
ui_impact: "Yes (authenticated Exam Converter question list, detail pane, report, files view, and mobile state rendering)."
data_impact: "No new durable data model beyond existing correction-session persistence; PR-0406 consumes producer projection and existing readback/replay."
---

# ST-21-11: Cross-Repo Compact Answer-Key Review State Production Proof

## Context

Sir Convert owns producer-side source/effective exam truth and target
readiness. Skriptoteket owns authenticated teacher interaction and local
correction-session persistence. This story is the mirrored Skriptoteket tracking
surface for the Task 373 / PR-0406 cross-repo implementation and final live
proof.

The purpose is to keep the handoff small and verifiable: Task 373 must land
first in Sir Convert, PR-0406 consumes it in Skriptoteket, and the final gate is
a real production browser proof with a tracked `.dxe` fixture.

## Scope

- Consume Sir Convert's `digiexam_answer_key_review_state_v1` projection through
  one narrow adapter.
- Render compact Swedish labels from producer semantic state:
  `Granska`, `Klart`, `Ändrat`, and `Kontrollera`.
- Keep `provenance_detail` optional and detail-only. Do not model a generic
  `history` stream or any `review_decision` compatibility surface.
- Render small-screen Exam Converter as a bespoke task flow. Question list,
  selected item detail, files, and report are separate narrow-viewport surfaces;
  the files surface contains file rows/actions only.
- Use the approved exact small-screen answer-key review mockup at
  `docs/mockups/pr-0406-answer-key-review-small-screen/README.md` as the
  visual and copy authority for the represented review states.
- Use the desktop alignment mockup at
  `docs/mockups/pr-0406-answer-key-review-desktop/README.md` as the proposed
  desktop visual and copy authority once product approval is recorded.
- Render the desktop result band from compact review-state aggregates with
  `Kontrollera facit`, compact review counts, and
  `Granska frågorna som saknar rätt svar eller facitsvar.` instead of
  projection-backed partial-conversion copy.
- Do not expose pre-conversion PDF/QTI target-file or source-format choices in
  the workflow rail. Supported generated files are requested automatically for
  the DXE converter path, then downloaded or saved from `Filer` once review
  persistence and artifact readiness permit.
- Keep desktop detail navigation symbolic: Lucide previous/next controls with
  accessible labels, no persistent visible `Föregående` / `Nästa` text, and
  auto-advance only after backend-confirmed persistence plus fresh Sir Convert
  replay projection.
- Treat `Ändra` as entry into the normal answer-key editor inside the selected
  detail surface, with `Spara facit` for teacher-owned edits and bounded
  `Tidigare förslag` detail when the edit began from an advisory suggestion.
- Keep PR-0406 review-state symbols bound to the approved symbol contract:
  `IconAi`/`Sparkles`, `IconCheck`/`Check`, `IconEdit`/`PencilLine`, and
  `IconWarning`/`AlertTriangle`.
- Keep file readiness driven by Sir Convert `target_readiness_report_v1` and
  replay artifact references, not question-list state.
- Use the same final production proof fixture as the Sir Convert mirror:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1776888013-ak7-lag-och-ratt.dxe`.

## Out Of Scope

- No Sir Convert schema/runtime implementation in this story.
- No public anonymous consumer path for the compact review-state report.
- No accepted-current-state export workaround.
- No local answer-key review-state inference fallback once the producer
  projection exists.
- No broad report redesign beyond what is needed to consume producer state.

## Overseer Implementation Handoff

You are the overseer. Run Sir Convert Task 373 first with
`implementation_agent`, then a fixed `ruthless_review_agent` until approved.
Only then run PR-0406 with a separate `implementation_agent` and fixed
`ruthless_review_agent`. Do not inspect partial worker diffs while a worker or
reviewer is active.

PR-0406 success means the authenticated Exam Converter UI consumes Sir
Convert's projection through one adapter and proves state labels, report/files
behavior, saved-intent separation, replay artifact authority, and mobile/desktop
rendering. The story closes only after the final live browser gate below passes.

## Final Live Browser Gate

Run this only after both repos have approved retained reviews and production
deploys are healthy.

1. Authenticate through the HuleEdu browser-session ceremony at production
   Skriptoteket. Do not use direct backend credential posts, direct product
   cookies, browser-authored identity headers, or browser-direct Sir Convert
   calls.
1. Upload the named DXE fixture through the production Exam Converter UI.
1. Verify Sir Convert first-pass artifacts include the compact
   `answer_key_review_state_report`, target readiness, PDF, and QTI where
   readiness permits.
1. Verify desktop and mobile question list/detail states render from the compact
   projection.
1. Verify the desktop result band uses `Kontrollera facit` review framing when
   compact review state exists and does not show partial-conversion copy for the
   projection-backed review state.
1. Verify the pre-conversion workflow rail does not ask the teacher to select
   PDF/QTI target files or source formats.
1. Verify desktop detail navigation uses symbolic previous/next controls with
   accessible labels and no visible word labels.
1. Verify `Ändra` opens the represented answer-key edit surface, `Spara facit`
   persists teacher-owned edits, and bounded advisory provenance remains
   detail-only.
1. At a phone-sized viewport, verify the small-screen flow keeps the question
   list, item detail, files, and report as separate task surfaces with no
   horizontal overflow, clipped action labels, hidden desktop columns, or
   selected-question editor/detail inside the Files view.
1. Exercise all supported teacher interactions available in the fixture:
   accept an unchanged advisory key, edit a suggested key or keyed content,
   create/fix a missing choice or gap/open-cloze key, save facit, navigate
   between items, open report, open files, and return to questions.
1. Verify saved intents survive navigation/reload but do not become fresh
   `Klart`/file-ready state until Sir Convert replay returns projection and
   readiness.
1. Verify correction replay submits the complete supported persisted correction
   set through Gateway/Sir Convert and PR-0406 renders returned
   `answer_key_review_state`.
1. Verify PDF/QTI download and save actions stay disabled until replay artifact
   references authorize them, then download and save replay-scoped corrected
   PDF/QTI artifacts.
1. Retain a redacted proof bundle with screenshots, request/correlation ids,
   projection/readiness snippets, artifact names, download/save evidence,
   reload evidence, desktop/mobile checks, and forbidden browser-authority
   checks.

## Planned PR Slice

- [x] [PR-0406: ST-21-04 Exam Converter consume compact answer-key review state](../prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md)

## Test Requirements

- [x] Parser/contract tests reject unknown schema versions, unknown state/origin
  codes, unknown reason codes, missing projection, `history`, and
  `review_decision` compatibility payloads.
- [x] Projection tests prove exhaustive mapping from producer state to Swedish
  labels/icons.
- [x] Component tests prove PR-0406 review states use the approved symbol
  wrappers rather than feature-local `Bot`, `CheckCircle2`, or `XCircle`
  imports.
- [x] Component tests prove desktop table and mobile navigator render the same
  compact states.
- [x] Component tests prove the desktop result band uses the approved
  projection-backed copy and keeps export-ready copy behind target readiness
  plus replay artifact authority.
- [x] Component tests prove the workflow rail has no pre-conversion PDF/QTI
  target-file/source-format selection controls.
- [x] Component tests prove desktop detail navigation is symbolic, sticky, and
  does not use visible previous/next word labels.
- [x] Component tests prove `Ändra` switches the selected detail pane into the
  normal answer-key editor with `Spara facit` and bounded `Tidigare förslag`
  detail for advisory-seeded edits.
- [x] Small-screen layout tests prove list, detail, files, and report are
  separate task surfaces and that the files surface has no selected-question
  editor/detail content.
- [x] Replay tests prove local saved input does not unlock file actions before
  fresh Sir Convert projection/readiness.
- [x] Report/files tests prove `Kontrollera` is a current validation problem
  and corrected PDF/QTI actions use replay artifact references.

## Done Definition

This story is done only when Sir Convert Task 373 and Skriptoteket PR-0406 are
approved, production deployments are healthy, and the final live browser proof
passes with retained redacted evidence linked from both repos.

## Production Closeout

Closed on 2026-06-29 after Sir Convert Task 373 approval, PR-0406 approval,
production deploys, HuleEdu Gateway recovery, and the retained production DXE
proof.

- Sir Convert production revision:
  `95937ea6e9a892a2825521149ecbcc29262d6252`; deploy verifier:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/build/verification/hemma-deploy-verify/report.md`.
- Skriptoteket production revision:
  `63e27ad4e65bc0cb5f3abceb8f8498dc12d6303e`; deploy log:
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260629-150551.log`.
- HuleEdu Gateway/browser-session recovery log:
  `/home/paunchygent/apps/huleedu/.artifacts/hemma-deploy-20260629T151038Z.log`.
- Final production proof bundle:
  `.artifacts/playwright-pr-0337-correction-session-live/20260629T152928Z/manifest.redacted.json`.
  The proof covers HuleEdu login, production DXE upload, first-pass
  `digiexam_answer_key_review_state_v1`, `Acceptera -> Klart`,
  `Ändra -> Ändrat`, validation key repair, report/files views, disabled draft
  downloads/saves, replay-scoped PDF/QTI download and save, reload persistence,
  mobile detail/list/files/report screenshots with no horizontal overflow, no
  page errors, and clean PDF/QTI inspection.

## Notes

- Task 373 and PR-0406 are approved and deployed.
- Keep public anonymous compact-report consumption out of PR-0406 unless a
  later governed story explicitly adds public grant semantics.
