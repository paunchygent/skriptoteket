---
type: review
id: REV-PR-0363
title: "Review: PR-0363 conversion lane mode deep-link contract"
status: approved
owners: "agents"
created: 2026-06-18
updated: 2026-06-19
reviewer: "codex-independent-reviewer"
prs:
  - PR-0363
links:
  - ST-37-03
  - EPIC-37
  - PR-0361
  - PR-0362
  - REV-PR-0362
  - REF-service-shell-ux-realignment-plan-v1
  - REF-current-product-lanes-and-sir-convert-boundary-v1
  - REF-app-presentation-decomposition-and-naming-plan-v1
---

## TL;DR

Approved on re-review. The scoped frontend code still satisfies the governed
`?mode=exam|transcript` contract without touching route/app-id/registry/public/
backend/Sir Convert/HuleEdu/QTI/DOCX surfaces, and the prior blocker is now
closed: the retained HuleEdu browser-session proof exists, uses the corrected
Docker/Gateway runtime lane, and visibly covers both
`/apps/documents.conversion_hub?mode=exam` and `?mode=transcript`.

## Problem Statement

This review checks whether `PR-0363` gives enough durable authority for code
implementation without leaking into later app-presentation or backend work:

1. direct authenticated shell entry to Exam Converter and Audio Transcription
   before app-id decomposition
2. truthful query-driven mode selection and tab synchronization on the current
   compatibility host
3. explicit fallback semantics for absent or invalid query state
4. hard scope boundaries that forbid route/app-id/registry/public/backend/Sir
   Convert/HuleEdu/QTI/DOCX drift
5. concrete fixture behavior, tests, and authenticated browser-proof gates

## Proposed Solution

Approve if the package keeps the change to the existing authenticated
`documents.conversion_hub` host, defines a closed `mode` contract with explicit
default and invalid-value behavior, preserves unrelated query keys during tab
switches, keeps fixture lanes truthful, and routes all broader app-presentation
changes into the already-planned follow-up sequence.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0363-st-37-03-conversion-lane-mode-deep-link-contract.md` | Governing scope, acceptance criteria, implementation steps, and proof gates | 20 min |
| `docs/backlog/prs/pr-0362-st-37-04-app-presentation-decomposition-and-naming-package.md` | Dependency state and claimed unblock status | 5 min |
| `docs/backlog/reviews/review-pr-0362-app-presentation-decomposition-and-naming-package.md` | Independent approval of the dependency package | 5 min |
| `docs/reference/ref-service-shell-ux-realignment-plan-v1.md` | Upstream shell-sequencing authority for `PR-0363` | 8 min |
| `docs/reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md` | Native-state versus heavy-conversion boundary | 8 min |
| `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md` | Naming/decomposition authority and follow-up split | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue` | Current local-mode reality and fixture boundary | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/ConversionHubModeTabs.vue` | Current mode type ownership and tab behavior | 5 min |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Existing authenticated/public route surfaces and fixture routes | 8 min |
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | Current host registry boundary that must stay unchanged | 5 min |

**Total estimated time:** ~84 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the contract on the existing authenticated `/apps/documents.conversion_hub` route via `?mode=exam|transcript` | This gives truthful direct shell entrypoints without pre-empting the later route/app-id decomposition decision | [x] |
| Default absent or invalid `mode` query state to exam without URL rewrite | This preserves legacy compatibility while failing closed against unsupported aliases, arrays, or empty values | [x] |
| Keep route records, registry metadata, public routes, backend/API, Sir Convert, HuleEdu, QTI, and DOCX out of scope | Those surfaces belong to later reviewed follow-up slices and are explicitly forbidden here | [x] |
| Require fixture truthfulness and HuleEdu-authenticated browser proof | The change is route-visible on a protected host, so truthful fixture handling and live proof are mandatory | [x] |

## Review Checklist

- [x] `PR-0363` defines the exact authenticated URL contract as
  `/apps/documents.conversion_hub?mode=exam|transcript`.
- [x] The package keeps query state synchronized from the mode tabs while
  preserving unrelated query keys.
- [x] Invalid, empty, repeated, array-valued, or absent `mode` state defaults
  to exam without URL canonicalization.
- [x] The package explicitly forbids route/app-id/registry/public/backend/Sir
  Convert/HuleEdu/QTI/DOCX changes in this slice.
- [x] Exam fixture behavior is called out explicitly and remains truthful to the
  existing lane-specific fixture routes.
- [x] Focused frontend tests, `fe-type-check`, docs validation, diff hygiene,
  and authenticated HuleEdu browser proof are all named as implementation gates.
- [x] `PR-0362` dependency state is satisfied by current docs state and
  independent review evidence.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-19`
**Verdict:** `approved`

### Current Re-Review Pass - 2026-06-19

