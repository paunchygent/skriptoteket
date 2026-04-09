---
type: pr
id: PR-0248
title: "ST-29-02 follow-up: recovered export silence, rules rail stickiness, and overview copy cleanup"
status: done
owners: "agents"
created: 2026-04-09
updated: 2026-04-09
stories:
  - "ST-29-02"
tags: ["frontend", "ux", "klassrumskartan", "planner", "copy", "export"]
dependencies:
  - "ST-29-02"
  - "ST-29-10"
  - "PR-0153"
  - "PR-0155"
  - "PR-0161"
acceptance_criteria:
  - "Given a teacher already completed a grouping or seating export earlier, when they later re-enter the same workspace and the active draft restores a recoverable succeeded export job, then no success toast is replayed merely because that old export exists."
  - "Given a grouping or seating export was still processing when the teacher left the workspace, when the active draft later restores that in-flight export and it completes after recovery, then the success toast still appears once when the recovered export actually finishes and the file remains available through `Mina filer`."
  - "Given a teacher triggers a new grouping or seating export in the current interaction flow, when the export completes and the browser download is triggered, then the normal success toast still appears once as immediate action feedback."
  - "Given `Regler` renders at the canonical `laptop` (`1366x768`) and `desktop` (`1440x900`) review widths, when the workspace is taller than the rail content, then the left rules tool rail stays locally sticky and visually bounded like the other planner support rails instead of stretching to the full map height."
  - "Given no classlist is selected in `Översikt`, when the class overview renders, then `Ingen klass vald` remains the only heading and no extra `VÄLJ EN KLASSLISTA` metadata label appears beside it."
---

## Status note

This PR is implemented locally and verified. The shipped shape keeps recovered export feedback
truthful and transient, aligns the `Regler` rail with the other bounded sticky planner support
lanes, and removes the redundant no-class metadata label from overview.

## Problem

The current planner still carries three small but visible presentation-truth gaps:

- recovered authenticated export state replays a success toast on workspace re-entry even though the
  action already happened earlier
- the `Regler` tool rail stretches to the full canvas height instead of behaving like the other
  bounded sticky support rails
- the no-class overview heading repeats itself through an unnecessary uppercase metadata label

Individually these are narrow issues. Together they weaken the calm, instrument-like workspace
direction already locked by `ST-29-02` and `ST-29-10`.

## Goal

Ship one narrow shared-planner follow-up that:

- keeps export success toasts tied to the live completion moment only
- restores the intended locally sticky, bounded `Regler` rail posture
- removes the redundant no-class overview metadata label

## Non-goals

- Changing export API contracts, job persistence, or `Mina filer` ownership
- Reworking the `Regler` map, summary panel, or rule-authoring interaction model
- Broadening the overview into a larger copy or layout redesign
- Reopening guest/public export behavior from `PR-0232`

## Recommended product copy

### Export behavior

- Keep the existing live-success toast pattern for exports started in the current session flow.
- Do not introduce a replacement banner, persistent status strip, or return-notice toast when a
  recovered export is already complete.

### No-class overview heading

- Keep:
  - primary heading: `Ingen klass vald`
- Remove:
  - secondary metadata label: `VÄLJ EN KLASSLISTA`

The selector and empty-state copy already provide enough guidance:

- selector placeholder: `Välj klasslista`
- empty-state body: `Välj en klasslista för att visa en kompakt elevöversikt här.`

## Implementation plan

1. Tighten the shared authenticated export-recovery seam rather than treating this as a generic toast cleanup.
   - Update the shared recovery logic in the planner export-flow layer and the grouping/seating wrappers together so the same contract applies to both workspaces.
   - Keep recovered export polling and state restoration for active in-flight work.
   - Suppress success replay only when the restored export is already terminal `succeeded` on workspace entry.
   - Preserve the recovered-success announcement for exports that were still in flight at restore time and finish later after recovery.
   - Keep live export success toast behavior for newly completed current-session exports.
   - Do not replace the removed replay with a banner or another persistent reminder surface.

2. Restore a bounded sticky `Regler` rail contract.
   - Keep the current left-rail + map composition from `PR-0155`.
   - Make the rail locally sticky with the same desktop support-surface posture as the other
     planner side rails.
   - Bound rail height and let internal content scroll if the tool state grows taller than the
     sticky lane.

3. Remove the redundant no-class metadata label in `Översikt`.
   - Keep `Ingen klass vald` as the sole title.
   - Leave the selector placeholder and empty-state helper copy intact.

4. Lock the intended behavior in focused frontend tests and live browser proof.
   - Update both export-flow specs so they separately prove silent historical-success recovery and one-time recovered in-flight completion success.
   - Keep the layout/copy proof isolated to the existing `Regler` rail and overview specs.

## Test plan

- `pdm run fe-test -- --run src/views/apps/useGroupingExportFlow.spec.ts src/views/apps/useSeatingExportFlow.spec.ts`
- `pdm run fe-test -- --run src/views/apps/components/PlannerRulesWorkspacePane.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio` at `1366x768`
  and `1440x900`:
  - complete a fresh export and confirm the live success toast still appears once
  - leave and re-enter the same workspace and confirm no old export-success toast reappears
  - prove through the export-flow specs that restored in-flight completion still announces once on later completion without widening the restored-export seam into an automatic browser download path
  - open `Regler` and confirm the left rail stays sticky and bounded instead of stretching the full
    workspace height
  - open `Översikt` with no selected classlist and confirm `Ingen klass vald` renders without the
    extra uppercase metadata label

## Rollback plan

- Revert the authenticated export re-entry change, rules-rail geometry adjustment, and overview
  copy cleanup together if the follow-up proves the wrong interpretation of the current planner
  continuity contract.

## Implementation notes

- Export recovery:
  - historical recovered `succeeded` jobs now restore silently on workspace entry
  - recovered in-flight jobs still poll in the background and announce once when they later finish
  - live exports started in the current interaction flow still auto-download and toast immediately
- Rules workspace:
  - the rules rail now uses a dedicated bounded sticky lane with the shared planner toolbar offset
  - rail content scrolls internally instead of stretching the full workspace column height
- Overview:
  - `Ingen klass vald` remains the sole heading when no classlist is selected
  - the selector placeholder and empty-state helper copy remain unchanged

## References

- Story parent:
  [ST-29-02](../stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md)
- Related overview guidance story:
  [ST-29-10](../stories/story-29-10-klassrumskartan-first-run-workspace-gating-and-prerequisite-guidance.md)
- Export-flow baseline:
  [PR-0153](pr-0153-klassrumskartan-shared-export-flow-composable-and-planner-hotspot-reduction.md)
- Shell-compression baseline:
  [PR-0161](pr-0161-st-29-02-shared-sticky-workspace-toolbar-and-transient-feedback-cutover.md)
- Rules-workspace baseline:
  [PR-0155](pr-0155-klassrumskartan-rules-workspace-dual-map-authoring-and-summary-cutover.md)
- Workspace doctrine:
  [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
