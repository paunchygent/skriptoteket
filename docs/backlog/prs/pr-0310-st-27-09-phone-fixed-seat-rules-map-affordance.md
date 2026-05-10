---
type: pr
id: PR-0310
title: "ST-27-09: phone fixed-seat rules map affordance"
status: done
owners: "agents"
created: 2026-05-09
updated: 2026-05-09
stories:
  - "ST-27-09"
  - "ST-29-17"
tags: ["frontend", "ux", "klassrumskartan", "rules-workspace", "fixed-seat", "small-screen"]
dependencies:
  - "PR-0290"
  - "PR-0298"
  - "PR-0304"
acceptance_criteria:
  - "Given `Regler` renders on a phone-sized viewport and the active tool is `Fast plats`, when a classroom template exists, then a classroom-seat map affordance is visible and reachable without leaving the phone rules workspace."
  - "Given the teacher chooses a student and a physical seat on phone, when the pending fixed-seat rule is shown, then both the student and the seat label are visible before `Spara regel` is enabled."
  - "Given the phone fixed-seat map renders, when the classroom has the same template geometry as `Sittplatser`, then seats appear in their classroom-relative positions and saved fixed-seat markers are not detached from the parent classroom template."
  - "Given the phone rules workspace is using relationship tools (`Nära läraren`, `Håll isär`, `Håll nära`), when no physical seat needs to be selected, then the default reduced student-selection flow from `PR-0290` remains intact and is not replaced by the map."
  - "Given no classroom template exists, when the teacher taps `Fast plats`, then the UI explains that a classroom is required and does not present an empty or misleading seat map."
  - "Given tablet, laptop, and desktop widths render, when this slice ships, then the existing desktop `Klassrumsvyn` / `Planeringskarta` rules map behavior from `PR-0298` remains intact."
  - "Given Smart seating applies with a compromise, when the toast is shown, then the copy identifies the compromise category rather than using only generic `basta mojliga kompromiss` language."
  - "Given the compromise is caused by too few physical seats, when the toast is shown, then the teacher sees how many students could not be placed."
  - "Given one or more saved rules apply to a visible classroom-map seat on any viewport, when a seating or rules map renders, then symbolic rule markers appear without covering the seat affordance or the placed student's name."
  - "Given multiple rules apply to one seat or student, when markers render on any seating or rules map surface, then they stack or collapse into a compact symbol cluster with accessible labels and no text badges inside the seat."
  - "Given a visible rule marker represents a satisfied rule, when it renders, then it uses the success token family; given it represents a warning or conflict state, then it uses the warning/error token family."
  - "Given the simplified phone classroom map shows placed students, when multiple students share a first name, then the seat renders the first name and centered last-name initials on a separate row without consuming first-name width."
  - "Given the simplified phone seating map is editable, when the teacher short-presses an occupied seat, then that student is removed; when the teacher long-presses and drags to another seat, then the student is moved or swapped without triggering removal."
---

## Problem

`PR-0290` correctly reduced the phone `Regler` workspace so the desktop rail,
map, and inspector were not squeezed into a narrow viewport. That reduction now
breaks the `Fast plats` workflow: phone users can select students, but they do
not have a visible classroom-seat map where they can choose the physical seat
that a fixed-seat rule requires.

This is a major functional gap because `Fast plats` is not a student-only rule.
It binds exactly one roster student to one physical seat in the active
classroom template.

## Goal

Add a phone-appropriate classroom-seat map affordance for fixed-seat rule
authoring while preserving the reduced relationship-rule flow.

The phone map must be a representation of the active classroom template, not a
separate phone-only seating model. It may be visually simplified, but it must
still preserve seat identity, ordering, and classroom-relative geometry well
enough for the teacher to choose the intended physical place.

## Non-goals

- No backend persistence or solver change.
- No new fixed-seat data shape.
- No removal of `Planeringskarta` or the desktop `Klassrumsvyn`.
- No full desktop rail/map/inspector stack on phone.
- No phone-only classroom template fork or independent seat ordering.

