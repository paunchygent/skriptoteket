---
type: pr
id: PR-0338
title: "ST-21-04 AI prefill editor and replay artifact authority"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - frontend
  - conversion-hub
  - exam-converter
  - teacher-corrections
  - artifact-authority
dependencies:
  - "ADR-0087"
  - "PR-0336"
  - "REV-PR-0333"
acceptance_criteria:
  - "Given a valid AI answer-key candidate exists, when the question editor opens, then the candidate is used only as the initial editor value and no separate accepted/rejected AI decision state is created."
  - "Given the teacher saves an unchanged AI-prefilled answer key, when Skriptoteket builds the durable intent, then the payload uses `submission_origin: accepted_advisory_candidate` with candidate lineage."
  - "Given the teacher edits an AI-prefilled answer key before saving, when Skriptoteket builds the durable intent, then the payload uses `submission_origin: teacher_edited_advisory_candidate` with candidate lineage."
  - "Given no usable AI candidate exists, when the teacher saves an answer key, then the durable intent uses `submission_origin: teacher_authored` and no candidate lineage."
  - "Given the teacher clicks `Spara facit`, when the save succeeds, then the UI advances only after upsert, durable readback, full Sir Convert replay, and projection update."
  - "Given replay returns no corrected artifact download/save reference, when the teacher opens `Filer`, then `Hämta` and `Spara` remain disabled even if original job artifacts exist."
  - "Given durable active intents include supported kinds, when replay builds the Sir Convert apply request, then it submits the full supported set: `item_text_patch`, `point_correction`, `manual_choice_answer_key`, `manual_gap_open_cloze_answer_key`, `candidate_suppression`, and `review_decision`."
  - "Given same-batch answer-key/review-decision conflict is submitted, when the aggregate validates it, then the backend rejects it; given sequential writes occur, the later write explicitly supersedes the prior family."
  - "Given stale reviewed-AI workflow code, docs, or tests exist, when this slice closes, then they are deleted or rewritten so no hidden bulk accept/apply path remains."
---

# PR-0338: ST-21-04 AI Prefill Editor And Replay Artifact Authority

## Problem

The durable correction-session flow now has the right persistence and replay
spine, but the product still carries remnants of the older reviewed-AI
interaction model. That abandoned model treats AI suggestions as a separate
acceptance workflow, which conflicts with teacher-authored edits and creates
extra local state that can drift from the durable correction session.

The remaining file action path has a separate authority problem: corrected
projection/readiness can come from Sir Convert replay, while download/save
actions can still fall back to original job artifacts. That makes the UI claim
corrected files are available without proving the buttons target the same
replayed artifact evidence.

## Goal

Delete the abandoned reviewed-AI interaction model and tighten the artifact
authority boundary. AI suggestions are readable candidate data and editor
initial values only. The item editor is the only answer-key write surface, and
the save/replay/download pipeline is identical for empty, AI-suggested, saved,
and teacher-edited facit.

File actions must be enabled only when the replay result that drives the UI
also provides a valid corrected artifact download/save reference. No corrected
file action may fall back to original job artifacts.

## Scope

- UI impact: authenticated Exam Converter answer-key editing, AI suggestion
  navigation, file actions, and teacher-facing state copy.
- Data impact: no database migration expected unless Skriptoteket-owned replay
  artifact storage endpoints are introduced.
- Remove persisted/local "reviewed AI suggestion decision" workflows from the
  authenticated Exam Converter UI path.
- Keep `ExamConverterManualAnswerKeyEditor.vue` as the only answer-key write
  surface and keep one save event: `applyManualAnswerKey(question, answerKey)`.
- Preserve draft initialization order: replayed effective saved facit, then
  usable AI candidate, then empty draft.
- Keep `submission_origin` and candidate lineage as audit metadata computed at
  durable intent build time, never as a teacher-facing mode choice.
- Remove item-level AI action affordances such as accept, edit-as-AI,
  reject-as-answer-key, remove-facit, reviewed overlay apply, and hidden bulk
  accept/apply paths.
- Keep the top AI panel as navigation only: it may report that suggestions
  exist and may focus the first unsaved AI-prefilled item.
- Move next-item advancement after upsert, durable readback, full replay, and
  projection update.
- Ensure replay submits every supported active intent kind listed in
  `ADR-0087`; no replay filter may drop supported truth.
- Keep backend answer-key/review-decision conflict-family enforcement strict:
  same-batch incompatible state rejects, sequential writes supersede
  explicitly.
- Gate file `Hämta` and `Spara` actions on replay artifact references produced
  by the same replay result that drives visible file readiness.
- Replace internal freshness/copy noise with teacher-facing states:
  `Sparar`, `Sparat`, `Kunde inte sparas`, `Filer kan hämtas`, and
  `Filer kunde inte skapas`.
- Rewrite or delete stale docs/tests that still describe reviewed-AI
  acceptance as the active workflow.

## Non-goals

- No database migration unless the implementation introduces
  Skriptoteket-owned replay artifact storage.
- No compatibility shim, adapter, alias, or fallback for
  `reviewedCompletionOverlay`.
- No hidden bulk save or accept-all path.
- No matching answer-key enablement before Sir Convert Task 332 and a later
  approved slice.
- No fallback to original Sir Convert job artifacts after corrections.
- No new public conversion behavior.

## Implementation plan

