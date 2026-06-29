---
type: review
id: REV-PR-0408
title: "Review: PR-0408 Exam Converter design proof helper remediation"
status: approved
owners: "agents"
created: 2026-06-29
updated: 2026-06-29
reviewer: "ruthless-code-review"
prs:
  - PR-0408
links:
  - ST-21-04
  - PR-0406
  - REV-PR-0406
  - docs/runbooks/runbook-agent-browser-automation.md
---

## TL;DR

Approved. The reviewed proof-helper remediation keeps the retained PR-0408
artifact command as a thin adapter, moves reusable browser assertions into a
domain helper, and adds opt-in bounded HuleEdu RATE_LIMIT backoff to the shared
auth helper without changing strict default callers or exposing credentials.

## Problem Statement

This review checks only the PR-0408 proof-helper remediation requested by the
user: shared-auth helper use, bounded rate-limit backoff, proof-script surface
consolidation, behavior-meaningful assertions, small module shape, and tests
for the shared auth helper. It does not review unrelated dirty PR-0408 frontend
component changes.

## Proposed Solution

The implementation adds `scripts._playwright_auth_rate_limit` for sanitized
RATE_LIMIT parsing, extends `scripts._playwright_auth.login_via_auth_entry()`
with opt-in backoff parameters, extracts Exam Converter design proof behavior
to `scripts._exam_converter_design_proof`, and keeps
`.artifacts/pr-0408-exam-converter-design-proof/proof_pr0408_exam_converter_design.py`
as a retained artifact adapter.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0408-st-21-04-exam-converter-frontend-design-implementation-alignment.md` | Authority, non-goals, proof expectations | 10 min |
| `AGENTS.md`, `.codex/rules/050-python-standards.md`, `.codex/rules/075-browser-automation.md`, `docs/runbooks/runbook-agent-browser-automation.md` | Repo constraints for Python, auth, Playwright, proof lanes | 15 min |
| `scripts/_playwright_auth.py` | Shared auth default strictness and opt-in backoff integration | 25 min |
| `scripts/_playwright_auth_rate_limit.py` | RATE_LIMIT parsing, bounded waits, credential redaction | 20 min |
| `scripts/_exam_converter_design_proof.py` | Reusable domain proof helper and behavior assertions | 20 min |
| `.artifacts/pr-0408-exam-converter-design-proof/proof_pr0408_exam_converter_design.py` | Thin retained adapter only | 5 min |
| `tests/unit/scripts/test_playwright_auth_recovery.py` | Auth recovery/backoff/redaction proof | 15 min |
| `tests/unit/scripts/test_playwright_script_surface.py` | Script-surface hygiene and adapter delegation | 10 min |

**Total estimated time:** ~120 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep backoff opt-in on `login_via_auth_entry()` with strict default behavior. | Existing shared-auth callers should not silently retry HuleEdu login unless a proof explicitly opts in. | Yes |
| Sanitize login failure bodies before surfacing RATE_LIMIT diagnostics. | Login failures can contain submitted credentials in server details or exception text. | Yes |
| Put reusable Exam Converter proof behavior in an underscored domain helper. | Matches the repo browser-automation rule: entrypoints are proofs, helpers own shared flows. | Yes |
| Keep the PR-numbered artifact command as a thin adapter. | Retained artifact reproducibility is preserved without creating a new permanent `scripts/playwright_pr_0408*` surface. | Yes |
| Assert route-owned UI states and overflow instead of only checking that a helper was invoked. | The live proof remains useful for the PR-0408 desktop/phone design surfaces. | Yes |

## Review Checklist

- [x] Scope is bounded to the six requested files and PR-0408 proof-helper objective.
- [x] PR-0408 authority, browser automation runbook, and Python/browser rules were read.
- [x] Default auth behavior remains strict unless `rate_limit_backoff=True`.
- [x] RATE_LIMIT diagnostics redact submitted email and password.
- [x] No direct credential POST shortcut, local cookie shortcut, or retired local auth surface was introduced.
- [x] No new permanent PR-numbered script under `scripts/` was introduced.
- [x] Proof assertions cover route-owned desktop/phone surfaces, file/report exclusivity, symbolic navigation, no bot icon, and horizontal-overflow evidence.
- [x] File sizes remain under the repo's rough 400-500 LoC ceiling.

## Review Feedback

**Reviewer:** ruthless-code-review
**Date:** 2026-06-29
**Verdict:** approved

### Required Changes

None.

### Findings

No blocking correctness, security, compatibility, or proof-truth findings in
the reviewed scope.

### Verification

| Command or evidence | Result |
|---------------------|--------|
| `pdm run test tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_playwright_script_surface.py` | Passed locally, 13 tests. |
| `pdm run python -m py_compile scripts/_playwright_auth.py scripts/_playwright_auth_rate_limit.py scripts/_exam_converter_design_proof.py .artifacts/pr-0408-exam-converter-design-proof/proof_pr0408_exam_converter_design.py` | Passed locally. |
| `git diff --check -- scripts/_playwright_auth.py tests/unit/scripts/test_playwright_auth_recovery.py tests/unit/scripts/test_playwright_script_surface.py` | Passed locally for tracked reviewed diffs. |
| `.artifacts/pr-0408-exam-converter-design-proof/20260629T165724Z/manifest.redacted.json` | Status `ok`; desktop and phone captures present; overflow checks all `ok`; no credential/email hits found in the reviewed artifact manifests. |
| Overseer-provided live command `pdm run python .artifacts/pr-0408-exam-converter-design-proof/proof_pr0408_exam_converter_design.py` | Reported passed with artifact `.artifacts/pr-0408-exam-converter-design-proof/20260629T165724Z`. Not rerun in review to avoid consuming extra HuleEdu login attempts. |

### Residual Risk / Test Gaps

- The unit tests cover structured RATE_LIMIT JSON, bounded window backoff, and
  credential redaction. They do not separately exercise `Retry-After` header
  precedence or malformed 429 bodies; the parser implementation handles those
  paths by inspection, but they are residual low-risk coverage gaps.
- The script-surface test for the artifact adapter is partly a source-shape
  hygiene test. That is acceptable here because the governed contract is
  specifically to keep retained artifact adapters thin, but code review remains
  the stronger proof that browser logic moved to the domain helper.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Auth backoff preserves strict defaults.
- [x] Credential leakage is avoided in rate-limit diagnostics and retained proof manifests.
- [x] Proof behavior delegates to shared/domain helpers instead of creating a new permanent PR-numbered script.
- [x] Browser assertions remain behavior/proof meaningful for PR-0408 desktop and phone design states.
- [x] Tests and verification are sufficient for this remediation.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0408` | Independent retained review recorded for the PR-0408 proof-helper remediation with decision `approved`. |
