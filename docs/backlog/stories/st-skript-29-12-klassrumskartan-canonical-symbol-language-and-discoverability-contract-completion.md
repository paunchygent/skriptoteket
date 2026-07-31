---
type: story
id: ST-SKRIPT-29-12
title: Klassrumskartan — Canonical symbol language and discoverability contract completion
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-29
acceptance_criteria:
- Given the project must choose symbols deliberately rather than screen-by-screen,
  when this story starts implementation, then a complete visual index exists for current
  shared icon wrappers, current direct Lucide usage, and all locally available Lucide
  symbols.
- Given symbols can drift when the same icon represents unrelated concepts, when this
  story completes, then every repeated global action, Klassrumskartan domain concept,
  and approved site-specific semantic slot has one documented icon assignment or a
  documented deferred decision.
- Given repeated operations render across planner, editor, and adjacent tool-grade
  SPA surfaces, when this story ships, then undo, redo, history, configure context,
  create, close, export/download, zoom, fit view, and overflow use one canonical symbol-and-label
  language without unicode or surface-local alternates.
- Given icon-only and icon-led controls remain part of the dense-control system, when
  this story is complete, then accessible names, visible labels, hover aids, and nearby
  discoverability cues follow one documented contract across the shared control family.
- Given configure-context destinations differ by surface such as `Regler` or `Inställningar`,
  when the final symbol language is applied, then those controls are disambiguated
  through the canonical label/icon contract rather than collapsing to ambiguous bare
  icons.
- Given the repo still relies mainly on browser-native `title` discoverability, when
  this story defines the symbol/language baseline, then `ST-29-08` can later upgrade
  that baseline into a custom tooltip system without reopening the canonical operation
  vocabulary.
retired_ids:
- ST-29-12
---

## Context

### Source: Context

The first shared dense-tool primitive pass shipped enough canonical symbol work to support the
current planner. What remains is the broader completion pass that turns those assets into one
stable site/app-wide language instead of a planner-led foundation with some remaining drift.

The next pass must start from a complete visual inventory instead of isolated icon searches. It
must compare the current shared wrapper registry, current direct Lucide imports, and the full local
Lucide symbol inventory before decisions are made. This is especially important for concepts that
have drifted, such as `Link2` representing both actual share links and relationship/proximity
rules.

This story isolates the symbol, labeling, and discoverability completion work from the already
shipped workspace layout stories.

## Epic Contract Slice

The source does not provide a separate epic contract slice section; no additional epic contract slice is recorded.

## ADR Coverage

The source does not provide a separate adr coverage section; no additional adr coverage is recorded.

## Contract Inputs

### Source: References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Primitive foundation: [ST-29-01](story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- Primitive tightening prerequisite: [ST-29-11](story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Tooltip enhancement follow-on: [ST-29-08](story-29-08-klassrumskartan-shared-custom-tooltip-system-and-global-hover-contract.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
- Symbol inventory contract: [REF-symbol-semantics-inventory-and-decision-contract-2026-05-04](../../reference/ref-symbol-semantics-inventory-and-decision-contract-2026-05-04.md)
- Symbol inventory mockup bundle: [MOCK-st-29-12-symbol-inventory](../../mockups/st-29-12-symbol-inventory/README.md)

## Live Verification Plan

The source does not provide a separate live verification plan section; no additional live verification plan is recorded.

## Non-Goals

The source does not provide a separate non-goals section; no additional non-goals is recorded.

## Notes

### Source: Notes

- This is a follow-on definition and audit story, not a new workspace redesign.
- The visual inventory and decision matrix are prerequisites for runtime icon swaps.
- The first implementation goal is to finish the operation vocabulary itself. The later custom
  tooltip system remains a separate enhancement story under `ST-29-08`.
- The story should cover both accessibility truthfulness and teacher-facing discoverability, not
  just icon swaps in isolation.

### Source: PR Tasks

- [x] [PR-0291: Symbol inventory and visual index artifact](../prs/pr-0291-st-29-12-symbol-inventory-and-visual-index-artifact.md)
- [x] [PR-0292: Semantic symbol decision matrix](../prs/pr-0292-st-29-12-semantic-symbol-decision-matrix.md)
- [x] [PR-0293: Klassrumskartan symbol implementation](../prs/pr-0293-st-29-12-klassrumskartan-symbol-implementation.md)
- [PR-0294: Shared site symbol rollout and guardrails](../prs/pr-0294-st-29-12-shared-site-symbol-rollout-and-guardrails.md)

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Story Closeout Review

The source does not provide a separate story closeout review section; no additional story closeout review is recorded.
