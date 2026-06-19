---
type: review
id: REV-PR-0364
title: "Review: PR-0364 authenticated home work-apps surface"
status: approved
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
reviewer: "codex-independent-reviewer"
prs:
  - PR-0364
links:
  - ST-37-03
  - EPIC-37
  - PR-0361
  - PR-0362
  - PR-0363
  - REV-PR-0363
  - MOCK-pr-0364-authenticated-home-work-apps-surface
  - REF-service-shell-ux-realignment-plan-v1
  - REF-current-product-lanes-and-sir-convert-boundary-v1
  - REF-app-presentation-decomposition-and-naming-plan-v1
---

# Review: PR-0364 Authenticated Home Work-Apps Surface

## TL;DR

Approved. The follow-up runtime patch closes the prior code/test findings, and
the governed Docker-backed authenticated browser proof now passes using the
correct HuleEdu shared-auth export for the running Identity DB generation. The
prior mockup approval history and earlier runtime findings are retained below.

## Problem Statement

The signed-in home still presents Skriptoteket primarily as favorites, recent
tools, catalog/run/editor/admin actions, and a generic dashboard grid. After
`PR-0363`, the home can link directly to Exam Converter and Audio Transcription
without route decomposition, and the approved C2 mockup defines the app-first
target hierarchy.

## Proposed Solution

Review the amended `PR-0364` contract against the approved C2 mockup and the
actual mockup patch only. The deleted PR-0364 card-grid and service-foyer
mockups are not evidence. Approval requires that the HTML/CSS preview remains a
truthful design mockup, keeps runtime work bounded to authenticated home
composition unless `PR-0365` is explicitly absorbed, adds direct entries only
for the already-truthful lanes, keeps `Document Converter` non-clickable until a
reviewed route exists, removes `Mina körningar`/latest/recent home chrome, and
preserves flat secondary file/catalog/contribution affordances.

## Artifacts To Review

| File | Focus | Time |
|------|-------|------|
| `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md` | Approved C2 design direction, accepted/rejected patterns, Document Converter truth boundary | 8 min |
| `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html` | Concrete HTML/CSS mockup hierarchy, token usage, truthful links, and forbidden nested-card/open-link patterns | 10 min |
| `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md` | Scope, decisions, options, red/green plan, and proof gates | 20 min |
| `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-desktop.png` | Desktop geometry, equal-height shelves, and absence of clipping/overlap | 5 min |
| `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-mobile.png` | Compact-width geometry, stacking coherence, and absence of clipping/overlap | 5 min |

**Total estimated time:** ~56 minutes.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Put work-app lanes before old dashboard/platform sections on authenticated `/`. | This is the smallest route-visible step that centers the current product proposition without changing sidebar navigation yet. | [x] |
| Use current truthful route targets for the three runnable lanes. | `PR-0363` made Exam and Transcript directly linkable while preserving app-id compatibility. | [x] |
| Promote `Kodredigerare` into the app shelf. | The user explicitly rejected treating the editor as a form or nested secondary action. | [x] |
| Include `Document Converter` only with a truthful route stop condition. | The approved mockup includes the lane, but linking it to Exam/Transcript or catalog would be false. | [x] |
| Remove `Mina körningar`/latest/recent home chrome. | The user explicitly retired this dashboard path from the active home direction. | [x] |
| Preserve useful secondary surfaces without nested cards. | Files/catalog/contribution remain useful but must be flat ledger affordances below the app shelf. | [x] |
| Require Docker-backed HuleEdu browser-session proof. | Authenticated route-visible proof belongs to the implementation slice, not this static mockup review; the PR still keeps that gate. | [x] |
| Treat the approved C2 mockup as the design authority. | The user approved the latest C2 suggestion and requested a real HTML/CSS mockup before code. | [x] |

## Review Checklist

- [x] Scope is limited to authenticated home composition unless `PR-0365` is
  explicitly absorbed for sidebar/mobile navigation.
- [x] Route targets are exact and do not require route-table or app-id changes.
- [x] Document Converter handling cannot mislead teachers into Exam/Transcript,
  catalog, or the current compatibility host.
- [x] `Kodredigerare` is treated as an app shelf entry.
- [x] `Mina körningar`, latest-used apps, and recent-used vanity rows are
  absent from authenticated home.
- [x] Secondary surfaces are flat ledgers or equivalent un-nested structures.
- [x] Existing useful files/catalog/contribution/admin capabilities remain
  available below or outside the app shelf.
- [x] The implementation plan still requires red-first tests and live proof for
  the eventual runtime slice.