Decision: `approved`.

#### Findings

No findings.

The prior blocker is resolved in the current reviewed state:

- The latest retained proof artifact
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/manifest.redacted.json`
  records `status: ok`, `base_url: http://127.0.0.1:5173`, viewport
  `1512x900`, and captures for both governed routes:
  `/apps/documents.conversion_hub?mode=exam` and
  `/apps/documents.conversion_hub?mode=transcript`.
- Spot-check of the retained `exam-mode.png` and `transcript-mode.png`
  screenshots confirms the visible tab state and workspace shell match the
  governed modes: Exam Converter shows the `Prov` tab with the exam rail and
  workspace; transcript mode shows the `Transkript` tab with the transcript
  rail and workspace.
- The new runtime breadcrumb is internally consistent across the retained
  evidence and docs surfaces: protected Gateway/browser-session proof uses the
  Docker `skriptoteket_web` service on `hule-network` with alias
  `skriptoteket-web`, not host Uvicorn.

#### Validation Commands And Outcomes

Reviewer-ran checks:

```bash
pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run test tests/unit/scripts/test_playwright_script_surface.py
pdm run docs-validate
pdm run handoff-validate
pdm run skills-validate
git diff --check
```

Results:

- `fe-test`: passed, `4` files / `44` tests.
- `fe-type-check`: passed.
- `fe-lint`: passed.
- `test_playwright_script_surface.py`: passed, `3` tests.
- `docs-validate`: passed.
- `handoff-validate`: passed.
- `skills-validate`: passed.
- `git diff --check`: passed.

Evidence inspected without rerunning the live proof command:

- Latest retained manifest:
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/manifest.redacted.json`.
- Latest retained screenshots:
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/exam-mode.png`
  and
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/transcript-mode.png`.
- Shared local-devops breadcrumb diff in the external skill repository:
  `skills/local-devops/references/skriptoteket.md`.

### Current Implementation Review Pass - 2026-06-18

Decision: `changes_requested`.

#### Scope Reviewed

- Governing docs: `PR-0363`, `REV-PR-0363`, `REF-service-shell-ux-realignment-plan-v1`,
  `REF-current-product-lanes-and-sir-convert-boundary-v1`,
  `REF-app-presentation-decomposition-and-naming-plan-v1`, `AGENTS.md`,
  `docs/index.md`, and the targeted review/testing/frontend-skill references.
- Scoped implementation files only:
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`,
  `frontend/apps/skriptoteket/src/views/apps/ConversionHubModeTabs.vue`,
  `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.ts`,
  `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.spec.ts`,
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`.

#### Findings

1. Severity: `blocker`
   File: `docs/backlog/prs/pr-0363-st-37-03-conversion-lane-mode-deep-link-contract.md:146`
   What is wrong: the required authenticated browser proof for the new
   route-visible `?mode=exam|transcript` contract has not been run or retained;
   worker evidence explicitly says browser proof is pending, and
   `.codex/handoff.md` has no PR-0363 proof entry.
   Why it matters: this slice changes a protected route's real navigation
   behavior. Repo policy in `AGENTS.md:26`-`AGENTS.md:30` and the PR's own test
   plan require live HuleEdu browser-session verification before approval, so
   jsdom tests alone are not enough to close the review honestly.
   Concrete fix: run the sanctioned authenticated browser proof against
   `/apps/documents.conversion_hub?mode=exam` and
   `/apps/documents.conversion_hub?mode=transcript`, verify the correct tab and
   workspace are active in both cases, then record the exact command, URLs,
   viewport, and artifact paths in `.codex/handoff.md`.
   Proof requirement: retain that proof in `.codex/handoff.md`, then run
   `pdm run handoff-validate` and `pdm run docs-validate`.

No scoped code or test-truthfulness findings were identified beyond the missing
browser-proof gate. The implementation itself stays inside the governed
boundary: the helper accepts only `exam|transcript`, defaults absent/invalid/
empty/repeated/array values to exam without canonicalization, preserves
unrelated query keys on tab clicks, keeps exam UI-inspection fixtures exam-only
and skip-write, and introduces no route/app-id/registry/public/backend/Sir
Convert/HuleEdu/QTI/DOCX drift in the reviewed diff.

#### Validation Commands And Outcomes

Reviewer-ran focused checks:

```bash
pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts
pdm run fe-type-check
```

Results:

- `fe-test`: passed, `4` files / `44` tests.
- `fe-type-check`: passed.

Worker evidence accepted but not rerun by this reviewer:

- `pdm run fe-lint`: passed.
- `git diff --check`: passed before review-doc edits.

Missing required evidence:

- Authenticated browser proof through the HuleEdu browser-session ceremony:
  not run in the implementation evidence provided to this review.

### Historical Planning Review Pass - 2026-06-18

Decision: `approved`.

### Required Changes

None.

### Implementation Proof Addendum - 2026-06-19

The missing proof from the implementation review pass has now been supplied.
This addendum is an implementer update and does not self-approve the review.

- Corrected proof lane: HuleEdu Gateway plus Skriptoteket Docker
  `skriptoteket_web` service on `hule-network` with alias
  `skriptoteket-web`; host Uvicorn is not valid for this protected Gateway
  proof.
- Root cause of the failed earlier proof attempt: Gateway app continuation
  resolves `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL` as
  `http://skriptoteket-web:8000`, so it cannot reach a host-only Uvicorn
  process as that Docker DNS name.
