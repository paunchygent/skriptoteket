---
type: review
id: REV-SKRIPT-EPIC-40-CLOSEOUT
title: Shared design-system convergence
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: changes_requested
target: EPIC-SKRIPT-40
gate: closeout
reviewer: Independent Lead Architect (Pi)
decided_at: '2026-09-27T23:02:37+02:00'
---

## Governing Authority

REV-EPIC-40: independent, online pre-implementation plan review requested by
the parent for EPIC-SKRIPT-40 before implementation. Authority: repository
`AGENTS.md`, `agent-docs-governance/references/skriptoteket.md` (proposed epics
require review), its review-gates reference, and the accepted retained plan
D1-D18. This is the explicitly assigned repository epic review, not task
readiness, implementation approval, or capability verification. The parent
retains contract admission and lifecycle ownership.

The current package scaffolder requires the canonical identifier
`REV-SKRIPT-EPIC-40-CLOSEOUT` and `gate: closeout` for retained reviews.
`REV-EPIC-40` is the requested human-facing label; the requested filename is
preserved. These schema fields do not assert that this proposed epic is
implemented or eligible for terminal closeout. No backlog status is changed.

## Reviewed Scope

- Skriptoteket branch `codex/epic-skript-40`, revision
  `42a2351e918cb504719aac42e2ce90fc2ffe9405`: the epic, both stories, all four
  story tasks, and canceled TASK-SKRIPT-REP-0033.
- Current frontend component, message, toast, icon, CSS, dependency and
  validation seams in `frontend/apps/skriptoteket`; governance bootstrap test
  and PDM command bindings.
- Skill-repository revision `ccda9efd8a34688f870f9fc6de00222acc324efb`:
  TASK-SKILL-REP-0186/0187, the shared package, sync implementation and
  resource-package contract. This checkout was clean when inspected.
- Accepted retained plan at primary Skriptoteket checkout:
  `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md`.
  Review context: session `01a0e4a4-436a-70d9-a907-702d84f2a091`.
- Excluded: production edits, upstream repair, lifecycle changes, commits,
  deployment, and implementation verification.

## Evidence

The ledger is closed in the supplied retained plan: four accepted rounds,
D1-D18, an empty frontier, and user confirmation. The epic/story/task tables
mostly derive faithfully from those decisions. The two-story split, shared
ownership, palette adoption, unchanged toast store, package-first promotions,
and brand/auth exclusions are preserved. TASK-SKRIPT-40-01-01 carries forward
REP-0033's sync, token path, unused-export, validation and documentation
acceptance requirements. No additional walking-skeleton task is needed: the
accepted plan cites HuleEdu's existing boundary proof and makes the first
Skriptoteket sync the initial integrated delivery.

The declared upstream ordering is sensible: 0186 before token adoption,
01-01 before 01-02 before 01-03, then story 2 after story 1 and 0187. However,
its intermediate component slice is not dependency-complete (R1), and its
byte-for-byte target layout is contradictory (R2). These prevent the proposed
frontend gates from passing even if upstream fulfills its written contracts.

All references below are relative to the reviewed repositories. `package/`
means skill-repository `resources/frontend-design-system/huleedu-integrated/`.
`sync.py` means skill-repository
`packages/repository_governance/src/repository_governance/frontend_catalog/design_system.py`.

Runnable existing consumer checks are `pdm run fe-type-check`,
`pdm run fe-test`, and `pdm run fe-build` (`pyproject.toml:478-497`). The new
shared validator wrapper and bootstrap assertions are correctly assigned to
01-01. Upstream owns `pdm run design-resources-validate` and HuleEdu checks.
The Hemma staging walk is appropriate and remains required, using the routed
HuleEdu browser-session helpers/preflight. A generic successful test run or a
single happy-state toast/message does not cover R3/R4.

