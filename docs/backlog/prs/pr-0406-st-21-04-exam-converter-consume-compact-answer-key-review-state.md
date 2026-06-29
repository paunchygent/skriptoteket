---
type: pr
id: PR-0406
title: "ST-21-04 Exam Converter consume compact answer-key review state"
status: done
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
stories:
  - "ST-21-04"
  - "ST-21-11"
tags:
  - frontend
  - vue
  - conversion-hub
  - exam-converter
  - teacher-corrections
  - sir-convert
  - answer-key-review
dependencies:
  - "Sir Convert task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket"
  - "Sir Convert story-57-cross-repo-compact-answer-key-review-state-production-proof"
  - "ADR-0087"
  - "ADR-0086"
links:
  - "docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md"
  - "Sir Convert docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md"
  - "Sir Convert docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md"
  - "docs/reference/ref-exam-converter-ui-content-model-v1.md"
  - "docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md"
  - "docs/mockups/pr-0406-answer-key-review-small-screen/README.md"
  - "docs/mockups/pr-0406-answer-key-review-desktop/README.md"
acceptance_criteria:
  - "Given Sir Convert exposes a compact answer-key review-state projection, when Skriptoteket renders the question list, then list state comes from that projection instead of being re-derived from multiple producer artifacts and local UI state."
  - "Given a pending advisory answer-key suggestion exists, when the list renders, then the item uses the compact review-needed state with the approved `IconAi`/`Sparkles` affordance and does not imply an error."
  - "Given a teacher has reviewed an AI-suggested key unchanged, when the list renders, then the item shows only the normal completed state, such as `Klart` with a checkmark, and no extra AI badge."
  - "Given a teacher has edited the suggested key, keyed option text, gap value, stem, or other keyed content, when the list renders, then the current key is treated as teacher-owned and no AI provenance marker is shown for the current key."
  - "Given a multiple-choice or gap/open-cloze item lacks a valid selected key or accepted value, when the list and detail render, then the UI shows a compact current validation problem such as `Kontrollera` with a reason like `Inget rätt svar valt`, not stale-AI wording."
  - "Given the Exam Converter runs on a small screen, when the teacher switches between questions, files, and report, then Skriptoteket renders a bespoke task flow rather than a squeezed or stacked desktop two-column workbench."
  - "Given the Files tab is active on a small screen, when files render, then the screen contains file rows/actions only and does not show a selected-question editor or singular question detail above the file list."
  - "Given compact review state exists on desktop, when the result band renders, then it uses actionable review framing such as `Kontrollera facit`, `6 att granska`, and `Granska frågorna som saknar rätt svar eller facitsvar.` instead of coarse partial-conversion copy."
  - "Given a teacher reviews desktop item details, when the detail pane scrolls, then symbolic Lucide previous/next controls remain available as sticky navigation without visible word labels."
  - "Given a teacher uploads a DXE file, when the pre-conversion workflow rail renders, then it does not ask the teacher to choose PDF/QTI target files or source formats; supported PDF and QTI outputs are requested automatically and acted on later in `Filer`."
  - "Given a teacher chooses to change an advisory key instead of accepting it, when the desktop detail pane enters edit mode, then it shows the normal answer-key editor with `Spara facit` semantics and bounded `Tidigare förslag` provenance detail."
  - "Given file actions are evaluated, when Sir Convert has not returned target readiness or replay artifact references, then Skriptoteket keeps downloads/save actions disabled and does not infer readiness from local drafts."
  - "Given local correction-session readback exists, when Skriptoteket claims saved/reviewed/exportable state, then that claim is backed by Sir Convert returned projection/effective state rather than component-local state."
---

# PR-0406: ST-21-04 Exam Converter Consume Compact Answer-Key Review State

## Problem

Authenticated Exam Converter currently assembles item review state from several
surfaces: source IR, migration manifest, target readiness, optional
answer-key completion report, optional effective IR, correction-session
readback, and replay apply results. That makes the UI too responsible for
state semantics that belong to the producer. Small local assumptions can drift
from Sir Convert's source/effective state and artifact readiness contracts.

The current UX direction is deliberately compact:

