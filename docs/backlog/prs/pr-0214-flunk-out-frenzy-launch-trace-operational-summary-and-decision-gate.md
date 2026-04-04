---
type: pr
id: PR-0214
title: "Flunk-Out Frenzy: launch-trace operational summary and decision gate"
status: done
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-25-06"
tags: ["frontend", "games", "launcher", "telemetry", "playwright", "operations", "summary", "decision-gate"]
dependencies:
  - "PR-0209"
  - "PR-0213"
acceptance_criteria:
  - "Given launch-trace parity now produces a truthful but high-volume raw artifact, when this task is complete, then there is one canonical operator entrypoint that produces the raw artifact plus a compact derived summary artifact in the same run."
  - "Given developers need the trace to act as live-testing eyes and ears, when this task is complete, then the derived summary explicitly reports implementation-status verdicts, anomaly flags, and spotlight rows without requiring manual inspection of hundreds of raw trace steps."
  - "Given debugging still requires ground truth, when this task is complete, then every summary claim can be traced back to raw row evidence and the summary never embellishes or upgrades missing truth."
  - "Given review and implementation decisions need a stable rubric, when this task is complete, then the trace output includes an explicit gate outcome (`pass`, `pass_with_reservations`, or `blocked`) with documented rules for status assessment, debugging, and go/no-go decision making."
  - "Given this slice owns only the operational use of the existing truthful trace surface, when this task is complete, then no launcher gameplay tuning, no donor geometry changes, and no contract weakening are introduced."
---

## Problem

`PR-0213` remediates the live trace contract so the browser proof now emits a
truthful raw launch-to-drop artifact. That closes the false-green parity gap,
but it does not yet make the trace practical as an operational tool.

The current artifact is evidence-rich but review-poor: it stores the right
truth, yet it is still too large and too low-level to act as a reliable first
read during live testing, implementation assessment, or debugging. If
developers must manually scan hundreds of rows before they can answer "did the
implementation succeed?" or "what changed?", then the trace is not yet serving
as the canonical eyes-and-ears surface the launcher lane needs.

## Goal

Turn the truthful launch-trace artifact into a canonical operational surface
for three workflows:

1. status assessment during live testing
2. debugging and anomaly triage
3. ground-truth-backed decision making during review and implementation

The raw trace remains the source of truth. This slice adds the summary,
spotlight, and gate layers that make that truth usable.

## Non-goals

- No launcher speed, charge, handoff, or route-behavior changes.
- No donor geometry or seam-topology edits.
- No live/focused contract weakening.
- No replacement of the raw trace artifact as retained evidence.
- No broad telemetry-platform rewrite outside the Flunk-Out Frenzy launch lane.

## Scope lock (bounded)

Primary implementation scope:

- `scripts/playwright_flunk_out_frenzy_launch_trace_parity_check.py`
- `scripts/playwright_flunk_out_frenzy_launch_trace_check.py`
- a new launch-trace summarizer module adjacent to the focused Playwright path
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launchTraceContract.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launchTraceMatrix.ts`
- focused proof tests that lock summary derivation against raw rows

Operational/docs scope:

- a runbook or reference doc describing the canonical command, output files, and
  interpretation workflow
- `.agents/handoff.md`
- `docs/index.md`

Out of scope:

- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/launcherChain3d.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/world/PhysicsWorldLauncher.ts`
- `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/table/prototypeAlphaTableSpec.ts`
- any runtime slice that changes what the raw trace means

## Canonical operating model

This slice defines one canonical operating flow:

1. run the focused browser proof entrypoint
2. produce the canonical raw trace artifact
3. derive a canonical summary artifact from raw rows only
4. read the summary first for status/debugging/decision support
5. jump from summary spotlight rows back to raw trace rows when deeper proof is
   needed

Required canonical surfaces:

- canonical command:
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_parity_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`
- canonical raw artifact:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
- canonical machine summary artifact:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.json`
- canonical human summary artifact:
  - `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-summary.md`

The legacy launch-trace command remains as a compatibility wrapper, but the
focused parity entrypoint is the authoritative operator command.

## Required summary layers

### 1. Status assessment layer

Per case, the summary must report:

- case id
- case verdict
- observed phase chain
- `sw16_exit_observed`
- `handoff_to_board_step`
- `first_board_collision_step`
- seam-transition count
- strike classification
- peak speed / displacement deltas
- anomaly flags

### 2. Debugging spotlight layer

Per case, the summary must extract only the rows developers usually need first:

- first row for each newly observed phase
- each non-null `seam_transition`
- first `handoff_to_board`
- first `board_drop_preimpact`
- first board-collision row

Every spotlight row must retain enough raw identity to let a developer jump
back to the source trace without guesswork.

### 3. Decision gate layer

The summary must publish two explicit verdict surfaces:

- per-case verdict:
  - `case_pass`
  - `case_attention`
  - `case_blocked`
- run-level verdict:
  - `pass`
  - `pass_with_reservations`
  - `blocked`

Case verdicts explain the status of each individual matrix case. The run-level
verdict is an aggregate operator decision for the whole trace run.

