# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history to
  `.codex/long-term-memory/entries/` first.
## Snapshot
- Date: 2026-06-10.
- Branch: `main`.
- Docs-only cross-repo STT planning added `ST-21-05` through `ST-21-07` under
  EPIC-21 with approved retained review `REV-ST-21-05`; no transcript runtime
  implementation is authorized until the upstream blockers are resolved.
- Current lanes under `ST-21-03`: `PR-0330` is canceled after `PR-0338`;
  `PR-0331` is Codex-owned reviewed AI-facit export integrity and is ready.
- Current state: `ADR-0085` accepted; `PR-0318` through `PR-0323` done;
  `REV-PR-0318` through `REV-PR-0322` approved; Sir Convert `TASK-292` done;
  `PR-0325` live evidence exists; `PR-0326`, `PR-0327`, and `PR-0328` are
  implemented; `PR-0329` is done; `PR-0330` is canceled as a reviewed-AI phone
  strategy; `PR-0331` is ready with retained Hemma/public proof.
- Prior PR-0310 through PR-0314 history:
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`.
- Prior PR-0325 through PR-0326 live-proof history:
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`.
- Prior PR-0326 through PR-0331 AI-facit history:
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0326-through-pr-0331-ai-facit-review-history.md`.
## Status
- Earlier ST-21-03 / PR-0325 through PR-0331 proof and contract history is
  retained in the governed PR/reference docs and long-term memory entries above.
  Keep the fresh-source/idempotency lessons from those proofs for future
  artifact checks.
- Corrected `PR-0331` item-type contract: matching and single-/multi-gap
  `Lucktext`/open-cloze are supported in the source-neutral IR and QTI/PDF
  export contract. PDF may render gapped items as free text, but accepted
  gapped key values must still be included. Do not treat current DigiExam
  adapter restrictions as product limitations.
- `PR-0331` governance correction: teacher-owned correction/edit workflow is
  not a product decision made inside `PR-0331`. Accepted `ADR-0086` and
  independent `PR-0332` now govern stems/prompts, points, choice keys, and
  gapped/open-cloze teacher correction overlays. Matching remains future work
  until Sir Convert Task 332 provides a real matching-capable producer.
- `ADR-0086` is accepted and `REV-PR-0332` is approved. Task 322 and Task 323
  remain useful producer prerequisites; Task 324's matching route is
  superseded/abandoned by accepted Sir Convert ADR-0011 and completed Task 327.
  Sir Convert Task 333 and HuleEdu TASK-0567 are now landed for non-matching
  unified corrections. `PR-0332` must keep using only the unified HuleEdu
  source-state/apply routes and must not preserve the old Task 324 matching
  route as a bridge, shim, alias, wrapper, adapter, or compatibility layer.
- `PR-0332` is done as the non-durable unified-correction consumer/projection
  slice. It consumes only Task 333-supported non-matching correction families:
  `point_correction`,
  `manual_choice_answer_key`, `manual_gap_open_cloze_answer_key`, and
  `item_text_patch`. `manual_matching_answer_key` stays blocked until Sir
  Convert Task 332 issues matching-capable producer state.
- `ADR-0087` is accepted by user-lead (2026-05-19) and `REV-ST-21-04` is
  approved. `ST-21-04` is ready and owns durable authenticated teacher
  correction sessions: Skriptoteket persists source-bound correction intents;
  Sir Convert remains stateless and applies the complete supported persisted
  set during replay/projection/export.
- `PR-0333` is done: Skriptoteket now has the durable correction-session
  aggregate, owner/job-scoped PostgreSQL persistence, active-target constraints,
  exact source-binding round-trip, stale-version `CONFLICT` behavior, and
  migration coverage. Retained review `REV-PR-0333` is `changes_requested`:
  replay/conflict-family fixes passed, but per-question AI-seeded "Spara facit"
  still bypasses the AI review-decision workflow.
- `PR-0334` is done: authenticated owner-scoped correction-session read/upsert/
  revert routes now expose the aggregate, stale writes map to `409 Conflict`,
  and Skriptoteket OpenAPI/frontend types are regenerated. `PR-0335` replay
  orchestration is done.
- `PR-0335` is done: non-UI replay orchestration loads Skriptoteket persisted
  active intents, issues fresh HuleEdu Sir Convert Gateway source state,
  validates binding/fingerprints, submits the complete deterministic set to
  unified apply, and marks projection freshness unavailable/stale without
  claiming browser-local truth.
- `PR-0336` is done: the authenticated Exam Converter UI persists supported
  teacher changes through Skriptoteket correction-session APIs, restores saved
  active intents after navigation/reload, renders replayed points/text/keys/
  review decisions/candidate suppression/counters/file readiness, keeps drafts
  distinct and matching blocked, and the teacher-visible Swedish copy was
  audited to avoid internal projection/replay/session/Sir Convert terminology.
- `PR-0338` is done:
  `docs/backlog/prs/pr-0338-st-21-04-ai-prefill-editor-and-replay-artifact-authority.md`.
  AI candidates seed only the normal facit editor, `submission_origin`
  provenance is computed at durable-intent build time, selection advances only
  after readback/replay/projection, and corrected file actions require
  replay-provided artifact references.
- `PR-0339` is done:
  `docs/backlog/prs/pr-0339-st-21-04-sir-convert-replay-artifact-reference-contract.md`.
  Sir Convert returns replay-derived `artifact_key` values on exportable
  correction target readiness rows; HuleEdu passes through; Skriptoteket only
  consumes that replay authority for corrected downloads/saves.
- Latest PR-0339 UI refinement: accepted unchanged AI-prefilled facit keeps
  `accepted_advisory_candidate` provenance after replay and uses the Lucide
  Bot symbol in the list/inspector; teacher-authored and teacher-edited keys keep
  the normal check/selected-choice indicator. Report warnings are diagnostics,
  not remaining teacher actions.
- `PR-0340` is done:
  `docs/backlog/prs/pr-0340-st-21-04-ai-suggestion-outcome-reporting.md`.
  It replaces the prominent raw `Konverteringsvarningar` count with
  teacher-relevant AI suggestion outcome counts and item mapping; raw technical
  source notes are not shown in the report summary. Saved choice facit now
  renders as selected alternative rows with text, not detached numbers.
- `PR-0341` is done:
  `docs/backlog/prs/pr-0341-st-21-04-authoring-export-boundary-separation.md`.
  Accepted-current-state export is export-owned, not teacher authoring state.
  Skriptoteket removed `review_decision` / `accept_current_state_for_export`
  from durable correction sessions, UI gates, replay requests, fixtures, and
  tests. Migration `b3e7a1c9d4f2` deactivates active legacy `review_decision`
  rows and drops `conflict_family`; local and Docker DBs are upgraded to that
  head. Missing facit/poäng stays blocked until real authoring corrections are
  saved.
- `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` was regenerated
  from the current Sir Convert v2 OpenAPI snapshot for PR-0332. Skriptoteket's
  own `frontend/apps/skriptoteket/src/api/openapi.d.ts` was regenerated for
  `PR-0341` after removing `review_decision` / `conflict_family` from the
  local correction-session API surface.
- `PR-0337` is done:
  `docs/backlog/prs/pr-0337-st-21-04-correction-session-browser-and-artifact-proof.md`.
  Live proof retained at
  `.artifacts/playwright-pr-0337-correction-session-live/20260520T001258Z`.
  It proves local drafts do not unlock files, submitted supported corrections
  survive reload through Skriptoteket readback/Sir Convert replay, final target
  readiness exposes `correction_replay_*` artifact keys, and corrected PDF/QTI
  downloads and saves use only those replay-scoped references while preserving
  uploaded-source-derived target filenames.
- `PR-0331` evidence and cleanup details are retained in the PR/reference docs;
  current proof script is `scripts/playwright_pr_0331_reviewed_ai_facit_live.py`.
- `PR-0342` is implemented locally:
  `docs/backlog/prs/pr-0342-st-21-05-transcript-intake-and-gateway-lifecycle-client.md`.
  It adds authenticated Conversion Hub transcript intake, speaker controls,
  HuleEdu Gateway submit/status/result/artifact/cancel client methods, and
  false-success `transcript_json` rejection. No public/no-login/direct Sir
  Convert path, local STT/diarization, durable transcript save, or formatter
  output was added.
## Verification
- Prior PR-0331 through PR-0336 verification details are retained in their
  governed PR/review docs and long-term memory entries.
- Current PR-0339/PR-0340 verification details are retained in their governed
  PR docs; PR-0340 passed focused Vitest, typecheck, lint, build,
  UI-fixture Playwright smoke, docs/handoff validation, and `git diff --check`.
- Current PR-0341 authoring/export boundary separation passed its retained
  backend, migration, DB-upgrade, container-health, focused frontend, and
  typecheck gates; exact commands are retained in the PR doc.
- Current PR-0337 live proof passed:
  `pdm run python -m scripts.playwright_pr_0337_correction_session_live --base-url http://127.0.0.1:5173 --dotenv .env --timeout-seconds 580`.
  Evidence:
  `.artifacts/playwright-pr-0337-correction-session-live/20260520T001258Z`.
  It retained zero enabled draft downloads/saves, six accepted final
  corrections with no rejected entries, ready PDF/QTI target rows with
  `correction_replay_examnet_pdf` / `correction_replay_qti_package`, replay-key
  download/save `200` responses, uploaded-source-derived suggested/saved
  filenames, clean PDF/QTI forbidden-text scans, PDF point correction evidence,
  and QTI prompt/correctResponse evidence.
