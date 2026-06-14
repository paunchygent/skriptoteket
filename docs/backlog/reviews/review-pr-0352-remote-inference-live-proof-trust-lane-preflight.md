---
type: review
id: REV-PR-0352
title: "Review: PR-0352 remote inference live-proof trust-lane preflight"
status: changes_requested
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
reviewer: "ruthless-review-subagent"
prs:
  - PR-0352
links:
  - ST-21-09
  - EPIC-21
  - docs/backlog/reviews/review-pr-0351-transcript-completion-progress-and-export-ux.md
---

## TL;DR

Changes requested after independent re-review. The prior local-host bypass,
mixed-tunnel opt-in, and retained URL redaction findings are remediated, but the
remote proof gateway lane can still pass without proving the gateway target or
runtime lane is resolved.

## Problem Statement

The review must verify that the recurring local HuleEdu Gateway to Sir Convert
internal identity mismatch is now blocked by tooling, not remembered as
session guidance. The task must keep Sir Convert's hosted model/runtime estate
remote by default while preventing incoherent local-signer to Hemma-verifier
lanes from running silently.

## Proposed Solution

Add a browser-free preflight helper used by the PR-0349/PR-0351 transcript live
proof. The helper validates public lane metadata before source media is copied
or Playwright is launched. Production/Hemma remote proof is allowed; mixed
local-Gateway to Hemma-Sir-Convert tunnel use requires explicit opt-in and
matching public signer/verifier fingerprints.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0352-st-21-09-remote-inference-live-proof-trust-lane-preflight.md` | Scope, acceptance, evidence | 10 min |
| `docs/backlog/stories/story-21-09-conversion-hub-remote-inference-proof-trust-lane.md` | Parent story and hosted runtime boundary | 5 min |
| `scripts/_sir_convert_trust_lane_preflight.py` | Preflight semantics, redaction, typing, maintainability | 25 min |
| `scripts/playwright_pr_0349_transcript_parity_live.py` | Hook placement before media copy/job submit | 15 min |
| `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py` | Behavioral proof and redaction coverage | 15 min |
| Adjacent script tests and validators | Regression proof | 10 min |

**Total estimated time:** ~80 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Preflight before media copy | Proves the blocker happens before upload/job creation. | [ ] |
| Remote hosted runtime remains default | Avoids making local model/runtime hosting a prerequisite. | [ ] |
| Mixed tunnel requires opt-in plus fingerprint agreement | Keeps debugging possible without silent incoherent defaults. | [ ] |
| Failure summaries are redacted public metadata only | Retained artifacts must not leak secrets, transcript text, or media content. | [ ] |

## Review Checklist

- [ ] Governing docs-as-code authority is valid and current.
- [ ] Preflight blocks local-signer to Hemma-verifier mismatch before upload.
- [ ] Production/Hemma remote proof remains usable.
- [ ] Mixed tunnel debug mode cannot run without explicit opt-in.
- [ ] Public fingerprint checks are strict and fail closed.
- [ ] No local model/runtime hosting or remote signing-secret copy path was added.
- [ ] Proof summaries do not expose private keys, tokens, cookies, passwords,
  transcript text, or media content.
- [ ] Tests prove behavior at the script/helper boundary without brittle
  implementation-only assertions.
- [ ] Python files remain within repo line budgets and pass lint/typecheck.

## Review Feedback

**Reviewer:** @ruthless-review-subagent
**Date:** 2026-06-14
**Verdict:** changes_requested

### Findings

1. **blocker - unresolved remote proof gateway lane can pass on fingerprints alone**

   `scripts/_sir_convert_trust_lane_preflight.py:184` routes every
   `remote-proof-gateway` local proof to `_check_matching_fingerprints`, and
   `_uses_remote_compute` treats `proof_lane == "remote-proof-gateway"` as
   remote compute at `scripts/_sir_convert_trust_lane_preflight.py:340` before
   checking any gateway/backend target. `_check_matching_fingerprints` then
   only requires signer and verifier fingerprints at
   `scripts/_sir_convert_trust_lane_preflight.py:365`.

   This means a local UI/backend proof can pass preflight with
   `--sir-convert-proof-lane remote-proof-gateway` plus matching fingerprint
   metadata even when `gateway_backend_url` and ready/profile metadata are
   absent or still point at a local/non-sanctioned backend. That violates
   `PR-0352` acceptance that unresolved lanes block before media copy/job
   submit and that the active lane is resolved from the HuleEdu Gateway target,
   Sir Convert readiness/profile metadata, and public fingerprints.

   Corrective shape: require a resolved sanctioned remote proof gateway target
   for `remote-proof-gateway` before allowing `_check_matching_fingerprints`.
   At minimum, missing `gateway_backend_url` should block with
   `sir_convert_trust_lane_unresolved`, and local/private/default backend
   targets should not be accepted as `remote-proof-gateway`. Keep the
   production/Hemma public product-host allowance separate from local proof
   gateway validation.

   Proof required:

   ```bash
   pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
   pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py
   pdm run python -m py_compile scripts/_sir_convert_trust_lane_preflight.py scripts/playwright_pr_0349_transcript_parity_live.py
   pdm run typecheck
   pdm run lint
   pdm run docs-validate
   pdm run handoff-validate
   git diff --check
   ```

### Required Changes

- Add a negative test proving `proof_lane="remote-proof-gateway"` with matching
  fingerprints but no gateway target blocks before media copy/job submit.
- Add a negative test proving `remote-proof-gateway` rejects local/private
  gateway targets such as `http://127.0.0.1:8085` or
  `http://host.docker.internal:8085`.
- Update the preflight logic so `remote-proof-gateway` is remote only after a
  sanctioned gateway target/profile is resolved, then rerun the proof commands
  listed above.

### Suggestions (Optional)

Pending.

### Decision Approvals

- [x] Preflight before media copy
- [ ] Remote hosted runtime remains default
- [x] Mixed tunnel opt-in and fingerprint agreement
- [x] Redacted retained failure summaries

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0352` | Added implementation summary, red-first evidence, and validation evidence. |
| 2 | `scripts/_sir_convert_trust_lane_preflight.py` | Added browser-free proof-lane preflight helper. |
| 3 | `scripts/playwright_pr_0349_transcript_parity_live.py` | Runs preflight before media copy and browser launch. |
| 4 | `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py` | Adds focused trust-lane preflight tests. |