- Gateway-to-Skriptoteket health check passed:
  `docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz`.
- Authenticated browser proof passed:
  `pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink`.
- Retained artifact:
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/manifest.redacted.json`.
- Captured routes:
  `/apps/documents.conversion_hub?mode=exam` and
  `/apps/documents.conversion_hub?mode=transcript` at viewport `1512x900`.
- Runtime breadcrumb added to:
  `.codex/skills/skriptoteket-testing/references/browser-automation.md`,
  `.codex/skills/skriptoteket-testing/references/backend-pytest.md`,
  `docs/runbooks/runbook-testing.md`, and the shared
  `local-devops/references/skriptoteket.md`.
- Implementer validation after the proof addendum:
  - `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
    passed with 4 files / 44 tests.
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run fe-build` passed with existing dynamic/static import and
    large-chunk warnings.
  - `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
    passed with 3 tests.
  - `pdm run docs-validate`, `pdm run handoff-validate`, and
    `pdm run skills-validate` passed in this repo.
  - `git diff --check` passed in this repo.
  - Shared skill repository `pdm run skills-validate` and
    `pdm run docs-validate` passed for the `local-devops` breadcrumb update.
  - Shared skill repository `git diff --check` passed.

### Suggestions (Optional)

- When implementation starts, keep the review scope honest if unrelated route,
  registry, or backend drift appears during testing; stop and re-plan instead
  of expanding `PR-0363` in place.

### Decision Approvals

- [x] Accept the authenticated query-mode bridge on the existing host
- [x] Accept exam-by-default invalid/absent query semantics
- [x] Accept the no-route/app-id/registry/public/backend contract boundary
- [x] Accept the required fixture and HuleEdu browser-proof gates

### Findings

Current re-review: no findings.
Planning review: no findings.

### Evidence And Validation

- `PR-0363` acceptance criteria and assumptions explicitly cover the protected
  `?mode=exam|transcript` contract, tab/query synchronization, exam default
  behavior, unrelated-query preservation, and exam-fixture truthfulness.
- `PR-0363` non-goals, remaining gates, and implementation steps keep route
  records, app ids, registry semantics, public routes, backend/API, Sir
  Convert, HuleEdu Gateway, QTI, and DOCX out of scope for this slice.
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
  currently owns `activeHubMode` as a local ref and renders the transcript host
  behind the same authenticated shell, so the planning package correctly
  targets the current implementation seam without inventing a new route.
- `frontend/apps/skriptoteket/src/router/routes.ts` already exposes the
  authenticated host through `/apps/:appId` and already has separate dev/test
  fixture routes for exam and transcript, which matches the package's no-route-
  change and fixture-truth assumptions.
- `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` still maps
  `documents.conversion_hub` to the authenticated Exam Converter host and the
  public Exam Converter host, so the package correctly treats registry and
  public-surface changes as out of scope.
- `PR-0362` dependency is satisfied:
  - `docs/backlog/prs/pr-0362-st-37-04-app-presentation-decomposition-and-naming-package.md`
    is `status: done` and says `PR-0363` through `PR-0365` are unblocked by
    planning and now gated only by their own review docs.
  - `docs/backlog/reviews/review-pr-0362-app-presentation-decomposition-and-naming-package.md`
    is `status: approved`, confirming the dependency package already passed its
    independent review gate.
- Historical planning validation:
  - `pdm run docs-validate`: passed.
  - `git diff --check`: passed.
  Current re-review validation is listed in the 2026-06-19 re-review section
  above.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0363` | Added the retained pre-implementation review, recorded dependency satisfaction for `PR-0362`, and approved the bounded `mode` deep-link contract |
| 2 | `REV-PR-0363` | Added the implementation review pass, reran focused frontend checks, and moved the current decision to `changes_requested` because the required authenticated browser proof is still missing |
| 3 | `REV-PR-0363` | Added the implementer proof addendum with Docker-service runtime evidence and requested independent re-review without self-approval |
| 4 | `REV-PR-0363` | Completed the independent re-review, verified the retained authenticated browser proof and runtime breadcrumbs, reran the focused validation gates, and approved the implementation |