- `Granska` means a teacher action is needed, including a pending AI suggestion
  where the approved `IconAi`/`Sparkles` affordance may be shown.
- `Klart` means the item is reviewed/valid for the current projection and needs
  no extra AI badge in the list.
- `Ändrat` may be used for a teacher-owned modified key, but AI provenance must
  not be shown as current-key provenance after keyed content changes.
- `Kontrollera` means a current validation problem, such as no correct answer
  selected or no accepted gap value. It does not mean stale AI provenance.

Those visible labels are Skriptoteket presentation choices. The durable
semantic state must come from Sir Convert.

## Goal

Consume the Sir Convert compact answer-key review-state projection introduced
by Task 373 and make it the primary source for authenticated Exam Converter
question-list, detail, report, and file-action review state.

Skriptoteket still owns teacher interaction, local authenticated
correction-session persistence, and presentation. Sir Convert owns source and
effective state, answer-key provenance semantics, candidate lineage/audit data,
target readiness, and replay artifact authority.

The approved small-screen visual and copy direction is retained in
`docs/mockups/pr-0406-answer-key-review-small-screen/README.md`. That mockup
bundle is the authority for the approved phone-flow hierarchy and the final
language corrections from the product discussion.

The desktop alignment mockup is retained in
`docs/mockups/pr-0406-answer-key-review-desktop/README.md`. It applies the same
state, copy, and symbol decisions to the desktop workbench while preserving the
desktop scan-and-detail layout.

## Non-goals

- No Sir Convert schema or runtime implementation in this PR.
- No local answer-key inference fallback once the Sir Convert projection is
  available.
- No accepted-current-state export workaround.
- No browser-local claim that a draft, prefill, or saved intent is export-ready
  before Sir Convert returns effective projection/readiness evidence.
- No resurrection of the old reviewed-AI acceptance workflow as a separate
  state machine. AI candidates seed normal facit editing and correction
  submission.

## Implementation Plan

1. Regenerate or update the Sir Convert Gateway types after Task 373 exports the
   new projection.
1. Add a typed parser/adapter for the compact projection response or named
   artifact.
1. Replace local list-state inference in the Exam Converter review projection
   with the Sir Convert projection where present.
1. Preserve local draft state only as draft UI; do not use it to unlock files,
   report completion, or reviewed-state claims.
1. Keep correction-session persistence and replay orchestration intact:
   teacher input still becomes source-bound correction intents, and saved state
   becomes authoritative only after readback plus Sir Convert replay/projection.
1. Build the small-screen Exam Converter as a dedicated task flow, not as a
   squeezed or stacked copy of the desktop two-column workspace:
   - the question list, selected item editor, files view, and report view are
     mutually exclusive surfaces on narrow viewports;
   - selected item detail opens as a full-width detail surface or sheet from
     the question list;
   - the files view renders file rows/actions only, never a selected-question
     editor or singular question summary above the files;
   - the report view renders report content only, with navigation back to the
     review flow;
   - the top review/action band and tabs fit the viewport without horizontal
     overflow.
1. Update the mobile/small-screen question list and detail copy to use compact
   labels with fixed, non-clipping row/card geometry:
   - pending advisory: `Granska` with the approved `IconAi` / `Sparkles`
     affordance;
   - reviewed/complete: `Klart` with checkmark only;
   - teacher-owned modified: `Ändrat` or `Klart`, no AI marker;
   - current validation problem: `Kontrollera` plus a short reason.
1. Update report and files views so file readiness remains driven by Sir
   Convert target readiness and replay artifact references, not question-list
   review state.
1. Remove pre-conversion target-file/source-format choice from the authenticated
   Exam Converter workflow rail. For the current DXE converter path, request the
   supported PDF and QTI outputs automatically and expose teacher download/save
   choice only in `Filer` after review persistence and artifact readiness.