## Design Options

### Option A: Reuse The Existing Rules Map In A Focused Phone Surface

Render `PlannerRulesMapPanel` / `PlannerRulesMapCanvas` inside a phone-only
subordinate surface when `Fast plats` is active. The map uses the same template,
seat ids, fixed-seat markers, and `selectFixedSeatRuleSeat` event path as
desktop.

Pros:

- Lowest semantic risk.
- Reuses the proven fixed-seat and classroom-view implementation.
- Preserves geometry exactly.
- Easier to test against existing rules-map specs.

Cons:

- Can feel visually busy on a phone if rendered at the full desktop density.
- Needs careful containment so it does not recreate the squeezed desktop
  workspace.

### Option B: Build A Phone-Specific Seat Picker From The Same Template

Add a compact `PhoneRulesSeatPicker` style component that reads the active
template seats and renders a simplified spatial grid. It would preserve
geometry and seat ids but omit desktop-only map chrome, labels, and secondary
overlays.

Pros:

- Cleaner phone UX.
- Can prioritize touch target size and selected-seat clarity.
- Easier to place above or below the selected-student panel.

Cons:

- More implementation work.
- Higher drift risk unless it reuses shared room/seat presentation helpers.
- Needs stronger parity tests so phone geometry does not diverge from desktop.

### Option C: Linear Seat List Only

Show a numbered/list-based seat picker while preserving seat order.

Pros:

- Smallest UI surface.
- Simple to implement.

Cons:

- Does not meet the classroom-geometry requirement.
- Teachers cannot reliably map a list item to the physical seat they intend.
- Not recommended.

## Accepted Direction

The reviewed phone layout uses Option B: a phone-specific seat picker that reads
the same classroom template, seat ids, and fixed-seat rule state as desktop, but
renders a simplified touch surface that preserves row/seat geometry without
desktop map chrome.

This keeps the phone workflow compact:

- `Fast plats` active on phone shows a visible classroom-seat map affordance
- the map is backed by the active template's seats
- selecting a seat updates the existing pending fixed-seat rule state
- relationship-rule tools continue to use the current reduced student list flow

The pre-implementation layout was reviewed before implementation: the approved
direction retained seat/row positions and geometry while simplifying the visual
surface to avoid clutter on small screens.

## Post-review Additions

The first phone-map implementation exposed two follow-up UX gaps that belong in
this PR slice because they affect the same phone `Regler` surface and teacher
interpretation of Smart outcomes.

### A. Smart Outcome Toast Diagnostics

Replace generic compromise copy with teacher-actionable outcome categories.

Decompose the copy into these cases:

- `applied_clean`: Smart applied and no tradeoff was detected.
- `applied_with_history`: Smart applied and used history/export support without
  a detected compromise.
- `applied_capacity_shortfall`: Smart applied, but the roster has more students
  than usable seats; the toast must say how many students were left without a
  physical place.
- `applied_rule_compromise`: Smart applied, but one or more soft relationship
  rules could not be fully satisfied.
- `blocked_hard_rule`: Smart did not apply because a hard rule such as `Fast
  plats` was invalid, duplicated, or impossible for the active room.

The current copy `Smart placering klar med bästa möjliga kompromiss.` is too
opaque and sounds stronger than the implementation can guarantee. Preferred
teacher-facing examples:

- `Smart placering klar.`
- `Smart placering klar med stöd av tidigare exporter.`
- `Smart placering klar, men 3 elever fick ingen plats.`
- `Smart placering klar, men alla regler kunde inte uppfyllas.`
- `Smart kunde inte placera fasta platser. Kontrollera reglerna.`

### B. Global Rule Marker Semantics On Seats

Move away from text labels inside map seats. This is a global map presentation
contract, not a phone-only behavior. Seats must preserve the tap or click
target, the physical seat identity, and the placed student name first.
Rule-state affordances are secondary markers on phone, desktop rules-map, and
seating-workspace map surfaces.

Use symbol markers instead of text badges:

