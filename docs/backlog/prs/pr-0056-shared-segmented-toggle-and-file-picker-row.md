---
type: pr
id: PR-0056
title: "UI cohesion: shared segmented toggle + cohesive file picker row"
status: in_progress
owners: "agents"
created: 2026-01-25
updated: 2026-01-25
stories:
  - "ST-14-22"
tags: ["frontend"]
acceptance_criteria:
  - "A shared segmented toggle component replaces the editor mode selector and the file picker mode selector (Upload vs Saved) while keeping subtle rounding (no pill toggles)."
  - "The segmented toggle uses an animated navy fill that moves to the selected option; no per-button highlight/box-shadow is used for selection."
  - "The editor mode selector is always a single row (Källkod/Diff/Metadata/Testkör) with subtle segment separators so modes read as distinct surfaces."
  - "The file picker 'Choose files' affordance is integrated into the upload field row and does not use button-like box shadows or border highlights."
  - "The same file picker UI is used in both user tool runs and the editor sandbox run panel (no forked styling)."
  - "Keyboard + screen reader semantics remain correct (focus visible, disabled states, aria-pressed/aria-disabled)."
---

## Problem

We have multiple segmented-toggle-like UI surfaces (editor workspace mode selector, file picker source selector) that are
visually similar but implemented separately. This causes drift and makes the UI feel inconsistent.

Additionally, the file picker uses a button-like affordance inside a field row. For file selection, that “button”
presentation is visually too strong (shadow/border highlight) and breaks cohesion with the rest of the form UI.

## Goal

1) Introduce a shared segmented toggle component with an animated navy selection fill.

2) Use the shared component in:
- Editor workspace mode selector (Källkod/Diff/Metadata/Testkör)
- Tool run file picker mode selector (Ladda upp/Välj sparade)

3) Redesign the file picker upload action to be an integrated field-row control (no shadow, no border-highlight
button), applied consistently in both tool runs and the editor sandbox run panel.

## Non-goals

- ToolRunView layout refactor (handled in PR-0057).
- Browse catalog CTA removal (handled in PR-0057).
- Changing file picker behavior/contract (min/max, sources, validation) — visuals only.

## Decisions (LOCKED)

- **Subtle rounding is allowed** for segmented toggles (e.g. ~4px). No pill-shaped toggles.
- **Selection is expressed via a single animated navy fill** that moves between segments (no “active button” highlight
  treatment).
- **Editor mode selector is a single row** (no wrapping) so it aligns proportionally with the workflow button row above.
- **File selection affordance is not a button:** no box shadow and no border highlight around the “Välj filer” control.
  It must read as part of the input row.
- **One implementation shared across runtime + editor:** the same components and styles are used; no forked copies.

## Implementation plan

1) Add shared segmented toggle:
- New component: `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`
- API:
  - `modelValue: string`
  - `options: { value: string; label: string; disabled?: boolean; title?: string }[]`
  - emits `update:modelValue`
- Implementation details:
  - Container renders options as buttons with `aria-pressed`.
  - A single absolutely-positioned background element measures the active button rect and animates (prefers-reduced-motion respected).

2) Refactor editor mode selector to use the shared component:
- Update `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceModeSelector.vue` to be a small wrapper around
  `UiSegmentedToggle`.
- Preserve existing behavior:
  - `diff` is disabled only when not active and `canEnterDiff=false`.
  - `openCompareTitle` remains as tooltip/title on the diff option.
- Layout requirements:
  - Always render as a single row (4 segments).
  - Render full-width within the editor header right column to match the workflow button row width.

3) Update file picker to use the shared component for Upload vs Saved:
- Update `frontend/apps/skriptoteket/src/components/tool-run/ToolFileFieldPicker.vue`:
  - Replace the current two-button group with `UiSegmentedToggle` using values `upload` and `refs`.
  - Keep subtle rounding.

4) Replace the file picker “button” with an integrated row control:
- In upload mode in `ToolFileFieldPicker.vue`, replace the `btn-ghost`-styled label with:
  - A full-height label that behaves like inline text/link inside the field row (underline + hue change).
  - Disabled state: reduced opacity + no pointer events.

## Test plan

- Frontend unit tests: `pdm run fe-test`
- Frontend lint: `pdm run fe-lint`
- Manual (required):
  - Tool run page shows file picker with integrated chooser; mode toggle animates between Upload/Saved.
  - Editor workspace mode selector shows animated selection fill; diff disabled behavior is unchanged.
  - Note: manual verification is deferred until PR-0057 is fully implemented (per session instructions).

## Rollback plan

- Revert the PR-0056 commit(s).
- Restore `EditorWorkspaceModeSelector.vue` and `ToolFileFieldPicker.vue` to their previous local implementations.