1. Update the desktop result band and review-detail controls:
   - projection-backed review uses `Kontrollera facit`, a compact review count,
     and `Granska frågorna som saknar rätt svar eller facitsvar.`;
   - `Konverteringen av provet lyckades delvis` is not the primary
     projection-backed review message;
   - `Ändra` opens the normal answer-key editing surface in the selected detail
     pane, with `Spara facit` for teacher-owned edits and bounded
     `Tidigare förslag` provenance detail where an advisory seed exists;
   - symbolic Lucide previous/next controls remain available in the detail
     pane without visible word labels;
   - accepting or saving a key waits for backend-confirmed readback/replay
     projection before auto-advancing to the next actionable item.

## Closed Consumer Decisions

1. Projection transport.
   - Decision: consume both producer surfaces from Task 373. Use the named
     `answer_key_review_state_report` artifact for first-pass bundle review and
     the top-level correction-apply `answer_key_review_state` field for
     immediate replay UI.
   - Constraint: do not add a second local inference path when either producer
     surface is missing or invalid; fail closed instead.
1. Exact semantic enum names.
   - Decision: map producer `review_state` codes
     `review_required`, `review_complete`, `teacher_modified`, and
     `validation_required` to Skriptoteket presentation state.
   - Decision: consume producer `current_key_origin` codes `none`,
     `source_provided`, `reviewed_advisory`, `teacher_authored`,
     `teacher_edited_advisory`, and `mixed`.
   - Decision: consume producer reason codes including
     `source_answer_key_present`, `advisory_candidate_pending`,
     `reviewed_advisory_accepted`, `teacher_answer_key_present`,
     `teacher_edited_advisory_candidate`, `manual_answer_key_required`,
     `no_correct_choice_selected`, `required_gap_accepted_values_missing`,
     `unsupported_item_type`, `unsupported_target_shape`,
     `target_validation_failed`, `provider_unavailable`,
     `correction_rejected`, `stale_source_state`,
     `replay_artifact_unavailable`, and `matching_source_state_unavailable`.
   - Constraint: generated TypeScript type names and exact schema component
     names are implementation details to bind after Task 373 exports OpenAPI;
     the semantic codes above are already closed.
1. `Ändrat` versus `Klart` in the list.
   - Decision: `teacher_modified` with `current_key_origin =
     teacher_edited_advisory` maps to a teacher-owned modified state. The list
     may show `Ändrat` for orientation, but report/export completion treats the
     item as complete once Sir Convert returns a valid teacher-owned key.
   - Constraint: no AI current-key marker appears after teacher-owned edits.
     If the UI cannot safely distinguish the orientation state, it must render
     plain complete state rather than invent AI provenance.
1. Provenance detail.
   - Decision: consume only Task 373's bounded `provenance_detail` object for
     any `Tidigare förslag` style disclosure. Do not consume or model a generic
     `history` event stream.
   - Rationale: provenance detail is optional detail/audit context. It must not
     create a second review state machine, explain current truth through legacy
     lineage, or affect list labels, report completion, or file readiness.
1. Public lane behavior.
   - Decision: PR-0406 is authenticated-only. Public anonymous compact-report
     consumption is out of scope even if Task 373 can emit a public-safe report.
   - Constraint: any public consumption needs a later governed public-grant
     consumer task.
1. Saved local intent versus producer projection conflict.
   - Decision: show saved correction intent as local saved/readback input only
     when Sir Convert replay is stale or unavailable.
   - Constraint: do not show fresh `Klart`, report completion, file readiness,
     or export/save enablement until replay projection and target readiness
     succeed.
1. Small-screen layout contract.
   - Decision: mobile/small-screen Exam Converter uses a bespoke
     task-oriented flow, not responsive stacking of the desktop workbench.
     Question list, item detail, report, and files are separate narrow-viewport
     surfaces.
   - Decision: the files surface must not carry question-detail context. It
     shows generated files and file actions only, with filenames wrapping or
     truncating safely and format/action affordances kept visible.
   - Constraint: no small-screen implementation may rely on horizontal
     clipping, hidden right panes, squeezed tables, or off-canvas desktop
     columns as the primary user path.