The action-button task covers all six named local classes, CSS import order,
and the source-contract test relocation. Its removal must include the shared
shell and later hover rules in `src/assets/main.css:47-54,639-688,774-784`,
not only the primary definitions. The existing test expects Tailwind source
strings, while the shared file uses CSS declarations; update its assertions
to the adopted contract rather than moving the old string checks unchanged.
No separate blocking finding is raised: this is within the task's explicit
removal and test-update scope.

## Findings

### R1 — High: Story 1 defers dependencies required by its own adopted components

**Location:** ST-SKRIPT-40-01, Slice Contract, line 32;
TASK-SKRIPT-40-01-02, Implementation Contract, lines 30-43;
TASK-SKRIPT-40-02-01, Implementation Contract, peer installation.

**Evidence and consequence:** `package/src/vue/components/ToastHost.vue:38-39`
imports `uiGlyphs` and `UiGlyph`. `package/src/vue/index.ts:17-26` exports both
glyph components and the glyph table. The glyph table imports `@lucide/vue`.
Story 1 explicitly leaves glyph exports null and installs the peer only in
story 2. Its adopted ToastHost/barrel therefore have unresolved dependencies.
In addition, 0186 promises a package `UiDenseSpinner.vue` exported from the
barrel, but 01-02's exhaustive adoption list omits this new component. The
current local spinner is a separate custom-icon implementation, not the
promised synced package component.

**Contract derivation:** accepted D10-D11/D15-D17 require a working shared
component slice, preserved busy behavior, then the semantic icon migration.

**Required change:** close the dependency set in the plan before 01-02:
adopt the released glyph runtime and install its catalog peer when ToastHost
and the barrel first need them; keep the broad call-site/meaning migration
and old Lucide removal in story 2. Explicitly include the released spinner
export, manifest entry and consumer target in 0186/01-02. Reconcile the story's
null-export term through planning ownership rather than silently overriding
it during implementation. If a different package interface is selected, it
must provide the same complete dependency closure without local forks.

**Proof:** Story 1 alone must pass typecheck/build, render a status toast and
busy action, and pass shared digest validation with no source import pointing
to an unadopted file or missing peer. Do not wait for 0187 to repair Story 1.

### R2 — High: Keeping the existing flat paths conflicts with unchanged package imports

**Location:** ST-SKRIPT-40-01 D4;
TASK-SKRIPT-40-01-02, Implementation Contract, lines 30-36.

**Evidence and consequence:** the current consumer has
`src/components/ui/UiDenseActionButton.vue` beside `denseToolPrimitives.ts`.
The package action button imports `../denseToolPrimitives`; the package barrel
imports `./components/UiDenseActionButton.vue` while importing primitives from
its own directory (`package/src/vue/index.ts:10-45`). Sync copies bytes without
rewriting imports (`sync.py`, `sync_design_system`). Replacing the flat local
files as instructed cannot preserve these relative relationships. Editing
synced imports afterward violates digest validation.

**Contract derivation:** accepted D4/D6/D11 require synced files, existing
consumer paths and working adopted components. The current plan makes those
requirements mutually incompatible.

**Required change:** have planning close and publish the exact physical export
map and local-barrel/import migration. A viable candidate is a package-shaped
subtree (`denseToolPrimitives.ts`, `uiGlyphs.ts`, package barrel at its root;
Vue SFCs under `components/`), with the existing local UI barrel re-exporting
that barrel and direct consumer imports migrated. That changes the literal
current-path decision and needs explicit reconciliation. An upstream
layout-compatible alternative is also valid. Do not prescribe a flat map
while relying on nonexistent import rewriting.

**Proof:** resolve every transitive relative import against the selected map;
run the actual typecheck/build and digest validator before accepting 01-02.

### R3 — High: SystemMessage migration leaves content and dismissal contracts undecided

**Location:** TASK-SKRIPT-40-01-02, Implementation Contract, lines 37-39;
TASK-SKILL-REP-0186, SystemMessage promotion, lines 37-38.

