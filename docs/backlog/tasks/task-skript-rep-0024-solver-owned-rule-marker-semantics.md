---
type: task
id: TASK-SKRIPT-REP-0024
title: Solver-owned rule marker semantics
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Given a visible rule marker represents a soft solver rule, when the frontend renders
  the marker, then success, warning, and error tones come from solver-owned diagnostics
  or are not shown as fulfillment truth.
- Given `Håll nära` places two students across a relation that the solver treats as
  acceptable or as a tradeoff, when markers render, then the frontend does not independently
  mark the pair as a hard red conflict.
- Given `Nära läraren` is evaluated, when marker tones render, then the frontend does
  not use a separately maintained teacher-zone rule that can drift from the backend
  topology/scoring contract.
- Given no solver-owned per-rule diagnostic exists for a soft rule, when a map renders,
  then the marker may show rule participation but not a misleading fulfilled/conflict
  state.
- Given fixed-seat markers render, when the assigned student sits in or outside the
  exact fixed seat, then the direct hard-rule marker may still use local exact-seat
  truth.
- Given backend diagnostics are added, when `Håll nära` is evaluated, then pair and
  group outcomes distinguish desired success, acceptable degraded placement, and failed
  placement using backend topology and seating context.
- Given students sit at a shared round or square table, when a `Håll nära` pair is
  placed across the table in a backend-approved close relation, then the diagnostic
  can classify that as `satisfied` rather than a row-layout failure.
- Given students sit in bench or row layout, when a `Håll nära` pair is not left/right
  adjacent, then the backend diagnostic classifies it as degraded or failed according
  to the accepted row-layout rule and proves that with unit tests before frontend
  coloring.
- Given a seating workspace is reloaded or rehydrated after a Smart seating run, when
  the current persisted draft, smart-rule shape, template, roster, and seat assignments
  still match the solver input, then backend-owned rule diagnostics are recomputed
  and returned so soft-rule marker tones survive reload without persisting stale diagnostic
  blobs.
- Given diagnostics are returned from workspace load or Smart-run responses, when
  the frontend maps them to marker tones, then every diagnostic carries a freshness
  key or digest derived from draft revision, smart-rule shape, template, roster, and
  seat assignments, and stale or mismatched diagnostics render neutral.
---

## Context

The complete migrated source is retained in these ordered parts:

- [Part 01](task-skript-rep-0024-solver-owned-rule-marker-semantics-part-01.md)
- [Part 02](task-skript-rep-0024-solver-owned-rule-marker-semantics-part-02.md)

## Impact And Escalation

Detailed content is retained in the ordered parts listed above.

## Decision And Assumption Ledger

Detailed content is retained in the ordered parts listed above.

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

## Lessons Learned

Detailed content is retained in the ordered parts listed above.

## Notes

Detailed content is retained in the ordered parts listed above.

## Readiness

Detailed content is retained in the ordered parts listed above.

## Closeout

Detailed content is retained in the ordered parts listed above.
