---
type: review
id: REV-PR-0349
title: "Review: PR-0349 Transcript Parity Live Proof And Closeout"
status: approved
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
reviewer: "ruthless-code-reviewer"
prs:
  - PR-0349
links:
  - ST-21-08
  - EPIC-21
  - PR-0347
  - PR-0348
---

## TL;DR

The truthfulness remediation is now reviewable and correct. `PR-0349` and
`ST-21-08` still remain blocked on the live HuleEdu/Sir Convert trust lane,
but the retained `20260613T153843Z` artifact now reports the typed
`sir_convert_internal_identity_rejected` failure as the primary blocker and the
manifest lists only the evidence files that were actually captured.

## Problem Statement

PR-0349 is the live parity proof and closeout gate for ST-21-08. Because the
lane is blocked outside Skriptoteket production behavior, this review is not
about shipping the full transcript parity flow. It is about whether the proof
harness, retained artifacts, and closeout docs are truthful enough to approve
the blocked state without accidentally implying that progress, cancel, save,
overlay, replay, download, or Mina filer parity were proven.

## Proposed Solution

The reviewed change set adds:

- a targeted Playwright proof entrypoint for the authenticated transcript parity
  lane;
- shared sanitized evidence helpers for bounded network/console/summary output;
- auth-helper hardening so the proof follows the HuleEdu browser-session
  ceremony and handoff link instead of product-local shortcuts;
- docs/handoff/epic/story updates that keep PR-0349 and ST-21-08 blocked and
  explicitly separate implemented slices from unproven live closeout.

That overall shape is correct. The earlier retained-evidence truthfulness
blockers have now been fixed, and the blocked-state wording remains honest.

## Scope

Primary review target:

- `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md`

Authority and adjacent governed items reviewed:

- `docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md`
- `docs/backlog/prs/pr-0348-st-21-08-overlay-aware-download-and-mina-filer-save.md`
- `docs/backlog/reviews/review-pr-0347-overlay-aware-formatter-replay-client.md`
- `docs/backlog/reviews/review-pr-0348-overlay-aware-download-and-mina-filer-save.md`
- `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md`
- `docs/backlog/epics/epic-21-curated-app-conversion-hub.md`
- `.codex/handoff.md`
- `.codex/rules/075-browser-automation.md`
- `docs/index.md`
- `docs/reference/ref-review-workflow.md`

Implementation and proof files reviewed:

- `scripts/playwright_pr_0349_transcript_parity_live.py`
- `scripts/_transcript_parity_evidence.py`
- `scripts/_playwright_auth.py`
- `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
- `tests/unit/scripts/test_playwright_script_surface.py`
- `tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
- `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/proof-summary.json`
- `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/network.bounded.json`
- `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/browser-console.bounded.json`
- `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/failure.png`

Out of scope for approval here:

- approving full ST-21-08 parity acceptance;
- fixing the HuleEdu/Sir Convert signer trust mismatch itself;
- re-reviewing the already-approved PR-0347 or PR-0348 production logic beyond
  their use as parity prerequisites.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md` | Blocked closeout claims and acceptance-state honesty | 15 min |
| `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md` | Story status and parity gate wording | 10 min |
| `scripts/playwright_pr_0349_transcript_parity_live.py` | Auth path, proof sequencing, retained summary truth | 30 min |
| `scripts/_transcript_parity_evidence.py` | Sanitization, blocker extraction, captured-artifact manifest | 15 min |
| `scripts/_playwright_auth.py` | HuleEdu browser-session ceremony compliance | 15 min |
| `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py` | Blocked-run summary truthfulness coverage | 10 min |
| `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/*` | Retained evidence strength and honesty | 20 min |
| `tests/unit/scripts/test_playwright_script_surface.py` | Script-surface allowlist enforcement | 5 min |
| `tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py` | Transcript docs guard coverage | 5 min |

**Total estimated time:** ~2 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep approval scoped to the blocked proof-harness/docs state only | The full parity acceptance criteria remain unproven by design. | [x] |
| Require HuleEdu browser-session ceremony and repo helpers for proof | Matches AGENTS.md, browser-automation rules, and the PR non-goals. | [x] |
| Treat misleading retained evidence metadata as an approval blocker until fixed | This PR is a proof/closeout slice, so artifact truthfulness is the product. The earlier blockers are now resolved. | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0349 proof harness and blocked closeout truthfulness.
- [x] Docs-as-code authority exists for ST-21-08 and PR-0349.
- [x] The reviewed script uses the HuleEdu browser-session ceremony and repo helpers.
- [x] No direct product-backend credential shortcut or direct Sir Convert browser proof was found.
- [x] No new `Any`, `cast(...)`, or `# type: ignore` was introduced in the PR-0349 harness files reviewed here.
- [x] The blocked-run truthfulness tests cover typed blocker promotion and captured-artifact manifests without `Any`, `cast(...)`, or `# type: ignore`.
- [x] The new Playwright entrypoint is added to the script-surface allowlist.
- [x] Story/epic/handoff docs keep PR-0349 and ST-21-08 blocked rather than falsely accepted.
- [x] The retained proof summary is fully truthful about the blocker and the evidence actually captured.

## Verification

Commands run:

```bash
git status --short
git diff --stat
git diff --name-only
git diff --check
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py scripts/_transcript_parity_evidence.py scripts/_playwright_auth.py
pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run test tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py
pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py
```

Results:

- The working tree includes broader ST-21-08 implementation and docs changes,
  so this review stayed intentionally bounded to the PR-0349 proof/closeout
  slice and its governed dependencies.
- `git diff --check` passed before this review artifact was added.
- `pdm run python -m py_compile ...` passed for the PR-0349 harness and helper
  modules.
- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed: 2 tests.
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  passed: 6 tests.
- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  passed: 8 tests.
- The retained artifact directory exists and contains
  `proof-summary.json`, `network.bounded.json`,
  `browser-console.bounded.json`, and `failure.png`.
- `failure.png` shows the authenticated transcript lane UI with the blocked
  transcript-create failure surface visible.
- `network.bounded.json` proves the sanctioned local app path reached
  `POST /sir-convert/v2/convert/jobs?wait_seconds=0` and received HTTP `401`
  with scrubbed `error_code=auth_invalid_internal_identity` and
  `reason=invalid_internal_identity_signature`.
- `proof-summary.json` now reports the typed
  `sir_convert_internal_identity_rejected` object as the top-level `failure`
  and keeps the generic Playwright timeout only as `raw_failure`.
- The retained artifact manifest now lists only captured evidence:
  `network.bounded.json`, `browser-console.bounded.json`, and `failure.png`.
- I did not rerun the live PR-0349 browser script because the user asked for a
  review of the current worktree changes and retained evidence, not a fresh
  implementation/proof attempt.

## Review Feedback

**Reviewer:** ruthless-code-reviewer
**Date:** 2026-06-13
**Verdict:** approved

### Findings

No findings. The two earlier truthfulness blockers were resolved in
`scripts/_transcript_parity_evidence.py`, covered by
`tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`, and
confirmed in the retained
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/`
artifact set.

### Positive Checks

- The docs/handoff state does not falsely claim parity acceptance. `PR-0349`
  and `ST-21-08` remain blocked in the PR doc, story doc, epic summary, and
  `.codex/handoff.md`.
- The proof harness uses `login_via_auth_entry(...)` and stays on the
  sanctioned browser-session/Gateway path; I found no direct product-backend
  credential shortcut, no local session-cookie shortcut, and no direct Sir
  Convert browser lane.
- The retained network artifact is sanitized and strong enough to prove the
  immediate blocker: submit reaches the Gateway edge and is rejected before a
  transcript job exists.
- The retained `proof-summary.json` now leads with the typed
  `sir_convert_internal_identity_rejected` failure and relegates the generic
  timeout to `raw_failure`, which is the truthful blocked-run shape this slice
  requires.
- The retained artifact manifest matches the files that actually exist on disk
  and no longer claims happy-path screenshots that were never captured.
- The PR-0349 harness files reviewed here introduce no `Any`, `cast(...)`, or
  `# type: ignore`.
- The blocked-run truthfulness tests also introduce no `Any`, `cast(...)`, or
  `# type: ignore`.
- `tests/unit/scripts/test_playwright_script_surface.py` correctly adds the new
  PR-0349 entrypoint to the allowlist, and the transcript docs guard stays
  green.

### Suggestions (Optional)

- None.

### Decision Approvals

- [x] Approval scope stays limited to blocked proof-harness/docs state
- [x] Authenticated proof uses the HuleEdu browser-session ceremony
- [x] Retained evidence truth is strong enough for blocked closeout approval

## Implementation Response

**Date:** 2026-06-13
**Responder:** Skriptoteket implementation specialist
**Decision authority:** reviewer-owned; this response does not approve
`REV-PR-0349`.

The two requested evidence-truthfulness changes were implemented:

- `scripts/_transcript_parity_evidence.py` now finalizes retained summaries
  after bounded network/console files are written, computes the artifact
  manifest from files that exist on disk, and promotes a detected Sir Convert
  `auth_invalid_internal_identity` /
  `invalid_internal_identity_signature` submit response to the primary
  `failure` object. The PR-0349 Playwright entrypoint imports that helper.
- `tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py` covers
  the blocked-run summary shape and proves that phantom happy-path screenshots
  are not listed.

Red-first evidence:

- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  failed before implementation with an import error for the missing summary
  finalizer functions.

Green evidence:

- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed with `2 passed`.
- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  passed with `8 passed`.
- `pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py scripts/_transcript_parity_evidence.py scripts/_playwright_auth.py`
  passed.

Cross-repo smoke after approved upstream slices:

- HuleEdu `TASK-0676` profile publisher passed for `local-auth-integration` and
  `hemma-production`, both emitting canonical DER SPKI fingerprint
  `46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992`.
- Sir Convert `task-361` approved focused suite passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
  with `39 passed`.

Fresh PR-0349 live proof rerun:

- `pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --timeout-seconds 1200`
  still failed before a cancellable transcript job was created.
- Retained artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/proof-summary.json`.
- The top-level `failure` is now
  `type=kind=sir_convert_internal_identity_rejected` with HTTP `401`,
  `error_code=auth_invalid_internal_identity`,
  `reason=invalid_internal_identity_signature`, and path
  `/sir-convert/v2/convert/jobs?wait_seconds=0`.
- The artifact manifest lists only captured evidence:
  `network.bounded.json`, `browser-console.bounded.json`, and `failure.png`.

Remaining blocker:

- The code-level HuleEdu/Sir Convert trust-profile contract now smokes green,
  but the live Sir Convert runtime reached by the sanctioned local browser
  proof still rejects the Gateway-signed identity context. Full PR-0349 parity
  remains blocked until that deployed/runtime trust lane is reconciled.

## Residual Risks

- `PR-0349` remains product-blocked until the HuleEdu/Sir Convert signer trust
  lane is reconciled or a sanctioned Hemma/prod browser proof lane is provided.
- This approval is only for the truthfulness remediation and retained review
  closeout quality, not for full ST-21-08 parity acceptance.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0349` | Re-reviewed the truthfulness remediation, updated the retained review record, and marked it `approved`. |
| 2 | Implementation | No production code changes were made by this reviewer. |
