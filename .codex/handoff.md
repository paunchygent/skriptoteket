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
- Date: 2026-05-15.
- Branch: `main`.
- Current lane: `PR-0325` Exam Converter authenticated runtime UI and save
  remediation under `ST-21-03`; Slice 6 exposed an accepted-state export gap.
- Current state: `ADR-0085` is accepted; `PR-0318`, `PR-0319`, `PR-0320`,
  `PR-0321`, `PR-0322`, and `PR-0323` are done. Retained reviews
  `REV-PR-0318` through `REV-PR-0322` are approved. Sir Convert `TASK-292`
  completed the public verifier/read-lease runtime needed by `PR-0322`.
- Prior PR-0310 through PR-0314 history was compacted to
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`.
## Status
- `ST-21-03` defines the public one-time Exam Converter lane plus the
  authenticated artifact workflow under `EPIC-21`.
- Public lane authority is now settled: HuleEdu mints only
  `PublicConversionGrantV1`; Sir Convert verifies that grant, creates
  public-grant-owned jobs/artifacts, and issues `PublicArtifactReadLeaseV1`;
  Skriptoteket keeps both authorities server-side.
- `PR-0323` aligned the Skriptoteket consumer with the grant-only HuleEdu shape:
  `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/public_exam_converter_grants.py`
  no longer expects HuleEdu read leases, and
  `public_exam_converter_sir_convert_client_v2.py` owns parent-grant/read-lease
  Sir Convert calls.
- `PR-0322` live proof is approved in
  `docs/backlog/reviews/review-pr-0322-exam-converter-live-upstream-public-grant-proof.md`.
  Local proof artifacts are ignored under `.artifacts/pr-0322-live-proof/`.
- `PR-0324` authenticated proof is blocked by retained
  `docs/backlog/reviews/review-pr-0324-exam-converter-authenticated-end-to-end-proof.md`.
  Proof preflight found no authenticated bespoke Exam Converter host surface,
  no authenticated DigiExam artifact-bundle runtime surface, and no
  save-to-user-files path for downloaded Sir Convert named artifacts.
- Created `docs/backlog/prs/pr-0325-st-21-03-exam-converter-authenticated-runtime-ui-and-save-remediation.md`
  as the narrow remediation before rerunning `PR-0324`.
- `PR-0325` UI work is gated by
  `docs/reference/ref-exam-converter-ui-content-model-v1.md`: direct Swedish
  copy, progressive disclosure, no summary cards, no visible service jargon,
  and token-correct Klassrumskartan-style workspace patterns before component
  layout changes continue.
- Selected UI direction is retained in
  `docs/mockups/st-21-03-exam-converter-authenticated-progressive-review/README.md`;
  use it for layout/components, but do not implement the rejected bottom
  stretched `Visa filer` panel.
- Each Exam Converter UI area must be a separate approved slice before
  implementation: send a focused mockup/sketch, behavior notes,
  component/affordance choices, recommendation rationale, and clarifying
  questions; wait for explicit product-owner approval.
- Each approved UI slice also needs focused test code whose module header and
  test names describe what the slice should do, expected behavior,
  progressive-disclosure boundary, and recommended component/affordance shape.
- Slice 1 is implemented: `ExamConverterAuthenticatedView.vue` is now a
  composition-only host frame with `ExamConverterWorkflowRailShell.vue` and
  `ExamConverterWorkspaceShell.vue`; no runtime/result/file/question/report
  behavior is present in this slice.
- Slice 2 is implemented and extended through the local intake affordance pass:
  authenticated Exam Converter now has browser-local `.dxe` source-file
  selection, optional `Valfritt rättat prov` PDF selection, invalid-file
  rejection, selected filename/size rail state, remove-to-idle behavior,
  output-format true/false toggles, combined `.dxe` + PDF drop placement, and
  multiple-`.dxe` rejection. Submit/runtime remains out of scope.
- Slice 3 is implemented: authenticated Exam Converter now enables
  `Starta konvertering` only after a `.dxe` and at least one target are
  selected, shows `Konverterar provet...` in a compact result strip with
  moving stage/progress visualization, locks local intake affordances while
  running, and keeps success/partial/failed result-strip states ready for
  runtime mapping.
- Slice 4 is implemented: authenticated Exam Converter now submits the selected
  `.dxe`, optional `Valfritt rättat prov` PDF, Swedish artifact language, and
  selected PDF/QTI targets through the existing HuleEdu Gateway Sir Convert
  client, polls queued/submitted/running/processing jobs with the returned correlation
  ID, reads the terminal result, and maps complete/partial/blocked/failed
  outcomes to the approved compact result strip. Real upstream progress/ETA
  consumption, artifact manifest rendering, question/file/report modes,
  download, and save remain out of scope.
- Slice 5 is implemented: authenticated Exam Converter loads Sir Convert
  `ir_json` and `migration_manifest` through the HuleEdu Gateway artifact
  client, projects them through `digiexamIrReviewParser.ts`, and renders
  `Frågor`, `Filer`, and `Rapport` as a read-only progressive inspection
  surface. It shows missing-only labels (`Facit`, `Poäng`) under `Saknas`,
  uses one `Fråga` column with number plus prompt preview, treats free-text
  `manual_marking_required` as normal for this slice, uses lucide
  warning/success symbols for row status, avoids local review/edit state, and
  treats Sir Convert `blocked` bundles with real missing data as partial
  conversion rather than runtime failure. A Sir Convert `partial` bundle caused
  only by normal free-text manual marking stays teacher-visible as a converted
  exam.
- Slice 5 review projection refinement is implemented: flerval rows now use
  `Flerval: ett val`, `Flerval: flera val`, and `Flerval: matchning` instead
  of `Enval`; the selected-question detail pane shows source-backed
  alternatives; and `Lucktext` detail shows gap count plus embedded image
  structure from the IR without changing missing `Facit`/`Poäng` counts.
- Slice 6 is partially implemented: authenticated Exam Converter now shows a
  review-decision gate with short `Granska` / `Godkänn` actions when actual
  `Facit`/`Poäng` gaps exist, keeps long action explanations in help
  affordances, and clears acceptance on new/reset flows. Live audit showed
  that local `Godkänn` is not enough when Sir Convert has already returned
  blocked target files for accepted missing `Facit`/`Poäng`.
- Slice 6 save wiring uses `useExamConverterFileActions.ts` to download named
  artifacts through the HuleEdu Gateway and save them through the
  owner-scoped user-file endpoint; `saveMetadata.ts` normalizes
  `sha256:<hex>` to the 64-character value verified by the backend save
  handler.
- Sir Convert follow-up is required before real long-running ETA can be shown:
  DigiExam migration jobs that can exceed ten seconds need an additive
  progress/ETA contract (stage, bounded percent or step, optional ETA,
  stale/stalled/unknown semantics). Skriptoteket must consume that later instead
  of treating browser-local progress as authoritative.
- `PR-0325` explicitly points implementers at Klassrumskartan's app-export
  save precedent:
  `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py`
  and `apps_classroom_planner_export_job_contracts.py`.
- Story, epic, PR docs, `docs/index.md`, and this handoff are synced to
  `PR-0324` blocked / `PR-0325` ready state.
- PR-0316/PR-0317 smart seating history was compacted to
  `.codex/long-term-memory/entries/session-2026-05-13-pr-0316-pr-0317-smart-seating-history.md`.
## Verification
- `pdm run pytest tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py -q`
  (6 passed)
- `pdm run fe-test -- --run src/views/apps/ExamConverterPublicView.spec.ts src/views/PublicAppHostView.spec.ts src/views/AppHostView.spec.ts`
  (7 passed)
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts`
  (18 passed)
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedConversionSlice.spec.ts`
  (25 passed)
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedConversionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts`
  (29 passed)
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedConversionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/api/sirConvertGateway/client.spec.ts`
  (30 passed)
- `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts`
  (26 passed)
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts`
  (9 passed; verified flerval alternatives, corrected type labels, and
  `Lucktext` gap/image detail)
