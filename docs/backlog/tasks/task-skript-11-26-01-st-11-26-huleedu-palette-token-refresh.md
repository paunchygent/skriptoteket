---
type: task
id: TASK-SKRIPT-11-26-01
title: ST-11-26 HuleEdu palette token refresh
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
story: ST-SKRIPT-11-26
task_kind: story
acceptance_criteria:
- Shared CSS tokens define the HuleEdu working palette and semantic aliases for brand,
  text, borders, action, buttons, and light canvas surfaces.
- The Tailwind 4 theme bridge exposes paper, terracotta, action, and critical utilities
  without removing legacy burgundy compatibility.
- Shared button, focus, selected-state, and link primitives use the Verdigris action
  channel where they are functional UI, not warning/destructive UI.
- Shared destructive primitives use critical/error-family tokens, while transient
  failure toasts use terracotta because they are not critical blocking states.
- Shared dense buttons, rails, toggles, segmented controls, and share/export action
  buttons use the action channel for active/selected/primary control states instead
  of structural navy.
- Filled selected selectors keep light selected text for nested labels and disabled
  selected states; navy text must not sit on Verdigris fill.
- Canvas is treated as the unified base surface; broad white-on-canvas panel stacks
  are avoided in favor of translucent panel surfaces and light row/object highlights.
- Modal, dialog, popover, drawer, and sheet shells use an opaque canvas-toned modal
  token instead of translucent panel tokens, while form fields and deliberate object
  previews may remain white.
- Secondary share/link actions use Verdigris outline/text hierarchy and link symbols,
  while filled Verdigris is reserved for true primary CTA or selected/active state.
- Design-system docs/rules document the palette split and deprecate new usage of generic
  burgundy for functional action roles.
---

## Context


The previous token set used `burgundy` for too many unrelated meanings: brand
warmth, primary CTA, selected states, focus, and destructive/critical actions.
That makes the UI harder to reason about and causes visual drift when components
try to become more product-oriented.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Story Contract Slice


Introduce the agreed HuleEdu working palette as shared tokens and wire the first
semantic pass through the SPA bridge and shared primitives:

- Deep Navy for structure and long text.
- Warm Terracotta for brand accent and transient failure toasts.
- Verdigris Teal for functional action, selection, focus, and calm positive state.
- Light canvas/paper for the shared warm surface.
- Translucent canvas-toned panel surfaces as the default page/panel base, with opaque canvas-toned modal shells over overlays and white reserved for fields and deliberate object contrast.
- Amber/ochra for warning.
- Burgundy/error-family for destructive and truly critical decisions.

## Contract Inputs

No separate contract inputs is stated in the source.

## Plan


1. Update the canonical token CSS with palette tokens, semantic aliases, opacity
   variants, and compatibility aliases.
2. Update the Tailwind 4 `@theme inline` bridge with `paper`, `terracotta`,
   `action`, and `critical` utilities.
3. Update shared primitives in `main.css` and dense control components so primary
   buttons, focus rings, selected states, toggles, rails, and links use `action`,
   destructive primitives use `critical`, and transient failure toasts use
   terracotta.
4. Update SPA, renderer, and email/template surfaces that still used old burgundy
   action styling or stale navy literals.
5. Replace high-visibility white-on-canvas dashboard/planner panels with
   canvas-toned surfaces, while keeping white only for deliberate object/editor
   contrast.
6. Add a dedicated opaque modal shell token and move overlay-backed modal,
   dialog, popover, drawer, and sheet chrome off translucent panel surfaces.
7. Update the governing design-system docs so future work does not reintroduce
   terracotta/teal warning semantics.

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


- `pdm run docs-validate`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `git diff --check`

## Validation

No separate validation is stated in the source.

## Stop Conditions


Revert the token, bridge, primitive, and documentation changes together. Because
legacy `burgundy` compatibility remains, rollback is limited to the token refresh
and does not require route or API changes.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Non-goals


- Removing the deprecated `burgundy` compatibility alias or rewriting historical docs/mockups.
- Redesigning individual Klassrumskartan screens or editor layouts.
- Changing warning or destructive semantics to terracotta or teal.
- Promoting the token package into a cross-repo HuleEdu package.

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Implementation Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