- `Fast plats`: lock symbol.
- `Håll nära`: link/connection style symbol.
- `Håll isär`: separation/no-entry style symbol.
- `Nära läraren`: teacher/front-zone symbol if already approved by the symbol
  inventory, otherwise a conservative existing icon wrapper.

Marker colors must use existing token semantics:

- satisfied/honored rule: success token family
- pending/editing rule: warning token family
- violated/conflicting rule: error/critical token family

Do not introduce new one-off colors.

### C. Collision-free Multi-rule Marker Layout

When several rules apply at once, markers must not obscure the seat body or the
student name on any seating or rules-map surface.

Required layout behavior:

- keep the seat button as the primary tap target
- reserve one compact marker lane or corner cluster outside the name baseline
- collapse overflow into a count marker such as `+2` only when space is too
  tight
- expose the full rule names through `aria-label`/`title`
- keep minimum phone touch target proof at `393x852`
- keep desktop/tablet rules-map and seating-workspace markers on the same
  symbol/tone contract

### D. Rule-state Evaluation Boundary

For this slice, marker status can be derived from the current visible workspace
state and existing solver/presentation helpers. Do not add a new persistence
shape unless implementation proves the frontend cannot honestly derive the
state.

Post-deploy iPhone testing proved that this boundary is too permissive for
soft-rule fulfillment tones. `PR-0314` supersedes the local-derivation rule for
`Nära läraren`, `Håll nära`, and `Håll isär`: frontend markers may keep
symbols and layout, but success/warning/error fulfillment truth must come from
solver-owned diagnostics or be omitted for soft rules.

Stop and create a follow-up if the work requires:

- changing the smart-run response contract beyond additive diagnostics
- persisting per-rule solver explanations
- changing fixed-seat hard-rule semantics
- adding a new symbol system outside the current icon wrappers and token
  contract

### E. Phone Seat Name Disambiguation

The simplified phone map must keep the compact first-name presentation, but it
must not make same-first-name students indistinguishable. Render the assigned
student's first name as the primary row and last-name initials as a centered
secondary row below it. Keep long first names constrained with the same
ellipsis/no-overlap rule as the desktop seating token.

### F. Phone Seating Touch Interaction

The simplified phone seating map replaces the cramped per-seat remove button
with direct touch semantics:

- short press on an occupied seat removes that student from the seat
- long press on an occupied seat starts move/swap mode
- releasing over an empty seat moves the student
- releasing over another occupied seat swaps the two students
- the long-press path must suppress the subsequent click/removal event

## Current Frontend Entry Points

- `PlannerRulesWorkspacePane.vue`: phone rules composition and desktop rules
  map wiring.
- `PlannerRulesMapPanel.vue`: map shell and projection switch.
- `PlannerRulesMapCanvas.vue`: classroom/planning map rendering and seat
  selection.
- `PlannerRulesSeatNode.vue`: fixed-seat marker and seat-level presentation.
- `RoomCanvas.vue` and `SeatNode.vue`: seating-workspace classroom map and
  seat-level presentation.
- `useSmartRuleUiState.ts` and `useClassroomState.ts`: pending rule state and
  fixed-seat actions.
- `classroomPlannerSmartRulePresentation.ts`: rule summary labels and stable
  ordering helpers.
- `classroomPlannerSeatRuleMarkers.ts`: shared seat-level symbolic rule marker
  derivation for phone, desktop rules-map, and seating-workspace surfaces.
- `klassrumskartan-phone-workspace.css`: phone rules layout and student tray
  containment.

## Implementation Plan

1. Add focused phone tests that currently fail because `Fast plats` on phone has
   no seat-map affordance.
2. In `PlannerRulesWorkspacePane.vue`, keep the existing phone rule rows and
   student selection for relationship tools.
3. When the active phone tool is `fixed_seat` and a classroom template exists,
   render a subordinate classroom-seat map surface.
4. Wire the phone map to the same pending fixed-seat state:
   - selected student: `pendingFixedSeatStudentId`
   - selected seat: `pendingFixedSeatSeatId`
   - commit: `commitPendingFixedSeatRule`
   - existing rules: `activeFixedSeatRules`
