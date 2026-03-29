---
type: pr
id: PR-0166
title: "ST-30-02: transition continuity adoption and remaining transition audit"
status: done
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-30-02"
tags: ["frontend", "ux", "transitions", "editor", "vault", "tool-run", "planner", "playwright"]
dependencies:
  - "ADR-0077"
  - "EPIC-30"
  - "ST-30-01"
acceptance_criteria:
  - "Given the editor workspace shell is the first adoption target, when this PR lands, then editor mode changes use the continuity pattern without introducing blank states or shell jump cuts."
  - "Given the rules map, file picker, and Vault are smaller same-shell selector surfaces, when this PR lands, then they preserve continuity during body swaps or refreshes instead of replacing the current surface with an empty loading state."
  - "Given the SPA still contains older `out-in` transitions, when this PR lands, then those surfaces have been audited and any clearly broken continuity cases are remediated while acceptable small-scope swaps are left unchanged with rationale."
  - "Given this slice changes UI behavior, when this PR lands, then focused tests, live browser proof, and handoff evidence are recorded."
---

## Problem

The continuity rule is now documented, but the app still has several remaining selector-driven
surfaces that either swap abruptly or temporarily replace live content with loading/blank states.

## Goal

Apply the continuity pattern across the remaining qualifying surfaces, starting with the editor,
while auditing the remaining `out-in` transitions and fixing only the ones that still produce a
real continuity defect.

## Non-goals

- Reworking every animation in the SPA
- Changing backend behavior or data contracts
- Reopening the already-fixed main planner shell transition lane

## Implementation plan

1. Adopt continuity in the editor workspace mode surface.
2. Adopt local continuity in the rules map view switch.
3. Add retained-surface/local crossfade handling to the tool file picker body switch.
4. Keep Vault results rendered during refresh and remove any empty refresh gap.
5. Audit `App.vue`, `ProfileView.vue`, `ProfileInlineField.vue`, and `AuthTopBar.vue`, then fix only
   the cases that still violate the continuity goal.
6. Add/update focused tests and run live browser proof.

## Test plan

- `pdm run fe-test -- --run src/App.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/components/tool-run/ToolFileFieldPicker.spec.ts src/components/vault/VaultPanel.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof on `http://127.0.0.1:5173`

## Rollback plan

- Revert the continuity adoption slice together if any affected shell becomes less stable.
- Keep `ADR-0077` as the decision baseline; rollback should not reintroduce `out-in` as the
  preferred pattern.

## References

- Story parent: [ST-30-02](../stories/story-30-02-adopt-transition-continuity-across-editor-and-selector-shells.md)
- Epic parent: [EPIC-30](../epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md)
- Transition ADR: [ADR-0077](../../adr/adr-0077-same-shell-transition-continuity.md)
- Transition reference: [REF-frontend-transition-continuity-v1](../../reference/ref-frontend-transition-continuity-v1.md)