The run-level verdict must never be inferred implicitly from prose. It must be
derived from the case verdicts plus the run-level rubric below.

## Baseline source

All drift checks in this PR must compare against one pinned, deterministic
baseline source rather than whichever prior local artifact happens to exist.

For this slice, the approved baseline source is:

- baseline source:
  - `frontend/apps/skriptoteket/.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`

Guardrails:

- the summarizer may not auto-discover "latest prior run" baselines
- the baseline source above is the repo-defined default for `PR-0214`
- the summarizer may allow an explicit override only if that override is passed
  intentionally and surfaced in the derived summary output
- if the baseline artifact is missing, unreadable, or schema-incompatible, the
  summary must report that condition explicitly instead of silently skipping
  drift checks
- missing baseline handling must itself be part of the gate rubric so operator
  output stays deterministic

## Case-verdict rubric

### `case_pass`

Use `case_pass` when:

- the case has no invariant violations
- all required raw phases for that case are present
- all spotlight claims are backed by raw rows
- no case-level drift threshold is exceeded

### `case_attention`

Use `case_attention` when:

- the case remains contract-valid, but
- one or more anomaly or drift checks exceed the attention threshold without
  invalidating the trace contract

### `case_blocked`

Use `case_blocked` when:

- the case has invariant violations
- required raw phases are missing
- spotlight claims cannot be backed by raw rows
- required seam truth is absent
- baseline comparison for required drift checks cannot be performed

## Run-level verdict rubric

The summary must publish one explicit outcome for the run:

- `pass`
- `pass_with_reservations`
- `blocked`

That verdict must be rule-driven, not narrative.

### `pass`

Use `pass` only when all of the following hold:

- every case verdict is `case_pass`
- no required baseline comparison failed
- no run-level drift threshold is exceeded

### `pass_with_reservations`

Use `pass_with_reservations` when:

- no case verdict is `case_blocked`, but
- one or more case verdicts are `case_attention`, or
- one or more run-level drift/anomaly checks exceed the attention threshold
  without invalidating the trace contract itself

Examples:

- repeated long `board_drop_preimpact` spans
- large but non-blocking handoff-step shifts
- velocity/displacement drift beyond the review threshold

### `blocked`

Use `blocked` when:

- any case verdict is `case_blocked`
- any required baseline comparison cannot be performed
- artifact schema/cadence drifts away from the declared canonical contract

## Drift checks

This slice must define explicit drift checks for reviewable implementation
assessment. At minimum:

- phase-order drift
- handoff-step drift
- first-board-collision drift
- peak-speed drift
- max-displacement drift
- strike-classification drift

Thresholds must be documented and encoded so the summary can explain whether the
run is stable, attention-worthy, or blocked.

Each drift check must state:

- whether it is evaluated per case or per run
- which baseline field it compares against
- the threshold for `case_attention` / `pass_with_reservations`
- the threshold for `case_blocked` / `blocked`

If thresholds are uncertain, this PR may introduce a conservative initial set,
but those thresholds must be explicit and test-backed rather than hand-waved in
review comments.

## Implementation plan

1. Formalize the canonical entrypoint:
   - keep `playwright_flunk_out_frenzy_launch_trace_parity_check.py` as the
     authoritative browser proof command
   - keep `playwright_flunk_out_frenzy_launch_trace_check.py` as a thin
     compatibility wrapper only
2. Add a launch-trace summarizer:
   - derive summary data strictly from the canonical raw artifact
   - emit machine-readable and human-readable outputs
3. Encode the status/debug/decision layers:
   - case verdicts with explicit `case_pass` / `case_attention` / `case_blocked`
     semantics
   - spotlight rows
   - gate outcome and rationale
   - drift checks and anomaly flags using one pinned baseline source
4. Lock derivation truth in tests:
   - summary rows must be backed by raw row evidence
   - spotlight rows must correspond to actual raw rows
   - case-verdict and run-verdict logic must be deterministic
   - baseline resolution and missing-baseline handling must be deterministic
5. Document the operating method:
   - add a short runbook/reference explaining how to use the trace for live
     testing, debugging, and decision making
   - update `.agents/handoff.md` with the canonical command and artifact set

## Test plan

- Focused proof verification:
  - `pdm run fe-test -- --run src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.proof.spec-impl.ts`
- Summary/gate verification:
  - add focused tests for the summarizer and gate rubric
  - assert that summary/spotlight claims are raw-row-backed only
- Browser proof verification:
  - `pdm run python -m scripts.playwright_flunk_out_frenzy_launch_trace_parity_check --base-url http://127.0.0.1:5173 --artifact-dir .artifacts/flunk-out-frenzy-launch-to-drop`
- Quality gates:
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run docs-validate`

## Rollback plan

- If the summary/gate design proves misleading, roll back only the derived
  summary and gate layers.
- Do not remove the canonical raw trace artifact or the truthful parity surface
  established by `PR-0213`.
- If the first threshold set proves too strict or too weak, adjust it in a
  follow-up refinement slice rather than quietly weakening the operator gate.
