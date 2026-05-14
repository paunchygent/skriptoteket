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
- Date: 2026-05-14.
- Branch: `main`.
- Current lane: `PR-0325` Exam Converter authenticated runtime UI and save
  remediation under `ST-21-03` is ready.
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
  running, and keeps success/partial/failed result-strip states as component
  scaffold states for the later runtime slice. Gateway submit/poll/result
  mapping, real upstream progress/ETA consumption, question/file/report modes,
  download, and save remain out of scope.
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
- `pdm run lint`
- `pdm run typecheck`
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
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Browser proof on `http://127.0.0.1:5173/apps/documents.conversion_hub`
  confirmed the visible local intake copy and combined-drop announcement.
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010|PublicConversionGrantV1|PublicArtifactReadLeaseV1" src/skriptoteket/web/static/spa`
  (no matches)
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- PR-0322 live proof: submit/status/result/manifest/download passed; cookie
  parity passed; invalid target/missing `.dxe`/unsupported root/missing job/rate
  limit/expired grant probes failed closed; no account-owned rows were created.
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
- `PR-0313` still needs real iPhone confirmation before final `done` closeout.
- `PR-0315` remains a separate local lane; do not mix any follow-up review or
  publication work for it into the `PR-0317` diff without an explicit decision.
- `ST-27-09` still has older ready PR slices (`PR-0297`, `PR-0298`) whose
  implementation appears delivered or superseded by later fixed-seat work
  (`PR-0304`, `PR-0310`). Reconcile separately before starting unrelated
  fixed-seat runtime work.
- BF25/G104 now prioritizes stronger overlap-rule rotation and keeps valid
  `Håll isär` separation with a 10.5 mean-distance floor.
## Next Steps
- Continue `PR-0325` by proposing the next slice first. Do not
  implement UI until that slice's mockup/sketch, behavior, affordances,
  component choices, recommendation rationale, and test-code behavior-spec
  shape are explicitly approved. Runtime/save wiring follows the approved UI
  structure and remains separate.
- Rerun `PR-0324` only after `PR-0325` lands and is reviewed.
- Do not reopen the public grant/read-lease lane unless HuleEdu or Sir Convert
  changes the accepted contract.
