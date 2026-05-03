---
type: review
id: REV-PR-0282
title: "Review: PR-0282 shared-link PDF download spinner contract"
status: approved
owners: "agents"
created: 2026-05-03
updated: 2026-05-03
reviewer: "lead-developer"
prs:
  - PR-0282
links:
  - EPIC-26
  - ST-26-06
  - ST-29-11
  - PR-0276
  - PR-0281
---

## TL;DR

`PR-0282` is approved after re-review. The implementation keeps the static
share-page action boundary, reserves spinner geometry, suppresses duplicate
activations while busy, and now treats the spinner as a short browser-handoff
guard rather than a fake download-completion tracker.

## Problem Statement

The review checks the implemented `Ladda ner PDF` busy-state controller for
public Klassrumskartan share pages. The user-reported problem is not just
duplicate clicks or layout shift; it is that the spinner keeps running after the
browser download has completed unless another browser action or timeout occurs.

## Proposed Solution

Keep the static share-page boundary and the renderer-owned action module, but
change the controller contract from "persistent until timeout/focus" to an
honest browser-handoff guard or explicitly govern a stateful download flow. A
normal anchor download does not give page JavaScript a reliable completion event,
so the remediation must avoid pretending that the page can observe completion
without changing architecture.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0282-st-26-06-shared-link-pdf-download-spinner-contract.md` | Scope, acceptance, evidence claims | 8 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_download_action_renderer.py` | Static action CSS, markup, and controller lifecycle | 15 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_renderer.py` | Share document integration boundary | 5 min |
| `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_download_controller.py` | Test strength and missing recovery assertions | 8 min |
| `.artifacts/pr-0282-share-pdf-spinner-proof/proof.json` | Browser proof claims for busy state and duplicate activation | 6 min |
| `.artifacts/pr-0282-live-route-proof/manifest.json` | Live-route proof claims for backend-generated download | 6 min |

**Total estimated time:** ~48 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the tiny static public-share controller boundary | The slice must still avoid Vue hydration, API polling, token logging, and share/PDF semantic changes. | [x] |
| Keep in-button busy feedback with reserved spinner geometry | The geometry and duplicate-activation goals are aligned with `PR-0281`. | [x] |
| Treat browser download completion as observable from page JavaScript | Ordinary anchor downloads do not provide a reliable page-visible completion event. | [ ] |
| Accept proof that only records busy state plus one download event | The proof does not assert recovery after successful browser handoff. | [ ] |

## Review Checklist

- [x] Scope is limited to shared-link PDF action chrome and controller behavior.
- [x] No Vue hydration, fetch, XHR, API polling, token logging, route change, or PDF renderer change is introduced.
- [x] Spinner slot is reserved and action geometry is stable in idle and busy states.
- [x] Duplicate activation is suppressed while the action is busy.
- [x] Successful browser download handoff clears the visible busy state without waiting for the 15s fallback or user focus/visibility action.
- [x] Browser proof asserts idle recovery, restored `href`, and cleared `aria-busy`/`aria-disabled` after the first download event.
- [x] The task evidence distinguishes browser handoff from download completion and does not overclaim what anchor downloads expose to page JavaScript.

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-03`
**Verdict:** `changes_requested`

### Required Changes

1. **P1: Busy state still waits for timeout or focus.**

   `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_download_action_renderer.py:145`
   schedules `clearBusy(action)` only through the 15 second fallback timer.
   The other recovery paths are `pageshow`, `focus`, and `visibilitychange`.
   There is no successful-download or browser-handoff recovery path.

   Reproduction from the review: Chromium emitted a Playwright download event,
   but 2.5 seconds later the anchor still had
   `data-skriptoteket-share-pdf-download-state="busy"`, `aria-busy="true"`,
   `aria-disabled="true"`, and no `href`. It restored only after the timeout.

   Why it matters: this preserves the reported bug. The button can still look
   stuck after the PDF download has completed unless the user waits or performs
   another browser action.

   Required fix: either make the action a short browser-handoff guard that
   clears automatically after the handoff window, or create a separately
   governed stateful download flow. Do not claim ordinary anchor downloads give
   page JavaScript a reliable completion event.

   Proof required:

   - tracked browser proof that clicks the real rendered action, observes the
     browser download event, waits a bounded interval, and asserts idle state,
     restored `href`, and cleared `aria-busy`/`aria-disabled`
   - duplicate activation still produces exactly one download during the guard
     window
   - focused command should include the PR-0282 proof script or the new tracked
     Playwright test once it exists