1. Small-screen mockup and copy approval.
   - Decision: use
     `docs/mockups/pr-0406-answer-key-review-small-screen/README.md` as the
     approved exact mockup and language authority for PR-0406 small-screen
     answer-key review.
   - Decision: the canonical generated preview and `index.html` source encode
     the final approved small-screen layout and copy. Treat them as decision
     material, not inspiration.
   - Decision: validation issues use concrete missing-key language such as
     `Inget rätt svar valt`, `Välj minst ett rätt svar`, or `Saknar facitsvar`.
   - Decision: manual validation repair uses `Spara facit`; keep it disabled
     until a valid key/value exists.
   - Decision: `Acceptera` is reserved for accepting a pending AI suggestion
     unchanged. A second click must not convert unchanged AI provenance into a
     teacher-authored key.
1. Symbol contract.
   - Decision: PR-0406 small-screen review symbols must follow
     `docs/reference/ref-symbol-semantics-inventory-and-decision-contract-2026-05-04.md`
     and the symbol table in
     `docs/mockups/pr-0406-answer-key-review-small-screen/README.md`.
   - Decision: pending AI suggestions and AI detail use `IconAi` /
     `Sparkles`, reviewed/selected state uses `IconCheck` / `Check`,
     teacher-owned changed state uses `IconEdit` / `PencilLine`, and current
     validation problems use `IconWarning` / `AlertTriangle`.
   - Constraint: do not introduce feature-local direct `Bot`, `CheckCircle2`,
     or `XCircle` imports for the PR-0406 state projection. Existing Exam
     Converter drift must be corrected as part of the consumer implementation
     where these states are touched.
1. Desktop layout and result-band contract.
   - Decision: desktop keeps the workbench advantage: left workflow rail,
     central question table, and one selected-question detail pane for the
     active `Frågor` mode.
   - Decision: the pre-conversion workflow rail does not expose PDF/QTI target
     checkboxes or source-format choices. The source upload determines source
     handling, and supported PDF/QTI outputs are requested automatically for the
     current DXE converter path.
   - Decision: `Filer` and `Rapport` remain exclusive inspection modes on
     desktop as well. They must not carry a selected-question detail pane or a
     singular question summary above their mode content.
   - Decision: teacher choice over generated outputs happens in `Filer` after
     review persistence and target readiness, by downloading or saving each
     generated file.
   - Decision: when compact review state exists, the desktop result band uses
     actionable review framing instead of coarse conversion-result language:
     `Kontrollera facit`, a compact count such as `6 att granska`, and
     `Granska frågorna som saknar rätt svar eller facitsvar.`
   - Constraint: export-ready copy such as `Filerna kan sparas eller hämtas`
     may appear only when Sir Convert target readiness and replay artifact
     references authorize the file actions. The answer-key review projection
     alone must not unlock downloads or saves.
   - Constraint: if the compact projection is expected but missing or invalid,
     fail closed with review unavailable/blocked copy rather than falling back
     to local `Klart` inference or the old partial-conversion framing.
1. Desktop detail navigation and persistence behavior.
   - Decision: desktop detail panes get sticky symbolic previous/next
     navigation controls using Lucide `ChevronLeft` and `ChevronRight` or
     approved wrappers for those local navigation controls.
   - Decision: previous/next controls use accessible labels and optional
     tooltips, but no persistent visible `Föregående` / `Nästa` text.
   - Decision: `Acceptera` and `Spara facit` are persistence actions, not
     navigation actions. `Acceptera` is only for accepting a pending advisory
     suggestion unchanged; `Spara facit` is for manual selection, manual
     editing, and validation repair.
   - Decision: `Ändra` opens the normal selected-question answer-key editor in
     the detail pane. The editor may show bounded `Tidigare förslag` provenance
     detail, but it does not create a second AI-specific editing workflow.
   - Decision: after `Acceptera` or valid `Spara facit`, the UI must wait for
     backend-confirmed persistence/readback and Sir Convert replay projection
     before automatically advancing to the next actionable item.
   - Constraint: do not advance optimistically on click, and do not auto-advance
     to a non-actionable next row merely because it is numerically next.

## Implementation Dependencies

PR-0406 was implemented after Sir Convert Task 373 exported the concrete compact
projection schema/OpenAPI surface and was approved by retained Review 58. The
semantic decisions above remain closed.

## Assumptions

- Sir Convert Task 373 will remain the semantic source of truth for compact
  review states.
