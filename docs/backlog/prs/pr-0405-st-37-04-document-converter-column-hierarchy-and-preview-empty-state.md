---
type: pr
id: PR-0405
title: "ST-37-04 Document Converter column hierarchy and preview empty state"
status: done
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
stories:
  - "ST-37-04"
tags:
  - frontend
  - document-converter
  - layout
  - copy
dependencies:
  - "PR-0397"
  - "PR-0402"
  - "PR-0403"
  - "PR-0404"
acceptance_criteria:
  - "Given either Document Converter mode is open, when the workspace renders, then `Källa`, `Konvertering`, and `Resultat` use the same distinct column-header treatment and are visually separated from controls and field labels."
  - "Given no result exists yet, when the operations column renders the filename field, then the editable field is disabled, empty, and shows the placeholder `filnamn` instead of the value `Resultat`."
  - "Given no preview exists yet, when the result column renders, then the preview pane shows a preview-shaped empty state labeled `Förhandsvisning` and does not repeat source instructions such as `Välj en fil som du vill konvertera.`"
  - "Given `HTML/CSS-projekt` is open, when the middle column renders, then it uses the same `Konvertering` column title as `Filkonvertering` while keeping mode-specific controls as field labels below it."
  - "Given a real result exists, when filename, artifact selection, download, save, or preview controls render, then their ownership remains unchanged from `PR-0397` and `PR-0403`."
---

# PR-0405: ST-37-04 Document Converter Column Hierarchy And Preview Empty State

## Problem

The current Document Converter workbench uses the same visual scale for
column titles and lower-level field labels in parts of the layout. In
`Filkonvertering`, `Källa` and `Konvertering` can read like ordinary field
labels while `Resultat` uses a different treatment in the preview panel. In
`HTML/CSS-projekt`, the middle column still says `Utdatainställningar`, so the
left/middle/right grammar from `PR-0397` is not fully stable across modes.

The empty filename field also uses `Resultat` as the fallback value before a
real result exists, which can imply that the field is where results appear.
The empty preview repeats the source instruction instead of looking like the
place where the generated document preview will appear.

## Goal

Tighten the route-visible hierarchy and empty-state semantics without changing
the conversion flow:

- stable column headers: `Källa`, `Konvertering`, `Resultat`;
- lower-level field labels remain visually subordinate;
- empty filename field shows placeholder `filnamn` and no fake result value;
- empty preview is a quiet preview-shaped surface labeled `Förhandsvisning`;
- both `HTML/CSS-projekt` and `Filkonvertering` use the same column grammar.

## Non-goals

- No backend, API, artifact, save, or download contract changes.
- No new conversion modes or output options.
- No changes to preview touch/pinch behavior from `PR-0403`.
- No shared cross-app filename primitive extraction.
- No production deploy, commit, or push unless separately requested.

## Implementation plan

1. Done: add focused red-first frontend specs for both modes:
   - shared column-header copy and ownership;
   - empty filename placeholder/value behavior;
   - preview empty state copy and absence of repeated source instructions.
2. Done: introduce a small route-local column-heading structure/style reused by the
   source, operations, and result columns.
3. Done: separate the preview title from the filename fallback so `Resultat` does not
   become an editable filename stem before a real artifact exists.
4. Done: replace the result empty-state text block with a token-driven page-preview
   silhouette labeled `Förhandsvisning`.
5. Done: preserve existing result-ready actions, artifact selector, PDF viewport,
   zoom controls, and source/operations/preview ownership.
6. Done: send the implementation through independent retained review and
   record approval in `REV-PR-0405`.

## Test plan

- Red-first focused Vitest:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`
- Green focused Vitest for the same files.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- Live browser proof or screenshot proof for both modes through the
  authenticated shared-auth route; record exact artifact path in handoff.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Progress

- Created this governed PR slice after product review approved the final copy:
  `Källa`, `Konvertering`, `Resultat`, filename placeholder `filnamn`, and
  empty preview label `Förhandsvisning`.
- Added red-first frontend assertions in
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts`
  and
  `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`.