- [x] Stop conditions cover route/registry/backend/Sir Convert/HuleEdu/QTI/DOCX
  drift and the Docker service proof lane.
- [x] The approved C2 HTML/CSS mockup is the only mockup target; the deleted
  card-grid and service-foyer attempts are not treated as targets.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `approved`

### Mockup Review Pass - 2026-06-19

Decision: `approved`.

#### Scope Reviewed

- Governing docs: `AGENTS.md`, `.codex/rules/045-huleedu-design-system.md`,
  `PR-0364`, `REV-PR-0364`, the required design-skill references, and the
  scoped mockup README/HTML.
- Scoped worker patch only:
  `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md` and
  `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html`.
- Render evidence only:
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-desktop.png`
  and
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-mobile.png`.

#### Findings

No findings.

The approved state is grounded in the reviewed files and renders:

- `docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html:8`
  imports the canonical HuleEdu design tokens, and
  `index.html:10-26` maps local variables from those tokens rather than from a
  raw local palette.
- `index.html:80-85`, `index.html:160-164`, `index.html:317-327`, and
  `index.html:346-352` remove the all-caps/eyebrow treatment in favor of
  structure-first headings and sentence-case hierarchy.
- `index.html:166-181` and `index.html:297-327` define stable equal-height app
  shelves with border-led surfaces and no hard per-card shadows.
- `index.html:427-431` and `index.html:452-503` keep truthful runtime links for
  `Klassrumskartan`, `Exam Converter`, `Audio Transcription`, and
  `Kodredigerare`, while `Document Converter` remains visible but
  non-clickable.
- `index.html:505-519` keeps the lower continuation area as flat ledgers rather
  than nested cards.
- `README.md:30-48` and `README.md:52-59` now explicitly encode the approved
  direction, including the no-fake-Document-Converter-link rule and the banned
  `Mina körningar`/latest-used/nested-card patterns.
- The retained desktop and mobile renders show coherent layout, no overlap, no
  clipping, and the expected shelf/ledger hierarchy at both breakpoints.

Residual risk, not a blocker: this review covers only the static mockup lane.
The later runtime implementation still owes the governed red-first tests and
Docker-backed HuleEdu browser-session proof already specified in `PR-0364`.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run docs-validate
git diff --check
```

Results:

- `docs-validate`: passed.
- `git diff --check`: passed.

Worker evidence inspected without rerunning the render:

- `pdm run docs-validate`: reported passed before review-doc edits.
- `git diff --check`: reported passed before review-doc edits.
- Desktop render:
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-desktop.png`.
- Mobile render:
  `.artifacts/pr-0364-authenticated-home-work-apps-surface/design-rule-alignment-mobile.png`.

### Runtime Implementation Review Pass - 2026-06-19

Decision: `changes_requested`.

#### Scope Reviewed

- Governing docs and retained records:
  `AGENTS.md`,
  `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md`,
  `.codex/handoff.md`,
  the required frontend/testing skill references, and the retained mockup.