**Evidence and consequence:** local `SystemMessage.vue:8-46` has a nullable
string model that supplies fallback text, dismisses by emitting null, defaults
to dismissible, and announces errors assertively. For example,
`src/views/admin/AdminToolsView.vue:177-180` supplies only a model and variant,
with no slot. `src/components/editor/ChatDrawer.vue:138-167` likewise relies
on model text and update events. The package currently has slot-only content;
0186 promises optional v-model *visibility* and unchanged existing defaults.
Renaming variant/error alone does not establish whether strings are accepted,
where text comes from, how clear events work, or how dismissal remains present
when the package's new feature is inert by default. This risks blank feedback,
non-dismissible errors or broken typed models. ChatDrawer also imports the
old `SystemMessageVariant` type at line 10.

**Contract derivation:** accepted D12 and story acceptance require adoption
without losing existing message behavior, while retaining package tone/slots.

**Required change:** jointly close the released model type, hide/clear event,
dismiss default and text-slot contract with 0186. Specify consumer adaptation
for existing nullable-string models, slotless calls, explicit dismissal, typed
variant imports and `error` to `failure`. Preserve the needed failure
announcement behavior explicitly at the appropriate boundary. Do not depend
on unspecified upstream behavior or patch the synced component locally.

**Proof:** focused component/consumer tests must cover visible model text,
empty/null hiding, all tone mappings, default dismissal and null clearing,
existing clear-event handlers, and failure announcement semantics. Include a
real error and its dismissal in the staged message walk.

### R4 — Medium: Toast wrapper omits the package's ordering adaptation

**Location:** TASK-SKRIPT-40-01-02, Implementation Contract, lines 40-43,
and Validation, lines 59-61.

**Evidence and consequence:** `src/stores/toast.ts:59-65` removes the oldest
item at index zero and appends new items. Package ToastHost's explicit contract
(`package/src/vue/components/ToastHost.vue:12-18`) requires newest-first input.
Passing the unchanged store array directly reverses the package's intended
stack order. A single-toast walk cannot expose this mismatch. Variants and
maximum count already match; those do not need store redesign.

**Contract derivation:** accepted D10 requires a local adapter around the
unchanged store, rendering the shared ToastHost correctly.

**Required change:** specify that the wrapper derives newest-first props
without mutating the store array, retains dismissal by id and existing timers,
and chooses the intended placement through the package API. Keep this
adaptation in the consumer wrapper.

**Proof:** test at least three differently aged toasts, the fourth-toast
oldest eviction, manual dismissal and timer expiry; verify ordering in the
staged toast stack. These are tests of the existing contract, not new behavior.

### R5 — Medium: Glyph bundle guarantee is unsourced and rests on a false import assumption

**Location:** TASK-SKRIPT-40-02-01, Core Vertical And Performance, lines 45-47;
TASK-SKILL-REP-0187, corresponding performance paragraph.

**Evidence and consequence:** `package/src/vue/uiGlyphs.ts` eagerly constructs
`UI_GLYPHS` from all meaning tables; `UiGlyph.vue:15-32` selects from the table
using a runtime prop. Individual Lucide imports do not establish per-consumer
meaning tree-shaking. Growing the table can retain all mapped icons in the
shared runtime. The consumer contract nevertheless asserts per-meaning
imports and mandates no growth against existing usage without a baseline,
metric or comparison gate. The retained D1-D18 do not authorize this absolute
performance acceptance constraint.

**Contract derivation:** agent-planning requires derived accepted terms and
an evidence-based material-performance assessment; D14 accepts semantic
migration, not an unmeasured zero-byte-growth guarantee.

**Required change:** correct the import/tree-shaking claim in both plans.
Either remove the unsourced absolute requirement and record the actual bundle
risk, or return it to the owner for an accepted measurable budget with the
baseline, build mode, metric and proof command. Do not impose a package
architecture rewrite as a reviewer-created feature requirement.

**Proof:** retain comparable production-build bundle evidence before/after the
migration if the owner elects a performance acceptance limit. Ordinary build
success alone cannot prove that limit.

### R6 — Medium: Sync proof omits the clean-checkout checkpoints the command requires

