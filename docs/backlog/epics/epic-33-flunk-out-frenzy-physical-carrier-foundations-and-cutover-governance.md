---
type: epic
id: EPIC-33
title: "Flunk-Out Frenzy physical carrier foundations and cut-over governance"
status: active
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
outcome: "Flunk-Out Frenzy gains the carrier-role schema, launcher-world ownership rules, donor overhead collider foundation, observation-spine proof layer, and cut-over governance needed to replace route-driven launcher transport with a truthful physical carrier graph without weakening PR-0214."
dependencies:
  - "EPIC-25"
  - "PR-0212"
  - "PR-0213"
  - "PR-0214"
  - "PR-0215"
  - "PR-0216"
  - "REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04"
risks:
  - "Carrier foundations could be bypassed by runtime-only shortcuts if the cut-over lane is not explicitly blocked."
  - "Rapier tuning could be used to hide modeling gaps unless ownership and carrier roles are explicit first."
  - "The existing ST-25-06 cut-over tasks could continue under stale route-driven assumptions unless this epic is made an explicit prerequisite."
---

## Scope

- Define the carrier-role model required by
  `REF-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04`.
- Separate physical carrier roles from proof/observation roles in authored and
  compiled launcher contracts.
- Establish launcher-world ownership for every causal elevated-route surface
  through one terminal board handoff seam.
- Add the observer shadow mode and cut-over readiness gate required before any
  transport deletion or baseline repin.

## Out of scope

- Final physical carrier cut-over.
- Baseline repin in `PR-0214`.
- Broad whole-table gameplay-fidelity claims beyond the launcher/elevated-route
  boundary.

## Risks

- If this epic is skipped, later runtime work will be forced to invent carrier
  semantics inside launcher runtime code.
- If this epic weakens the proof surface, it fails its purpose even if the
  schema looks cleaner.
- If world ownership remains ambiguous, cross-world causality may continue to
  hide behind transport shortcuts.

## Stories

- [ ] [ST-33-01: Flunk-Out Frenzy physical carrier foundations and cut-over governance](../stories/story-33-01-flunk-out-frenzy-physical-carrier-foundations-and-cutover-governance.md)

## Notes

- This is a corrective foundation epic created after the architect direction in
  `docs/reference/ref-flunk-out-frenzy-physical-rail-architect-direction-2026-04-04.md`.
- It exists so physical cut-over work does not improvise missing carrier-role
  schema, compiler ownership, or observer-proof contracts inside `ST-25-06`
  runtime tasks.
- Until `ST-33-01` is complete, `PR-0200`, `PR-0202`, and `PR-0203` remain
  blocked for further continuation.

## Implementation Summary (as of 2026-04-04)

- `REV-EPIC-33` is now approved, so this corrective foundation epic is active.
- `ST-33-01` is the approved prerequisite before any further physical cut-over
  continuation resumes.
- `PR-0220` is now the final offline-review and decision packet before
  implementation starts.
- `PR-0217`, `PR-0218`, and `PR-0219` define the approved schema, compiler, and
  observer-governance sequence for the carrier-model foundation lane after that
  final review checkpoint.