5. Show a compact pending summary before save, for example:
   - `Elev: Vilma Ossner`
   - `Plats: Plats 12`
6. Make `Spara regel` available for fixed-seat rules only when both student and
   seat are selected.
7. If no classroom exists, keep `Fast plats` blocked with short Swedish recovery
   copy rather than an empty map.
8. Keep desktop rules workspace untouched except for shared helper extraction if
   needed to keep `PlannerRulesWorkspacePane.vue` below the file-size target.
9. Add browser proof for phone `Fast plats` authoring plus desktop preservation.
10. Add a small smart-run feedback mapper so toast text is selected from
    explicit outcome categories rather than raw backend phrasing.
11. Add backend/domain diagnostics only as far as needed to distinguish
    capacity shortfall from soft-rule compromise; keep this additive.
12. Replace text rule badges on map seats with symbol markers backed by the
    existing icon wrappers and token families.
13. Add collision-free marker layout for multiple simultaneous rules, including
    an accessible overflow marker where the compact surface needs one.
14. Extend phone Playwright proof to assert marker boxes do not overlap the
    seat name/tap target and that capacity-shortfall toast copy appears when
    seats are fewer than students.

## UX Copy Lock

Use short Swedish action/recovery copy:

- `Välj elev och plats.`
- `Välj en plats i klassrummet.`
- `Fast plats kräver ett klassrum. Välj ett klassrum först.`
- `Spara regel`
- `Smart placering klar, men 3 elever fick ingen plats.`
- `Smart placering klar, men alla regler kunde inte uppfyllas.`

Avoid internal terms such as `template_id`, `seat_id`, solver, payload, or
hydration in visible copy.

## Test Plan

- `pdm run fe-test -- --run PlannerRulesWorkspacePane PlannerRulesMapCanvas PlannerRulesSeatNode useSmartRuleUiState`
- Add focused assertions for:
  - phone `Fast plats` exposes a map when a classroom exists
  - phone seat selection updates pending fixed-seat seat state
  - phone save is disabled until both student and seat are selected
  - relationship-rule phone flow stays student-list-first
  - desktop `Klassrumsvyn` and `Planeringskarta` remain intact
  - smart-run feedback maps capacity shortfall to concrete toast copy
  - smart-run feedback maps soft rule tradeoffs to rule-compromise copy
  - phone, desktop rules-map, and seating-workspace markers use symbols, token
    colors, and accessible labels rather than text badges inside seats
  - multiple markers on one seat do not overlap the seat identity, student
    name, or touch target
  - phone map student labels render first name and last-name initials as
    separate centered rows
  - editable phone seating map supports short-press removal and long-press
    move/swap without firing both actions
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Focused backend/domain tests if additive smart-run diagnostics are added.
- `pdm run docs-validate`
- `git diff --check`
- Live browser proof:
  - phone `393x852`: open `Regler`, choose `Fast plats`, select one student,
    select one seat, save rule
  - phone `393x852`: choose `Håll nära` and verify the reduced student-list
    flow still works
  - laptop/desktop: verify the existing desktop map workspace still renders

## Implementation Closeout

Phone-map implementation and post-review UX additions completed on 2026-05-09.

- Added a phone-only fixed-seat panel that renders the active classroom template
  as a compact seat grid, preserves classroom-relative seat positions, shows
  pending student/seat binding, and reuses the existing fixed-seat rule commit
  state.
- Extracted the relationship-rule phone selected-student panel so `Fast plats`
  can use the map while `Nära läraren`, `Håll isär`, and `Håll nära` keep the
  reduced student-selection flow.
- Added a no-classroom recovery path for phone `Fast plats` instead of showing
  an empty map.
- Fixed the public guest route transition so opening `Regler` from an active
  grouping draft resolves the selected classroom template before phone
  fixed-seat authoring begins.