- Runtime patch:
  `frontend/apps/skriptoteket/src/views/HomeView.vue`,
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`,
  `frontend/apps/skriptoteket/src/components/home/HomeWorkAppsSection.vue`,
  `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`.
- Supporting contract/loader surface:
  `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts`.

#### Findings

1. Severity: `blocker`
   File: `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md:227`, `.codex/handoff.md:101`, `AGENTS.md:26`
   What is wrong: the required authenticated browser proof for the changed `/`
   route is still unresolved. The PR contract still requires Docker-backed
   HuleEdu browser-session proof, and the retained handoff explicitly records
   that the attempt is blocked by local identity-linking drift.
   Why it matters: this repo treats live proof for UI/route changes as a
   non-negotiable gate, and the user explicitly asked that this blocker not be
   treated as completed. I cannot mark the runtime slice approved while the
   governed proof remains missing, even though the blocker appears
   environmental rather than caused by the UI code itself.
   Concrete fix: resolve the local projection/RBAC identity-linking conflict,
   rerun the documented preflight/apply flow through the Docker-backed
   Gateway lane, then capture retained authenticated `/` proof at desktop and
   compact widths with the exact command, URL, viewport, and artifact paths
   recorded in `.codex/handoff.md`.
   Proof requirement: a clean rerun of
   `pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364.json`
   followed by the governed retained browser proof for authenticated `/`
   through the HuleEdu ceremony and Docker `skriptoteket_web` lane.

2. Severity: `medium`
   File: `frontend/apps/skriptoteket/src/views/HomeView.vue:25`, `frontend/apps/skriptoteket/src/views/HomeView.vue:111`, `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts:62`, `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts:130`
   What is wrong: the authenticated home no longer renders runs, favorites, or
   recent-tool sections, but it still calls `loadDashboard()`, which fetches
   `/api/v1/my-runs`, favorites, and recent tools as part of the initial `/`
   load path.
   Why it matters: retired dashboard endpoints are still coupled to the new
   app-first home. A failure from `/api/v1/my-runs` can still raise the shared
   `dashboardError` banner on `/`, and the route keeps paying for hidden
   network work that no longer drives visible state.
   Concrete fix: split a minimal authenticated-home loader, or parameterize
   `useHomeDashboard()` so `HomeView` only fetches data still rendered on this
   surface. Keep contributor/admin fetches only where they back visible ledger
   content.
   Proof requirement: add a focused loader/composable test proving the
   authenticated home path no longer calls `/api/v1/my-runs`,
   `/api/v1/favorites`, or `/api/v1/me/recent-tools`, then rerun
   `pdm run fe-test -- --run src/views/HomeView.spec.ts` plus the new focused
   loader spec and `pdm run fe-type-check`.

3. Severity: `low`
   File: `frontend/apps/skriptoteket/src/views/HomeView.spec.ts:234`, `frontend/apps/skriptoteket/src/views/HomeView.spec.ts:241`
   What is wrong: the new view spec still proves part of the change through
   removed CSS class names and a helper-call assertion
   (`.dashboard-card`, `.action-cards-grid`, `loadDashboard(...)`) instead of
   only through user-visible outcomes or an explicit API-boundary contract.
   Why it matters: the repo testing doctrine explicitly rejects
   implementation-detail tests like removed class-name checks, and these
   assertions will fail on harmless refactors without increasing confidence in
   the authenticated-home behavior.
   Concrete fix: delete the class-name and helper-call assertions from
   `HomeView.spec.ts`; keep the behavioral assertions around app order, truthful
   route targets, Document Converter non-linkability, and role-gated ledger
   content. If loader behavior matters, cover it in a dedicated composable/API
   boundary test instead.
   Proof requirement: rerun
   `pdm run fe-test -- --run src/views/HomeView.spec.ts` after trimming the
   implementation-detail assertions, plus any new focused loader/API test added
   for the data-loading contract.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run fe-test -- --run src/views/HomeView.spec.ts
```

Results:

- `pdm run fe-test -- --run src/views/HomeView.spec.ts`: passed with 5 tests.

Evidence inspected without rerunning the remaining gates:

- `pdm run fe-type-check`: reported passed in `.codex/handoff.md`.
- `pdm run fe-lint`: reported passed in `.codex/handoff.md`.
- `pdm run fe-build`: reported passed with existing warnings in
  `.codex/handoff.md`.
- `pdm run docs-validate`: reported passed in `.codex/handoff.md` and the PR
  doc verification notes.
- `pdm run handoff-validate`: reported passed in `.codex/handoff.md`.
- `git diff --check`: reported passed in `.codex/handoff.md` and the PR doc
  verification notes.
- Browser-proof blocker evidence:
  `.artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-after-huleedu-ui.json`,
  `.artifacts/skriptoteket-auth-bootstrap/local-dev-apply-result-pr-0364.json`,
  and
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T094857Z/`.

### Runtime Follow-Up Pass - 2026-06-19

Decision: `changes_requested`.

#### Scope Reviewed

- Follow-up runtime patch only:
  `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts`,
  `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.spec.ts`,
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`,
  plus the updated retained notes in
  `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md`
  and `.codex/handoff.md`.
- Governing proof gate and retained blocker evidence:
  `AGENTS.md`, the PR browser-proof section, and the live-proof blocker notes
  recorded in `.codex/handoff.md`.

#### Findings

1. Severity: `blocker`
   File: `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md:235`, `.codex/handoff.md:117`, `AGENTS.md:26`
   What is wrong: the required authenticated browser proof for the changed `/`
   route is still unresolved. The latest patch fixes the earlier loader/test
   review findings, but the governed Docker-backed HuleEdu browser-session
   proof remains blocked by local shared-auth identity drift.
   Why it matters: this repo’s UI/route-review policy requires live proof for
   the changed surface, and the user explicitly instructed that approval must
   not be granted by weakening that requirement. With the environment still
   failing `missing_identity_projection` / `identity_linking_required`, the
   runtime slice remains unapproved even though the remaining blocker does not
   appear to be caused by the frontend patch itself.
   Concrete fix: repair the local Skriptoteket projection/RBAC identity
   linkage for the current HuleEdu proof subjects, rerun the documented
   preflight/apply flow through the Docker-backed Gateway lane, then capture
   retained authenticated `/` proof at desktop and compact widths with exact
   commands, URLs, viewports, and artifact paths recorded in `.codex/handoff.md`.
   Proof requirement: a clean rerun of
   `pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364.json`
   followed by the governed retained browser proof for authenticated `/`
   through the HuleEdu ceremony and Docker `skriptoteket_web` lane.

