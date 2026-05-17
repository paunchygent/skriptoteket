---
type: agent_session_long_term_memory_entry
id: session-2026-05-17-pr-0325-pr-0326-exam-converter-history
status: active
created: '2026-05-17'
---

# PR-0325 / PR-0326 Exam Converter History

This entry compacts durable Exam Converter history so `.codex/handoff.md` can
stay focused on the current `PR-0326` implementation lane.

## PR-0325 Retained State

- `PR-0325` implemented the authenticated Exam Converter host/runtime/save
  remediation needed before rerunning blocked `PR-0324`.
- `ExamConverterAuthenticatedView.vue` became a composition-only host frame
  backed by workflow rail and workspace shells.
- The authenticated surface added browser-local `.dxe` source selection,
  optional corrected-result PDF intake, invalid-file rejection, selected file
  state, output-format toggles, and multiple-`.dxe` rejection.
- Runtime submission now sends the selected `.dxe`, optional result PDF,
  Swedish artifact language, and selected PDF/QTI targets through the HuleEdu
  Gateway Sir Convert client.
- The runtime bridge polls queued/submitted/running/processing jobs with the
  returned correlation ID and maps terminal complete/partial/blocked/failed
  outcomes to the compact result strip.
- The review shell loads Sir Convert `ir_json` and `migration_manifest`,
  projects them through `digiexamIrReviewParser.ts`, and renders read-only
  `Frågor`, `Filer`, and `Rapport` modes.
- Review projection refinement corrected flerval labels, showed source-backed
  alternatives, and exposed `Lucktext` gap/image structure without changing
  missing `Facit`/`Poäng` counts.
- A local review-decision gate added short `Granska` / `Godkänn` actions for
  actual `Facit`/`Poäng` gaps. This accepted-current-state path is separate
  from the later reviewed-completion overlay path.
- File actions use `useExamConverterFileActions.ts` to download named artifacts
  through the HuleEdu Gateway and save them through the owner-scoped user-file
  endpoint.
- `saveMetadata.ts` normalizes `sha256:<hex>` to the backend save handler's
  64-character SHA-256 value.
- The Task 306 consumer sync regenerated `sirConvertOpenapi.d.ts`, added a
  reviewed-completion lineage fixture, removed obsolete terminal-result
  `target_availability` parsing, replaced local schema-version literals with
  constants, and removed Tailwind's production Vite plugin from Vitest's jsdom
  config.
- Sir Convert still needs an additive progress/ETA contract before
  Skriptoteket can show real upstream long-running progress instead of
  browser-local status.

## PR-0325 Retained Verification

- Focused backend public converter and upstream-client tests passed.
- Focused authenticated Exam Converter Vitest slices passed through runtime,
  review, files-action, and Sir Convert Gateway client coverage.
- `NODE_OPTIONS=--trace-deprecation` focused frontend tests passed without the
  prior Node `DEP0205` warning.
- Focused backend user-file save tests passed.
- `pdm run fe-type-check`, `pdm run fe-lint`, docs validation, handoff
  validation, and `git diff --check` passed for the PR-0325 closeout.
- Live authenticated validation passed with local Sir Convert at
  `http://127.0.0.1:8085` and the HuleEdu Gateway `/sir-convert` edge enabled:
  submit, result, artifact manifest, `migration_manifest`, and `ir_json` all
  returned through the authenticated browser flow.
- Fresh live proof after rebuilding Sir Convert image
  `sha256:a2deed73aceab89acd1be3d1153ca1147388db683133aa391afeee8f68d1d7b0`
  and using byte-distinct source
  `.artifacts/pr-0325-live/fresh-inputs/1811577114-ekologiprov-v-49-25d-e-fresh-probe.dxe`
  passed: after `Godkänn`, `examnet_pdf` and `qti_package` became
  `Godkänt för export`; QTI saved to user files; generated PDF was retained at
  `.artifacts/pr-0325-live/fresh-examnet-import.pdf`.

## PR-0326 Retained State

- `PR-0326` was created as the next authenticated implementation slice under
  `ST-21-03`.
- First submit must request advisory local LLM completion with
  `completion_mode=local_llm_suggest_missing_machine_marked`,
  `remote_provider_policy=forbidden`,
  `result_pdf_usage=correct_machine_marked_answers_only`, and
  `manual_follow_up_policy=emit_item_addressable_report`.
- Skriptoteket must fetch and parse `answer_key_completion_report`,
  `effective_ir_json` when available, `bundle_manifest`, `target_readiness_report`,
  `ir_json`, and `migration_manifest`.
- The UI must present the output as AI-suggested `facit`, not source truth, and
  distinguish no-candidate-needed, suggested-valid, invalid, provider-unavailable,
  source-already-keyed, and manual-follow-up states.
- Teacher review must support accept unchanged, reject/manual follow-up, optional
  edit-before-accept where the approved UI slice allows it, and a compact
  accept-all-suggestions affordance for valid pending candidates.
- Reviewed decisions must produce `reviewed_completion_answer_key` overlay
  entries with candidate lineage and `answer_payload`; they must not be encoded
  as `manual_answer_key`, `review_decision`, or `effective_item_patch`.
- Second submit must use
  `completion_mode=local_llm_apply_missing_machine_marked_with_review`,
  `ingestion_overlay_filename=digiexam-ingestion-overlay.json`, and
  `ingestion_overlay_policy=apply_teacher_overlay`.
- PDF/QTI readiness must follow Sir Convert's returned manifest/readiness state;
  Skriptoteket may not locally mark files ready just because a teacher accepted
  an advisory suggestion.
