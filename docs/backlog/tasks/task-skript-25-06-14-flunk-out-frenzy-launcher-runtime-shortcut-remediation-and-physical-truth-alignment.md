---
type: task
id: TASK-SKRIPT-25-06-14
title: 'Flunk-Out Frenzy: launcher runtime shortcut remediation and physical-truth alignment'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: in_progress
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-25-06
task_kind: story
acceptance_criteria:
  - Given route admission currently promotes speed from inferred charge and a hard floor, when this task is complete, then accepted route travel derives from directly observed launcher contact/release state and does not upgrade velocity beyond what runtime evidence supports.
  - Given route progression currently advances the ball by direct `setTranslation(...)` and `setLinvel(...)` writes along authored route points, when this checkpoint is complete, then any remaining transport shortcut is treated as explicit blocked debt rather than being narrated as a completed physical rail.
  - Given `handoffVelocity` is the only acceptable declared bounded heuristic from `PR-0212`, when this task is complete, then any remaining non-simulated behavior is isolated to the terminal board handoff and is never overstated as continuous route physics.
  - Given the proof surface is now truthful and operational through `PR-0213` and `PR-0214`, when this task is complete, then the canonical focused tests and live Playwright trace continue to serve as the decision gate for whether runtime remediation actually improved physical truth.
  - Given automated traces can still mask the known inert-launch false-green risk, when this task is complete, then acceptance remains blocked until a manual launcher matrix check for `rest`, `short`, `medium`, `full`, and `relaunch` is recorded in `.codex/handoff.md` alongside the automated evidence.
  - Given this slice is now a bounded runtime-honesty checkpoint rather than the physical-carrier cut-over itself, when this task is complete, then no new carrier-role schema, donor overhead collider cut-over, or baseline repin is smuggled into the slice.
backlog_document_profile: contract-derived
---

## Implementation Contract

Partly canceled on 2026-10-28 under TASK-SKRIPT-REP-0055 D2, status unchanged. Route-transport remediation is cancelled as superseded by the epic 33 carrier cut-over (TASK-SKRIPT-33-01-01, 33-01-02, 33-01-03, all `ready`): the direct ball-body writes in `LauncherTravelRoute.ts` and `launcherChain3d.ts` stay as declared blocked debt and the cut-over is blocked on those tasks. Observed-speed route admission is already in code (`launcherChain3d.ts:424-432`). The manual launcher matrix check (rest, short, medium, full, relaunch) is still unrecorded and stays a user gate. The part files of this task hold its detailed content and stay.

## Context

The complete migrated source is retained in these ordered parts:

- [Part 01](task-skript-25-06-14-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment-part-01.md)
- [Part 02](task-skript-25-06-14-flunk-out-frenzy-launcher-runtime-shortcut-remediation-and-physical-truth-alignment-part-02.md)

## Decision And Assumption Ledger

Detailed content is retained in the ordered parts listed above.

## Story Contract Slice

Detailed content is retained in the ordered parts listed above.

## Contract Inputs

Detailed content is retained in the ordered parts listed above.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

Detailed content is retained in the ordered parts listed above.

## Implementation Steps

Detailed content is retained in the ordered parts listed above.

## Proof

Detailed content is retained in the ordered parts listed above.

## Validation

Detailed content is retained in the ordered parts listed above.

## Stop Conditions

Detailed content is retained in the ordered parts listed above.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The route-transport remediation is canceled as superseded by the epic 33 carrier cut-over (TASK-SKRIPT-REP-0055 D2, 2026-10-28); the manual launcher matrix check and the blocked-debt declaration stay in this task. |

## Lessons Learned

Detailed content is retained in the ordered parts listed above.

## Notes

Detailed content is retained in the ordered parts listed above.

## Plan Document Review

Detailed content is retained in the ordered parts listed above.

## Implementation Review

Detailed content is retained in the ordered parts listed above.