1. Delete or rewrite the stale reviewed-AI workflow surface:
   `acceptSuggestion`, `acceptAllSuggestions`,
   `acceptEditedChoiceSuggestion`, edited gap-fill accept helpers,
   `rejectSuggestion` as an answer-key workflow,
   `applyReviewedSuggestions`, and `reviewedCompletionOverlay` paths must not
   remain in the active authenticated Exam Converter flow.
2. Rename or rewrite AI-related navigation state so it represents focus only,
   not review decisions. The top panel should be a compact navigation surface
   with no save or bulk action.
3. Keep the manual answer-key editor as the write surface for all answer-key
   origins and verify that editor drafts initialize from replayed effective
   saved truth before advisory candidate data.
4. Keep provenance calculation in the durable intent builder. Compare the
   saved editor value with the usable AI candidate and emit
   `accepted_advisory_candidate`, `teacher_edited_advisory_candidate`, or
   `teacher_authored` plus candidate lineage rules from the acceptance
   criteria.
5. Change save advancement so the selected item only advances after the
   upsert/readback/replay/projection sequence succeeds. Local clicks may show
   pending state only.
6. Extend the replay projection/file model with corrected artifact references,
   or keep file actions disabled until Sir Convert/Skriptoteket provides such
   references. `exportEnabled` alone is not enough to enable `Hämta` or
   `Spara`.
7. Update file action clients to use replay-provided references only for
   corrected artifacts. Remove fallback to original `/jobs/{jobId}/artifacts`
   for corrected file actions.
8. Keep aggregate conflict-family tests aligned with the desired semantics:
   same-batch mixed answer-key/review-decision truth rejects; sequential writes
   supersede.
9. Update docs and tests so reviewed-AI acceptance is archival history, not an
   active workflow.

## Test plan

- Focused frontend tests proving:
  - unchanged AI prefill saves with `accepted_advisory_candidate` and candidate
    lineage;
  - edited AI prefill saves with `teacher_edited_advisory_candidate` and
    candidate lineage;
  - no AI candidate saves with `teacher_authored` and no candidate lineage;
  - `Spara facit` calls upsert, durable readback, full replay, and projection
    update before selecting the next AI-prefilled unsaved item;
  - UI question rows do not show contradictory missing-facit versus AI-prefill
    truth;
  - file buttons stay disabled unless replay provides a valid corrected
    artifact reference;
  - hidden bulk accept/apply paths and stale reviewed-AI labels are absent.
- Focused replay tests proving the complete supported active set is submitted
  to Sir Convert apply.
- Backend aggregate tests only if the conflict-family implementation changes.
- Closeout gates:
  - `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run fe-build`
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

## Implementation closeout

Completed in this slice:

- Replaced the stale reviewed-AI action surface with AI-prefill focus state:
  candidates seed the normal answer-key editor, and editor saves compute
  `accepted_advisory_candidate`, `teacher_edited_advisory_candidate`, or
  `teacher_authored` at durable-intent build time.
- Moved AI-prefill next-item advancement behind the durable save/readback/
  replay/projection sequence; local click state no longer advances the teacher
  before replayed truth lands.
- Added an explicit file action reference to projected file rows. Original job
  artifacts are authorized only for original-job projections; replay-derived
  rows require a replay-provided corrected artifact reference before `Hämta` or
  `Spara` can enable.
- `PR-0339` superseded the upstream contract gap: replay responses can now
  expose corrected artifact references, and corrected file actions enable only
  when those replay-scoped references are present.
- Accepted unchanged AI-prefilled facit keeps AI provenance after replay, so
  the question list and inspector use the Lucide Bot symbol. Teacher-authored
  and teacher-edited facit keep the normal selected/check indicator.
- Report warnings are presented as conversion diagnostics, not remaining
  teacher actions, so warning counts can remain visible after all facit/poäng
  checks are resolved and corrected artifacts are available.
- Rewrote focused tests from the stale reviewed-AI acceptance wording to
  AI-prefill durable-session behavior and expanded replay coverage for the
  complete supported active intent set.

### Follow-up decision for product-owner approval

1. Corrected artifact delivery authority:
   - Option A (recommended and now captured as `PR-0339`): create the governed
     upstream Sir Convert producer task for replay-scoped corrected artifact
     references. The unified correction apply result should return a corrected
     artifact reference, for example an `artifact_key` or explicit
     `artifact_reference`, on `ExamAuthoringCorrectionTargetReadinessRowV1`
     only when the replay-created target is the downloadable/saveable
     authority. HuleEdu Gateway should pass that reference through unchanged,
     and Skriptoteket should only map it into `file.artifactActionReference =
     { authority: "replay_result", artifactKey }`. Until that exists,
     corrected file actions stay disabled. This preserves the strict authority
     boundary and lets `PR-0337` prove the disabled state honestly.
   - Option B: introduce Skriptoteket-owned replay artifact storage in a later
     governed slice. This would make downloads/save actions available without
     waiting for Sir Convert to retain replay artifacts, but it moves storage,
     retention, and security authority into Skriptoteket.
2. Final browser proof wording:
   - Option A (recommended): make `PR-0337` prove durable correction readback,
     replayed question truth, and disabled corrected file actions when no replay
     artifact reference exists.
   - Option B: defer `PR-0337` until upstream corrected artifact references are
     available, so proof can include enabled downloads/saves.

## Rollback plan

Rollback means reverting this PR's UI and documentation changes together before
`PR-0337` proof runs. Do not restore the abandoned reviewed-AI workflow as a
compatibility path after this slice is accepted; if replay artifact references
are unavailable, keep corrected file actions disabled and document the upstream
contract gap.