- Task 373 will expose bounded `provenance_detail` for advisory detail display
  and will not expose a legacy `history` or `review_decision` compatibility
  surface.
- Skriptoteket will continue to persist authenticated teacher correction
  intents locally, then replay the complete set through Sir Convert apply.
- Sir Convert target readiness remains separate from item review state.
- Swedish visible copy remains in Skriptoteket; Sir Convert emits semantic
  codes and message keys, not final UI strings.

## Recommended Implementation Shape

Prefer one narrow adapter module that maps the producer projection into the
existing Exam Converter view model. Avoid distributing new state mapping across
`digiexamIrReviewParser.ts`, `digiexamIrQuestionReviewProjection.ts`, and
`correctionSessionProjection.ts` without a single owner; that is the current
drift risk.

The adapter should make unsupported/missing producer fields fail closed: show
review unavailable or keep existing conservative blocked behavior rather than
guessing `Klart`.

## Test Plan

- Focused projection tests proving Sir Convert compact states map to the
  visible short labels without adding an AI marker to `Klart`.
- Correction-session tests proving local drafts and saved intents do not unlock
  file actions before Sir Convert replay projection/readiness.
- Replay projection tests proving replay artifact references are preserved and
  original job artifacts are not used for corrected downloads.
- Report/files tests proving `Kontrollera` represents a current validation
  problem, not stale AI provenance.
- Desktop component tests proving the result band uses
  `Kontrollera facit` and
  `Granska frågorna som saknar rätt svar eller facitsvar.` when compact review
  state exists.
- Desktop component tests proving symbolic sticky previous/next navigation
  uses accessible labels without visible `Föregående` / `Nästa` text.
- Desktop component tests proving the pre-conversion rail has no PDF/QTI target
  checkboxes and the files view remains the only teacher-facing generated-file
  action surface.
- Desktop component tests proving `Ändra` opens the normal answer-key editor
  with `Spara facit` and bounded `Tidigare förslag` detail for advisory-seeded
  edits.
- Replay/navigation tests proving `Acceptera` and valid `Spara facit` wait for
  backend-confirmed readback/replay projection before auto-advancing to the
  next actionable item.
- Small-screen/component tests at phone-sized viewports proving the question
  list, selected item detail, report, and files surfaces are separate task
  views with no horizontal overflow or clipped action labels.
- Small-screen files-view tests proving files render without a selected-question
  editor/detail surface above them.
- `pdm run fe-test -- --run <focused Exam Converter specs>`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Closeout

Closed on 2026-06-29. `REV-PR-0406` approved the consumer implementation on
pass 2. Production closeout then added proof-harness resilience for the real
protected production route:

- cleanup of the accept-probe correction session uses the protected
  `api.hule.education` origin when the browser runs against
  `https://skriptoteket.hule.education`;
- correction-session writes and replay/save paths tolerate production `429`
  retry-after responses without treating a successful backoff as a failed
  proof;
- the retained production proof now captures phone-sized detail, question-list,
  files, and report screenshots and asserts no horizontal overflow or selected
  question detail on files/report surfaces.

Final production proof:
`.artifacts/playwright-pr-0337-correction-session-live/20260629T152928Z/manifest.redacted.json`.
It proves HuleEdu login, DXE upload, first-pass
`digiexam_answer_key_review_state_v1`, `Acceptera -> Klart`, `Ändra -> Ändrat`,
validation key repair, report/files navigation, disabled draft file actions,
replay-scoped PDF/QTI download and save, reload persistence, mobile checks, no
page errors, and clean PDF/QTI inspection.

## Rollback Plan

Revert the compact-projection adapter and UI mapping while preserving existing
correction-session persistence and replay behavior. Keep file actions
conservative if the projection is unavailable.

## Stop Conditions

- Stop if Sir Convert Task 373 is not implemented, independently approved, or
  has not emitted a stable versioned projection contract/OpenAPI surface.
- Stop if implementing this PR would require Skriptoteket to define producer
  answer-key semantics locally.
- Stop if file readiness becomes coupled to question-list labels instead of
  Sir Convert target readiness and replay artifact references.
- Stop if any implementation would reintroduce accepted-current-state export as
  authoring or correction state.