- Previous PR-0332 broader correction slice passed focused Vitest, typecheck,
  lint, build, docs/handoff validation, and `git diff --check`.
- Current `PR-0331` generated Sir Convert DTO diff proof, script-surface proof,
  and Hemma/public artifact proof are retained in the PR/reference docs.
- Current ST-21-05 through ST-21-07 docs guard:
  `pdm run test tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  failed red on missing exact Gateway-only/blocker/review constraints, then
  passed after docs/review remediation.
- Current PR-0342 local implementation proof:
  `pdm run fe-test -- src/api/sirConvertGateway/transcriptOptions.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts`
  passed with 8 tests; `pdm run fe-type-check`, `pdm run fe-lint`,
  `pdm run docs-validate`, and `git diff --check` passed. Live authenticated
  Hule/Sir end-to-end proof was not run in this slice.
## How to Run
```bash
pdm run fe-test -- src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts src/api/sirConvertGateway/completionContract.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```
## Known Issues / Risks
- The `PR-0331` live proof script now forces fresh Sir Convert idempotency keys
  and uses Playwright request context for public-edge artifact reads; keep this
  behavior so future proofs cannot pass by replaying stale advisory jobs.
- Exported artifacts must not expose internal fallback/parser diagnostics.
- Teacher edit of prompts/stems and correct keys is not governed by `PR-0331`;
  accepted `ADR-0086` and done `PR-0332` own non-durable correction controls;
  accepted `ADR-0087`/ready `ST-21-04` own durable correction sessions.
- Future PR-0342 live proof must use the authenticated HuleEdu browser-session
  ceremony and verify Gateway-owned `transcript_json` download/cancel through
  `/sir-convert/v2/convert/...`; do not claim public deployment proof from
  local Vitest.
## Next Steps
- Review PR-0342 locally, then run authenticated shared-stack/live Gateway proof
  when the HuleEdu TASK-0570 edge is available in the target environment.