**Location:** TASK-SKRIPT-40-01-01, Implementation Contract and Validation,
lines 29-48,65; second-sync validation in all later tasks.

**Evidence and consequence:** `sync.py`, `refuse_dirty_targets` and
`sync_design_system`, checks the map as well as every adopted target and
mirror file before writing. The package's Consumer Adoption reference
explicitly documents this. A newly created/edited map refuses the first sync;
the first successful sync dirties targets and normally prevents the immediate
second sync. Merely stopping on dirty targets does not define an executable
first-adoption or repeatability sequence.

**Contract derivation:** D4/D16 and the carried REP-0033 acceptance require a
real safe sync and the task explicitly requires a second unchanged sync.

**Required change:** add the parent-owned clean-map/bootstrap and post-sync
checkpoint sequence, including how the initially stale mirror/adoption map
passes or is handled by the new hook at that boundary. Prove repeatability
from the resulting clean committed state, or another approved clean proof
checkout. Keep dirty-target protection intact; do not stash, discard work,
hand-copy exports, or bypass validation as an implicit repair.

**Proof:** retain successful first sync, validate result, clean-state evidence
at the repeatability checkpoint, and successful no-diff second sync. This
review authorizes no commit by the reviewer.

## Decision

changes_requested

R1-R3 are high severity and R4-R6 are medium severity. The overall capability
and two-story decomposition remain sound, but the component adoption boundary
needs contract repair before this plan supports implementation. These findings
request changes through the owning planner; they do not overwrite accepted
user decisions or upstream reviewer-owned results.

## Permitted Next Step

The parent may reconcile the six findings with the accepted plan and owning
upstream tasks, then request bounded rereview of changed contracts/evidence.
Preserve the 0186 and 0187 release/HuleEdu gates and the canceled predecessor's
acceptance carry-forward. Do not treat this review as implementation approval,
epic closeout, or permission to remove dependency gates.

## Validation Not Run

No frontend tests, typecheck, build, design-resource validation, sync,
bootstrap test, HuleEdu checks or Hemma walk were run: this is pre-implementation
review, and the needed package promotions and consumer map are not present in
the inspected checkouts. No successful implementation proof is claimed.

`pdm run docs-validate` passed (exit 0), recorded in review session
`01a0e4a4-436a-70d9-a907-702d84f2a091`, capture
`0001-pdm-run-docs-validate`. `git diff --check` passed. The validator refreshed
`docs/backlog/INDEX.md` and `docs/repository-index.json` to index this single
new review; no other source document or production code was changed.

## Residual Risk

- The supplied assignment says 0186 is in progress and 0187 ready. Both files
  in the supplied primary skill-repository checkout still read `proposed` at
  the inspected revision. Work in another checkout may be ahead. Reconcile
  the exact merged release and HuleEdu proof before any consumer sync; the
  observed checkout does not establish either prerequisite completed.
- The local glyph exception is accepted. Clarify story 2's stop sentence as
  stopping on an *unclassified* mapping entry, not an entry explicitly marked
  local; otherwise it conflicts with its own acceptance criterion. The old
  Lucide dependency must still be absent, including retained local icons.
- The imported-file counts in the retained plan are discovery snapshots, not
  completion limits. Re-enumerate current icon and message uses at execution;
  cover all current direct imports, type imports and dynamic component uses.
- The root handoff predates EPIC-40 and describes unrelated work. It was read
  and left untouched under the assignment's single-review-file scope. Parent
  reconciliation remains necessary; no lifecycle action was taken here.
- `/Users/olofs_mba/core.md` and `runtime-AGENTS.md`, referenced by the home
  entrypoint, were absent. The supplied global Pi policy and canonical shared
  `resources/global-agent-policy/core.md` were available and read.
- The canonical retained review schema has only a closeout gate/identifier
  shape. This record explicitly limits itself to the assigned proposed-epic
  checkpoint; a future implementation review must use its own distinct
  canonical record rather than interpreting this artifact as terminal proof.