Resolved in this follow-up patch, no longer active findings:

- The authenticated-home loader no longer keeps retired runs/favorites/recent
  endpoints on the default `/` load path:
  `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts:144`.
- The new boundary spec now proves that default authenticated-home loading does
  not call those retired endpoints and only fetches contributor/admin data when
  those ledgers are visible:
  `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.spec.ts:81`
  and `useHomeDashboard.spec.ts:95`.
- `HomeView.spec.ts` has been trimmed back to behavioral assertions rather than
  removed class names or helper-call expectations:
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts:199`.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts
pdm run docs-validate
```

Results:

- `pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts`: passed with 2 files / 7 tests.
- `pdm run docs-validate`: passed.

Evidence inspected without rerunning the remaining gates:

- Red-first proof recorded in the PR doc and handoff:
  `pdm run fe-test -- --run src/composables/home/useHomeDashboard.spec.ts`
  failed before the loader change because the default home path still called
  retired endpoints.
- `pdm run fe-type-check`: reported passed.
- `pdm run fe-lint`: reported passed.
- `pdm run handoff-validate`: reported passed.
- `git diff --check`: reported passed.
- Live-proof blocker evidence remains unchanged:
  `.artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-after-huleedu-ui.json`,
  `.artifacts/skriptoteket-auth-bootstrap/local-dev-apply-result-pr-0364.json`,
  and
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T094857Z/`.

### Final Runtime Proof Review Pass - 2026-06-19

Decision: `approved`.

#### Scope Reviewed

- Final proof-closeout evidence for the already-reviewed runtime slice:
  `docs/backlog/prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md`,
  `.codex/handoff.md`,
  `.artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-local-shared.json`,
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/manifest.redacted.json`,
  and the retained screenshots in that artifact directory.
- Prior runtime code/test findings were treated as closed unless the final
  proof evidence contradicted them.

#### Findings

No findings.

The previous blocker is now closed by retained evidence:

- The corrected preflight output is `status: ok` with every shared-auth check
  marked `ok`:
  `.artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-local-shared.json`.
- The retained browser-proof manifest is `status: ok`, targets `/` on
  `http://localhost:5173`, and records both required viewports:
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/manifest.redacted.json`.
- The expected retained screenshots exist for both proof widths:
  `authenticated-home-desktop.png` at `1512x900` and
  `authenticated-home-compact.png` at `390x844`.
- The PR doc and handoff now accurately explain why the earlier blocker was a
  false export mismatch and record the successful proof lane that matches the
  running HuleEdu Identity DB generation.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts
pdm run docs-validate
```

Results:

- `pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts`: passed with 2 files / 7 tests.
- `pdm run docs-validate`: passed.

Evidence inspected without rerunning:

- Correct preflight artifact:
  `.artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-local-shared.json`
  with `status: ok`.
- Retained browser-proof manifest:
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/manifest.redacted.json`
  with `status: ok`.
- Retained screenshots:
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/authenticated-home-desktop.png`
  and
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/authenticated-home-compact.png`.
- Reported green gates inspected in the PR doc and handoff:
  `pdm run fe-type-check`, `pdm run fe-lint`,
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`,
  `pdm run docs-validate`, `pdm run handoff-validate`, `pdm run lint`,
  `git diff --check`, and `pdm run fe-build` with existing warnings.

### Required Changes

None.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0364` | Retained the independent mockup review verdict as `approved` with scoped evidence, no findings, and validator results |
| 2 | `REV-PR-0364` | Added a separate runtime implementation review pass, recorded the live-proof blocker plus code/test findings, and changed the current overall verdict to `changes_requested` |
| 3 | `REV-PR-0364` | Added a follow-up runtime pass confirming the loader/test findings are fixed and that only the governed authenticated browser-proof blocker remains |
| 4 | `REV-PR-0364` | Added the final runtime proof-closeout pass, verified the corrected preflight plus retained browser-proof artifacts, and promoted the overall verdict to `approved` |