2. **P2: Proof never asserts recovery.**

   `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_download_controller.py:61`
   checks for controller substrings, and the proof manifests record the busy
   snapshot plus one download event. Neither surface proves that the button
   returns to idle after a successful browser download without focus,
   visibility, pageshow, or timeout recovery.

   Why it matters: the evidence went green while missing the exact lifecycle
   path under review.

   Required fix: add or track a browser-level proof that mechanically asserts
   post-download recovery, not just busy-state entry and duplicate suppression.

### Suggestions (Optional)

- Prefer the "short handoff guard" interpretation unless product ownership
  explicitly wants to govern a stateful download route. It matches the static
  share-page constraint and avoids introducing a fake completion signal.

## Remediation Response

**Status:** approved after re-review on 2026-05-03.

The controller now uses the suggested short handoff-guard interpretation. The
static share-page action still preserves normal anchor/download behavior, still
removes `href` while busy to suppress duplicate activation, and now clears busy
state through a 1.8 second browser-handoff guard instead of waiting for the old
15 second timeout/focus/visibility/page lifecycle recovery.

New retained proof:

- `PYTHONPATH=src:. pdm run python -m scripts.prove_pr_0282_share_pdf_download_handoff`
- Artifact manifest:
  `.artifacts/pr-0282-share-pdf-download-handoff/20260503T162714829953Z/proof.json`

The proof clicks renderer-produced grouping and seating `Ladda ner PDF` actions
at desktop and mobile widths, observes one Playwright browser download event,
attempts duplicate mouse and keyboard activation during the guard, and then
asserts recovered idle state with restored `href`, cleared `aria-busy` /
`aria-disabled`, hidden spinner, and stable action x-position/width. It records
browser handoff only; it does not claim page JavaScript observes ordinary anchor
download completion.

### Re-review Closeout

**Reviewer:** `lead-developer`
**Date:** `2026-05-03`
**Verdict:** `approved`

The re-review found no remaining blockers. The original P1 is closed because
the controller no longer waits for the old 15 second timeout/focus-only
lifecycle; it clears through the short browser-handoff guard and keeps
focus/visibility/page lifecycle recovery only as fallback cleanup. The original
P2 is closed because the retained Playwright proof now asserts recovered idle
state, restored `href`, cleared `aria-busy`/`aria-disabled`, hidden spinner,
stable geometry, and one download event after duplicate mouse/keyboard
activation attempts.

Verification rerun during closeout:

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_download_controller.py
PYTHONPATH=src:. pdm run python -m scripts.prove_pr_0282_share_pdf_download_handoff
pdm run docs-validate
pdm run handoff-validate
pdm run lint
pdm run typecheck
git diff --check
```

### Decision Approvals

- [x] Keep the tiny static public-share controller boundary
- [x] Keep in-button busy feedback with reserved spinner geometry
- [ ] Treat browser download completion as observable from page JavaScript
- [x] Reject JavaScript-observed completion and document browser handoff instead
- [x] Require proof for recovered idle state after browser handoff

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0282` | Created retained implementation review with `changes_requested` status for the PDF download busy lifecycle gap. |
| 2 | `PR-0282` | Reopened the PR slice from done to in-progress and linked the retained review gate. |
| 3 | `share_download_action_renderer.py` | Replaced the completion-looking timeout lifecycle with a short browser-handoff guard and retained lifecycle/focus cleanup as fallback recovery. |
| 4 | `scripts/prove_pr_0282_share_pdf_download_handoff.py` | Added retained Playwright proof for post-download-event idle recovery, restored `href`, cleared busy attributes, duplicate suppression, and stable geometry. |
| 5 | `PR-0282` / `ST-26-06` / `ST-29-11` / `.codex/handoff.md` | Updated governed docs to request re-review without claiming approval. |
| 6 | `REV-PR-0282` / `PR-0282` | Re-reviewed remediation, approved the retained review gate, and closed the PR slice. |
