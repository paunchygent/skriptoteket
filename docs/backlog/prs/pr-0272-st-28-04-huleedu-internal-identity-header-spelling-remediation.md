---
type: pr
id: PR-0272
title: "ST-28-04 HuleEdu internal identity header spelling remediation"
status: ready
owners: "agents"
created: 2026-04-25
updated: 2026-04-25
stories:
  - "ST-28-04"
dependencies:
  - "PR-0254"
  - "PR-0263"
  - "PR-0264"
  - "HuleEdu TASK-0325"
tags: ["auth", "huleedu", "gateway", "production-regression", "verification"]
acceptance_criteria:
  - "Given HuleEdu Gateway now emits corrected `X-HuleEdu-Identity-*` transport headers, when Skriptoteket verifies protected app API requests, then the verifier consumes the corrected spelling and no longer rejects Gateway-proxied requests as `missing_internal_identity_headers` because it expects `X-Huledu-Identity-*`."
  - "Given older `Huledu` spellings may remain in tests, proof helpers, docs, or historical path defaults, when this remediation is implemented, then every remaining `Huledu` or `huledu` occurrence is either removed, updated, or explicitly classified as unrelated historical checkout/path text with no runtime header effect."
  - "Given protected browser `/api` traffic must enter through `https://api.hule.education/api/...`, when the live proof runs for an existing Skriptoteket projection, then `GET /api/v1/profile/app-continuation` returns `200` through the HuleEdu Gateway edge and no direct app-host protected API shortcut is introduced."
  - "Given the auth cutover owns local projection and RBAC inside Skriptoteket, when the spelling fix ships, then it does not change projection keys, local `User.role` authorization, first-login provisioning policy, CSRF handling, logout semantics, or product identity realm validation."
  - "Given auth outcome observability is already in place, when the proof exercises the failing path with a known correlation id, then the retained evidence distinguishes corrected signed-context acceptance from unrelated missing-projection, unsupported-realm, or local RBAC failures without logging signed headers, raw subjects, emails, cookies, CSRF tokens, or request bodies."
---

## Problem

After the HuleEdu redeploy on 2026-04-25, cross-app auth regressed for a user who first logged in
through HuleEdu and then opened Skriptoteket using the same browser session.

Bounded production log inspection showed:

- HuleEdu Identity successfully created a browser session for the user.
- HuleEdu Gateway resolved that browser session and proxied
  `GET /api/v1/profile/app-continuation` to `skriptoteket-web`.
- Skriptoteket rejected the request with
  `auth.internal_identity.rejected reason=missing_internal_identity_headers`.

The apparent root cause is a transport-header spelling drift:

- HuleEdu now emits corrected `X-HuleEdu-Identity-*` header names.
- Skriptoteket still expects the older misspelled `X-Huledu-Identity-*` names in its internal
  identity verifier and proof helpers.

This prevents the app-continuation route from reaching realm-aware projection resolution at all.
The failure is therefore a signed-context transport mismatch, not first evidence of a broken local
projection.

## Goal

Align Skriptoteket with the corrected HuleEdu internal identity header spelling, prove the
Gateway-proxied production route accepts the signed context, and leave a small inventory of any
remaining old spellings so this typo does not survive in a hidden proof helper or docs claim.

## Non-goals

- Changing HuleEdu Gateway, Identity, session, CSRF, logout, or product-realm behavior.
- Adding a compatibility fallback that accepts both spellings indefinitely unless a reviewed
  rollback decision explicitly requires a short-lived bridge.
- Changing local identity projection schema, local role assignment, local RBAC, provisioning
  policy, or user linking semantics.
- Treating historical checkout/path names such as `huledu-reboot` or `/home/.../huledu/...` as
  header-spelling bugs unless they are proven to affect current runtime key mounts or proof lanes.
- Printing raw signed identity headers, signatures, cookies, CSRF tokens, raw subject ids, or
  emails in logs, docs, or retained proof artifacts.

## Implementation Plan

1. Inventory old and corrected spellings before editing:
   - `rg -n "Huledu|huledu|X-Huledu|X-HuleEdu" src tests scripts docs frontend compose.yaml compose.prod.yaml .env.example`
   - Classify each hit as runtime header contract, proof/test fixture, docs wording, historical
     path default, or unrelated product naming.
2. Update the canonical Skriptoteket internal identity transport constants to match HuleEdu:
   - `src/skriptoteket/domain/identity/internal_identity_context.py`
   - The expected runtime header names must become `X-HuleEdu-Identity-Context-Version`,
     `X-HuleEdu-Identity-Context`, `X-HuleEdu-Identity-Key-Id`, and
     `X-HuleEdu-Identity-Signature`.
3. Update all active proof helpers and fixtures that mint signed HuleEdu headers:
   - `scripts/_playwright_huleedu_auth.py`
   - Any route/projection fixtures under `tests/fixtures/`
   - Unit tests that assert explicit header names or missing-header behavior.
4. Add a focused regression that fails with the old spelling and passes with the corrected
   spelling:
   - corrected `X-HuleEdu-*` headers accepted;
   - old `X-Huledu-*` only headers rejected, unless a reviewed short-lived compatibility bridge is
     intentionally added;
   - mixed or spoofed browser-supplied headers still fail closed or are stripped at the expected
     boundary.
5. Re-run the spelling inventory after edits and document any remaining `Huledu` / `huledu`
   occurrences in this PR's implementation summary or a small reference note before closeout.
6. Run the public/Gateway proof with a known correlation id against the protected API edge:
   - HuleEdu login/session first;
   - Skriptoteket app-continuation through `https://api.hule.education/api/v1/profile/app-continuation`;
   - expected `200` for a known existing projection;
   - direct `https://skriptoteket.hule.education/api/v1/profile/app-continuation` remains non-200
     or otherwise non-authoritative for protected app API access.

## Test Plan

- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py`
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_context_api.py`
- `pdm run pytest -q tests/unit/web/test_huleedu_identity_context_probe_api.py`
- `pdm run pytest -q tests/unit/application/auth/test_pr_0254_auth_cutover_manifest.py`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`

If proof helpers or frontend protected API routing change, also run:

- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane`
- `pdm run fe-test -- --run src/stores/auth.spec.ts src/api/client.spec.ts`
- `pdm run fe-type-check`

## Rollback Plan

If the corrected spelling cannot be deployed safely, revert only this spelling-remediation slice
and retain the incident evidence. Do not change projection data or local user records as rollback.

If production compatibility with an older HuleEdu Gateway is temporarily required, add a new
reviewed task for a time-boxed dual-spelling compatibility bridge with explicit removal criteria
and tests proving the bridge does not accept unsigned or browser-forged identity material.

## Review Notes

Review should focus on hidden old-spelling remnants and unintended broadening of the auth trust
boundary. The dangerous failure modes are:

- tests still mint only `X-Huledu-*`, so local proof passes while production Gateway traffic fails;
- docs continue to instruct operators to look for the old header names;
- a broad compatibility fix accepts arbitrary browser-supplied identity headers;
- a same-origin direct protected API route is accidentally certified as production policy.