- Updated the route so `Källa`, `Konvertering`, and `Resultat` are stable
  column headers in both modes; `HTML/CSS-projekt` no longer uses
  `Utdatainställningar` as the middle-column title.
- Split the filename source from the preview panel title so empty results no
  longer seed `Resultat` into the editable filename field.
- Replaced the preview empty-state text block with a token-driven page
  silhouette labeled `Förhandsvisning`.
- Updated retained browser proof helpers to assert filename ownership through
  the operations filename field instead of the preview header.
- Corrected the final header-band CSS so the `Resultat` heading and its
  divider align with `Källa` and `Konvertering` even when the preview zoom
  toolbar is visible.
- Toned down the shared column headers from the app-title-like `text-lg` /
  `extrabold` treatment to approved `text-base` / `bold` tokens and reduced
  the aligned header band height from `4.5rem` to `3.75rem` in both modes.
- By operator request, committed and pushed the ready implementation to
  `main` as `5cf76513`, then deployed it on Hemma before the independent
  review loop.
- Approved by retained review `REV-PR-0405` after the final CSS-only
  typography/height adjustment was recorded and reviewed.

## Verification notes

- Red-first evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  failed before implementation because the shared column-title test ids were
  absent and the preview empty state still rendered the source instruction.
- Focused green evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterProjectResult.spec.ts`
  passed with 33 tests.
- Additional focused frontend evidence:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterFileApi.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts`
  passed with 9 tests.
- Script-surface proof:
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py` passed
  with 7 tests after updating the retained proof helpers.
- Frontend gates: `pdm run fe-type-check`, `pdm run fe-lint`, and
  `pdm run fe-build` passed. `fe-build` kept the existing large-chunk warnings.
- Backend/script gates: `pdm run lint` and `pdm run typecheck` passed.
- Docs gate: `pdm run docs-validate` passed.
- Live shared-auth proof:
  `pdm run python -m scripts.authenticated_home_work_apps --base-url http://localhost:5173 --artifact-root .artifacts/authenticated-home-work-apps --timeout-seconds 120`
  passed with retained artifacts at
  `.artifacts/authenticated-home-work-apps/20260629T005352Z/`.
- Final header-alignment correction verification:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  passed with 13 tests. The final CSS-only alignment edit did not rerun the
  shared-auth browser proof because it changes presentation geometry only and
  the proof lane is currently susceptible to HuleEdu login rate limiting.
- Final header typography correction verification:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterResultPanel.spec.ts`
  passed with 13 tests. This CSS-only token/height edit also did not rerun the
  shared-auth browser proof for the same rate-limit reason.
- Live proof note: two earlier proof reruns hit the HuleEdu auth
  `RATE_LIMIT` guard (`limit=5`, `window_seconds=60`) before the final green
  run. The rate-limit resilience concern is real but remains a separate
  proof-infrastructure follow-up; this slice does not weaken or bypass the
  HuleEdu browser-session ceremony.
- Publish/deploy proof: `git push origin main` advanced `origin/main` to
  review follow-up `5603b8cc`; `pdm run hemma-deploy` launched remote PID
  `1934005` with log
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260629-014917.log`;
  `pdm run hemma-deploy-monitor -- /home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260629-014917.log`
  showed `Seating export deploy/readiness gate passed.`; Hemma checkout was
  `5603b8ccb2d9f60d37f50536203f54f8c96d5f70`; public
  `https://skriptoteket.hule.education/healthz` returned healthy JSON.
- Retained review: `REV-PR-0405` approved the current worktree, including the
  final `text-base` / `bold` / `3.75rem` shared column-header tweak, without a
  shared-auth Playwright rerun because the operator explicitly requested no
  auth-heavy rerun for the CSS-only presentation change after HuleEdu
  `RATE_LIMIT` pressure.

## Rollback plan

Revert this slice to restore the prior component headings, `Resultat` fallback
filename value, and text-only preview empty state while preserving all
conversion, save, download, and preview-touch behavior.
