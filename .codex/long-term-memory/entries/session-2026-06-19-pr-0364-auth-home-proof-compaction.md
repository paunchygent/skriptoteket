---
type: agent_session_long_term_memory_entry
id: session-2026-06-19-pr-0364-auth-home-proof-compaction
status: active
created: 2026-06-19
---

# Session 2026-06-19 PR-0364 Authenticated Home Proof Compaction

## Scope

This entry retains the detailed PR-0364 authenticated-home implementation and
verification notes that were compacted out of `.codex/handoff.md` when PR-0371
public landing implementation became the active session focus.

## Retained PR-0364 State

- `PR-0364` is done and approved by `REV-PR-0364`.
- Authenticated `/` is app-first with primary shelves for Klassrumskartan,
  Provhantering `?mode=exam`, Ljudtranskribering `?mode=transcript`,
  Dokumentkonvertering, and Kodredigerare.
- Runtime implementation touched:
  - `frontend/apps/skriptoteket/src/views/HomeView.vue`
  - `frontend/apps/skriptoteket/src/components/home/HomeWorkAppsSection.vue`
  - `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`
  - `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`
  - `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts`
  - `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.spec.ts`
- Post-deploy corrections replaced CSS graph-paper sketches with app image
  identities and Swedish labels, removed generic helper phrases, removed
  `Arbetsappar`/`Direkt i appen`, and removed stale `Mina körningar`
  sidebar/help-index entries.
- Rejected PR-0364 card-grid and service-foyer attempts were deleted at user
  request on 2026-06-19 and must not be reintroduced.

## Retained PR-0364 Verification

- Red-first loader proof:
  `pdm run fe-test -- --run src/composables/home/useHomeDashboard.spec.ts`
  failed because the default authenticated-home loader still called
  `/api/v1/my-runs`, `/api/v1/favorites?limit=5`, and
  `/api/v1/me/recent-tools?limit=5`.
- Focused green tests:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts`
  passed with 7 tests.
- Additional gates passed:
  `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`,
  `pdm run handoff-validate`, `git diff --check`, and
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`.
- Authenticated browser proof used the HuleEdu auth-integration export at
  `/Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json`
  and the Docker/Gateway lane with `skriptoteket_web` resolvable as
  `http://skriptoteket-web:8000`.
- Retained proof artifacts:
  - `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/manifest.redacted.json`
  - `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface-visual-identity/20260619T135320Z/manifest.redacted.json`
  - `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface-no-my-runs-nav/20260619T174051Z/manifest.redacted.json`