- Added the retained PR proof to the governed Playwright script allowlist.
- Revised the phone map so classroom geometry is retained inside a scrollable,
  enlarged grid with finger-usable seat targets instead of shrinking seats to
  one tiny raw classroom cell.
- Closed the unloaded-public-guest regression: when `Regler` opens from the
  overview with an active grouping draft and selected classroom, the controller
  now resolves a seating draft before falling back to grouping state.
- Replaced the generic Smart seating compromise toast with explicit capacity
  shortfall and soft-rule compromise copy. Capacity shortfall now reports how
  many students could not be placed.
- Updated Smart grouping compromise copy to use the same explicit soft-rule
  language instead of `bästa möjliga kompromiss`.
- Added compact symbol-based map seat markers for fixed seats, near-teacher,
  keep-near, and keep-apart rules. Markers use a shared
  `classroomPlannerSeatRuleMarkers.ts` derivation module, success/warning/error
  token families, and keep the seat number plus assigned student name as the
  primary seat content on phone, desktop rules-map, and seating-workspace
  surfaces.
- Extracted the simplified phone classroom map into
  `PlannerPhoneClassroomSeatMap.vue` and reused it in the phone-only seating
  workspace branch. Desktop and tablet seating workspaces continue to use the
  full `RoomCanvas`.
- Removed the cramped per-seat `x` remove affordance from the phone seating
  map. On phone, tapping an occupied seat removes that student from the seat;
  drag/drop and swap events remain available through the same shared map
  component where the browser supports them.
- Added phone-map student-name disambiguation: seats render the first name on
  the primary row and compact centered last-name initials on a second row so
  students with the same first name remain distinguishable.
- Added explicit phone seating touch handling: short press removes an occupied
  seat assignment, while long press plus release over another seat moves or
  swaps the student and suppresses the follow-up click removal.
- Aligned near-teacher rule-marker tone with the backend solver's teaching
  anchor semantics: whiteboards take precedence, teacher desks fall back to the
  weighted teaching anchor, and bottom/right anchored classrooms no longer show
  success markers on the wrong side of the room.
- Extended public Smart seating coverage and the retained phone browser proof
  so capacity-shortfall copy is proved in the public/phone path, not only the
  authenticated handler path.
- Raised marked seats above adjacent seat nodes and changed the compact marker
  cluster to stack upward so it does not collide with the remove-seat affordance
  or disappear behind neighboring seats.
- Kept wall fixtures in the simplified phone fixed-seat classroom map attached
  to the room wall edge instead of rendering them as floor furniture.
- Kept the implementation under the strict SRP/file-size boundary: the shared
  marker module is focused, and touched frontend production modules remain
  below 500 lines.
- Extended the retained phone Playwright proof so it asserts saved-rule marker
  placement does not cover the seat label core.

Verification:

- `pdm run fe-test -- --run PlannerPhoneFixedSeatRulePanel PlannerRulesWorkspacePane PlannerRulesMapCanvas PlannerRulesSeatNode useSmartRuleUiState useClassroomPlannerGuestOverviewShell`
- `pdm run fe-test -- --run PlannerPhoneClassroomSeatMap RoomCanvas PlannerSeatingWorkspacePane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/application/apps/classroom_planner/test_smart_seating.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py -q`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py tests/unit/application/apps/classroom_planner/test_smart_seating.py -q`
- `pdm run ruff check scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_seating.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_smart_seating.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_grouping.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_smart_grouping.py tests/unit/application/apps/classroom_planner/test_smart_seating.py`
- `pdm run python -m scripts.playwright_pr_0310_phone_fixed_seat_rules_map --start-backend --start-vite`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

Browser artifact:

- `.artifacts/playwright-pr-0310-phone-fixed-seat-rules-map/phone-fixed-seat-map.png`
- `.artifacts/playwright-pr-0310-phone-fixed-seat-rules-map/phone-capacity-shortfall-toast.png`

## Rollback Plan

Remove the phone fixed-seat map wrapper and tests while preserving existing
desktop `PR-0298` fixed-seat behavior and backend fixed-seat rules.