- `pdm run pytest tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py -q`
  (3 passed)
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Browser proof on `http://127.0.0.1:5173/apps/documents.conversion_hub`
  confirmed the visible local intake copy and combined-drop announcement.
- Browser proof on `http://127.0.0.1:5173/apps/documents.conversion_hub`
  confirmed the authenticated Exam Converter route still renders after Slice 4;
  screenshot retained locally at
  `.artifacts/pr-0325-slice-4/authenticated-runtime-bridge.png`.
- Live validation with local Sir Convert running at `http://127.0.0.1:8085`
  and the HuleEdu Gateway `/sir-convert` edge enabled passed end to end:
  submit/result/artifact manifest/`migration_manifest`/`ir_json` all returned
  200 through the authenticated browser flow, with screenshots retained under
  `.artifacts/pr-0325-live/`.
- Slice 6 live validation with local Sir Convert running at
  `http://127.0.0.1:8085` passed through the authenticated browser flow:
  a DXE with one missing `Facit` showed `Granska` / `Godkänn`, kept QTI
  `Hämta`/`Spara` disabled before `Godkänn`, enabled and saved QTI after
  `Godkänn`, and kept the upstream-blocked PDF row disabled. Screenshot:
  `.artifacts/pr-0325-live/slice-6-review-gate-files-save.png`.
- Follow-up live audit with `1811577114-ekologiprov-v-49-25d-e.dxe` exposed
  the current blocker: after `Godkänn`, Sir Convert still reports
  `examnet_pdf` as `blocked/manual_answer_key_required` and `qti_package` as
  `blocked/qti_validation_failed`, so both rows remain disabled. `Godkänn`
  needs a governed accepted-state export/rebuild path or an upstream
  best-effort artifact contract before `PR-0325` can close.
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010|PublicConversionGrantV1|PublicArtifactReadLeaseV1" src/skriptoteket/web/static/spa`
  (no matches)
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
## How to Run
```bash
pdm run pytest tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py -q
pdm run fe-test -- --run src/views/apps/ExamConverterPublicView.spec.ts src/views/PublicAppHostView.spec.ts src/views/AppHostView.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```
## Known Issues / Risks
- `PR-0325` is not closeout-ready until `Godkänn` is backed by a real
  accepted-state export path for target files blocked only by accepted missing
  `Facit`/`Poäng`. The prerequisite review-projection flaw is now fixed in
  Skriptoteket; the remaining gap belongs in the governed Sir Convert
  accepted-state export/readiness contract.
## Next Steps
- Finish `PR-0325` closeout: run the full frontend closeout gates
  only after resolving the accepted-state export gap behind `Godkänn`.
- Rerun `PR-0324` only after `PR-0325` lands and is reviewed.
- Do not reopen the public grant/read-lease lane unless HuleEdu or Sir Convert
  changes the accepted contract.
