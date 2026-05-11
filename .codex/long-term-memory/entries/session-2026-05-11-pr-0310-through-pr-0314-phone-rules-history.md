---
type: session_long_term_memory
id: session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history
status: active
created: '2026-05-11'
---

# PR-0310 Through PR-0314 Phone Rules History

This entry compacts the long `.codex/handoff.md` history for the
Klassrumskartan small-screen seating/rules sequence before the current PR-0315
lane.

## PR-0310

- Added the phone fixed-seat rules map with classroom-relative geometry and
  touch-target proof.
- Added the retained proof script
  `scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py` to the governed
  Playwright allowlist.
- Added clearer Smart outcome toast copy and global symbol-based rule markers
  that do not cover seat labels or student names.
- Reused the simplified phone classroom map in both phone `Fast plats` rule
  authoring and the phone-only `Sittplatser` workspace.
- Added phone seating short-press removal and long-press move/swap semantics.

## PR-0311

- Stabilized the phone room-template modal and kept the same no-hover/touch
  principle from PR-0310.
- Second-pass review approved the remediation.
- Committed and pushed as `cdd57c7c Stabilize phone room template modal`.

## PR-0312

- Added shared phone classroom-map touch viewport gestures for the room-template
  builder, phone `Sittplatser`, and phone `Regler` / `Fast plats`.
- Added shared native touch handling and direct zoom-factor APIs.
- Review remediation added `touch-action: pan-x pan-y` contracts and retained
  CDP touch proof.

## PR-0313

- Tracked real-device pinch remediation after iPhone testing showed simplified
  phone maps still did not visibly zoom.
- Added reusable non-passive target binding, platform gesture-event support,
  centroid-anchored scroll zoom, two-axis map containment, and bounded
  text/icon scaling from seat-cell geometry.
- Added the `endGestureCamera()` flush fix for the queued gesture-camera scroll
  before clearing pinch state.

## PR-0314

- Removed bad frontend soft-rule evaluator assumptions.
- Added backend-owned solver diagnostics and freshness-key rehydration for
  marker colors.
- Locked oversized `Håll nära` stop-rule copy:
  "För stor grupp för {aktuell regel} att hantera. Minska antalet elever för
  bättre resultat."
- Made near-teacher diagnostics context-aware: row/bench first-row seats in
  every column satisfy the rule, while table layouts use the two closest table
  support groups.
- Added
  `docs/reference/ref-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10.md`.
