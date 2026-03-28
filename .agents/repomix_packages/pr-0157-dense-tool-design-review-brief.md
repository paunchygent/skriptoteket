# PR-0157 Dense-Tool Design Review Brief

## Purpose

This package is for a frontend designer reviewing the first shared dense-tool primitive
implementation lane for Skriptoteket.

The goal is not to redesign the whole product at once. The goal is to review the primitive layer
that will later be consumed by Klassrumskartan and the tool editor.

## Governing backlog items

- `ST-29-01`
- `PR-0156`
- `PR-0157`
- `PR-0158`

## What PR-0157 is responsible for

`PR-0157` is the shared primitive implementation slice.

It should define:

1. The canonical symbol inventory for repeated dense-tool operations:
   - undo
   - redo
   - history
   - configure context
   - create
   - close
   - export/download
   - zoom in
   - zoom out
   - fit view
   - overflow

2. The canonical dense-tool primitive set:
   - icon button
   - icon-led button
   - split button
   - menu button
   - toggle
   - segmented mode switch

3. The shared interaction contract:
   - hover
   - focus
   - active/pressed
   - disabled
   - tooltip/title
   - accessible name / `aria-label`

4. The compound-control pattern that later slices will use:
   - labeled toggle + configure-context child
   - canonical example: `Smart` + open `Regler`

5. The migration boundary:
   - today, the primitives still live inside the SPA app
   - there is no shipped `frontend/packages/huleedu-ui` package yet
   - the review should help decide how disciplined the shared SPA primitive layer needs to be
     before later extraction

## Current implementation state

These de facto primitives already exist and will be extracted or formalized by PR-0157.

### De facto control primitives

| Component | Current location | Size | Key props | Status |
| --------- | --------------- | ---- | --------- | ------ |
| `PlannerToolbarIconButton` | `views/apps/components/` | 36px (`h-9 w-9`), `rounded-sm` | `label` (aria-label), `title`, `disabled` | Working icon button; needs extraction to `components/ui/` |
| `PlannerToolbarOverflowMenu` | `views/apps/components/` | 36px trigger | items `{ id, label, icon?, disabled?, tone?, onSelect }` | Working menu button with `role="menu"` semantics |
| `PlannerExportActionGroup` | `views/apps/components/` | compact navy + dropdown | `options[]`, `busy`, `disabled` | Working split button; navy primary + icon menu trigger, `border-white/15` separator |
| `PlannerWorkspaceActionBar` | `views/apps/components/` | flex row | `leading` slot + default | Toolbar container; overrides child padding via `[&_.btn-ghost]:px-3` |
| `ToggleSwitch` | `components/ui/` | 24×44px (`h-6 w-11`) | `modelValue`, `disabled` | Boolean `role="switch"` with `aria-checked`; success/green active state |
| `UiSegmentedToggle` | `components/ui/` | 28px default / 24px compact | `density`, `options[]`, `ariaLabel`, `columns` | Multi-option group with `ResizeObserver` slider; `aria-pressed` per option |

### Icon inventory

20 icons exported from `components/icons/index.ts`. All wrap `lucide-vue-next` with
`stroke-width="2.5"` and `aria-hidden="true"` (accessibility is delegated to parent controls).
Default `size=24`.

**Present:** IconArrow, IconBan, IconBookmark, IconCheck, IconDownload, IconHelp, IconHistory,
IconInfo, IconLink2, IconMoreVertical, IconPresentation, IconRedo, IconSchool, IconSearch,
IconSettings, IconShuffle, IconTrash, IconUndo, IconWarning, IconX

**Missing for PR-0157 scope:** zoom in, zoom out, fit view, create/plus.
`IconSettings` may serve for `configure_context`; the review should confirm.

### What does not exist yet

- No shared icon button primitive in `components/ui/` (only planner-local)
- No icon-led button (icon + optional text label)
- No shared split button
- No shared menu button
- No compound toggle pattern (toggle + configure-context child)
- No `components/ui/index.ts` barrel export

## Planner-editor control comparison

This comparison supports design task 6 (planner/editor parity).

### Shared operations across both surfaces

| Operation | Planner implementation | Editor implementation |
| --------- | -------------------- | -------------------- |
| Undo | `PlannerToolbarIconButton` + `IconUndo` | Inline button with Unicode arrow `↶` |
| Redo | `PlannerToolbarIconButton` + `IconRedo` | Inline button with Unicode arrow `↷` |
| History | Overflow menu item → history drawer | AI applied/undone status with timestamp |
| Overflow | `PlannerToolbarOverflowMenu` (kebab) | No equivalent (actions inline) |

### Planner-specific controls

- Context selector (`<select>` for classroom)
- `Smart` toggle + configure-context child (checkbox + `IconSettings` icon button → routes to `Regler`)
- Randomize (`IconShuffle :size="16"` + `Slumpa` text, `btn-ghost`)
- Reset (ghost text button → confirmation dialog)
- New draft buttons (`Nytt sittschema`, `Nytt gruppschema`)
- Zoom control group (zoom in/out/fit/scale readout — not yet built)
- Rules tool rail (vertical button group with burgundy active state)

### Editor-specific controls

- Save/checkpoint nested dropdown (with inline change summary input)
- Tool switching menu (searchable, recent/my-tools sections)
- AI status tracking (applied/undone state, timestamp, AI undo/redo)
- Chat collapse toggle (mobile-only, `lg:hidden`)
- Lock badge (draft lock status, success/neutral tone)
- Mode selector (`UiSegmentedToggle` for editor panels)

### Inconsistencies to address before or during PR-0157

1. **Disabled opacity drift:**
   - Planner icon buttons: `disabled:text-navy/25`
   - Planner ghost buttons and overflow items: `disabled:text-navy/35`
   - Editor utility buttons: `disabled:text-navy/30`
   - PR-0157 should freeze one shared disabled opacity for each role tier.

2. **Icon rendering divergence:**
   - Planner uses canonical icon components at 14–18px with `stroke-width="2.5"`
   - Editor uses inline SVGs (`h-4 w-4`, `stroke-width="1.5"`) and Unicode arrows
   - PR-0157 should make the shared icons the only path for canonical operations.

3. **Button height tiers (unnamed):**
   - Planner toolbar icon buttons: `h-9` (36px)
   - Editor utility buttons: `h-[28px]` (28px, arbitrary value)
   - Segmented toggle compact: `h-[24px]` (24px)
   - PR-0157 should name these tiers or collapse to fewer.

## Design tasks for the reviewer

1. Review the role hierarchy for dense tools.
   - Are we clearly separating `primary_cta`, `secondary_action`, `toolbar_action`,
     `destructive_action`, and `overflow_action`?

2. Review the visual density target.
   - Do the proposed primitives support desktop-first tool work, rather than reverting to
     landing-page buttons or mobile-stacked controls?

3. Review symbol clarity.
   - Which operations are truly canonical enough for icon-first treatment?
   - Which operations should remain icon-led or text-visible?

4. Review the split-button pattern.
   - Export/download is the first canonical split-button case.
   - The pattern should feel compact, obvious, and stable enough to reuse elsewhere.

5. Review the compound toggle pattern.
   - `Smart` / `Regler` should not expand into a mini-toolbar workspace.
   - The control should stay compact while still exposing deeper tuning clearly.

6. Review planner/editor parity.
   - The same repeated operations should not drift between Klassrumskartan and the tool editor.
   - Differences should happen at composition level, not at primitive or symbol level.

7. Review the implementation-home decision.
   - Is the shared primitive layer coherent enough inside the SPA app for now?
   - What should remain app-local versus genuinely shared?

## Stack and libraries to use

The current frontend stack and primitive lane are:

- Vue `3.5.x`
- TypeScript `5.7.x`
- Vite `6.x`
- Pinia `3.x`
- Vue Router `4.6.x`
- Tailwind CSS `4.1.x`
- HuleEdu design tokens from `src/skriptoteket/web/static/css/huleedu-design-tokens.css`
- Tailwind `@theme inline` bridge in `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`
- Shared SPA CSS entrypoint in `frontend/apps/skriptoteket/src/assets/main.css`
- Local icon components in `frontend/apps/skriptoteket/src/components/icons/`
- Shared SPA primitives in `frontend/apps/skriptoteket/src/components/ui/`
- Vitest `4.x` for component/composable verification
- Playwright for live browser proof

Important implementation note:

- `lucide-vue-next` is installed, but the current canonical symbol lane is still local component
  icons under `src/components/icons/`.
- The review should assume symbol consistency is more important than swapping icon libraries.

## Sizing and token reference

### Button height tiers in use

| Tier | Tailwind class | Pixels | Where used |
| ---- | -------------- | ------ | ---------- |
| Toolbar icon button | `h-9 w-9` | 36px | `PlannerToolbarIconButton`, overflow trigger |
| Editor utility / segmented default | `h-[28px]` | 28px | `EditorWorkspaceToolbar`, `UiSegmentedToggle` default |
| Segmented compact | `h-[24px]` | 24px | `UiSegmentedToggle` compact density |
| Toggle switch | `h-6` | 24px | `ToggleSwitch` track height |

### Color semantics

| Token | Hex | Tailwind class | Primary use |
| ----- | --- | -------------- | ----------- |
| `--huleedu-navy` | `#1C2E4A` | `bg-navy`, `text-navy`, `border-navy` | Primary text, borders, functional buttons |
| `--huleedu-burgundy` | `#4D1521` | `bg-burgundy`, `text-burgundy` | CTA accent, errors, focus outlines, active states |
| `--huleedu-canvas` | `#FAFAF6` | `bg-canvas`, `text-canvas` | Background, button text on dark fills |
| `--huleedu-success` | `#059669` | `text-success` | Success states, active toggle |
| `--huleedu-warning` | `#D97706` | `text-warning` | Attention, pending review |
| `--huleedu-error` | `#DC2626` | `text-error` | Error states |

### Shadow tokens

The Tailwind `@theme` bridge shifts shadow names down one step:

| Tailwind class | Maps to CSS variable | Offset | Use |
| -------------- | -------------------- | ------ | --- |
| `shadow-brutal` | `--huleedu-shadow-brutal-sm` | 4px | Standard card/panel shadow |
| `shadow-brutal-sm` | `--huleedu-shadow-brutal-xs` | 2px | Compact toolbar/action bar shadow |

The underlying `--huleedu-shadow-brutal` (6px) is not directly mapped to a Tailwind class.
No blur. No rounded corners on buttons (brutalist aesthetic).

### Dense workspace hover rule

Toolbar icon buttons, segmented toggles, and inspector controls do NOT perform physical
lift (`-translate-y-0.5` + hard shadow) on hover. Reserve strong hover feedback for isolated
CTAs and deliberate object interactions. Toolbar hover is limited to `bg-canvas/60` or
equivalent subtle fill change.

## PNG references

These screenshots were captured from the live local app on `2026-03-28`.

- `.agents/repomix_packages/pr-0157-dense-tool-design-review-assets/classroom-seating-workspace.png`
- `.agents/repomix_packages/pr-0157-dense-tool-design-review-assets/classroom-rules-workspace.png`
- `.agents/repomix_packages/pr-0157-dense-tool-design-review-assets/tool-editor-workspace.png`

## Repomix package contents

The file `repomix-pr-0157-dense-tool-design-review.xml` contains the full source for every file
listed below. Use it as the primary code reference alongside the PNG screenshots.

### Governing docs

- `.agents/rules/045-huleedu-design-system.md`
- `docs/reference/ref-shared-tool-control-language-v1.md`
- `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md`
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- `docs/backlog/stories/story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md`
- `docs/backlog/prs/pr-0156-st-29-01-control-language-freeze-primitive-contract-and-fe-codemap.md`
- `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
- `docs/backlog/prs/pr-0158-st-29-01-seating-workspace-adoption-of-shared-dense-tool-primitives.md`

### Token pipeline

- `src/skriptoteket/web/static/css/huleedu-design-tokens.css` (canonical source)
- `frontend/apps/skriptoteket/src/styles/tokens.css` (SPA import wrapper)
- `frontend/apps/skriptoteket/src/styles/tailwind-theme.css` (`@theme inline` bridge)
- `frontend/apps/skriptoteket/src/assets/main.css` (SPA CSS entrypoint, button classes)

### Icon layer

- `frontend/apps/skriptoteket/src/components/icons/index.ts` (barrel, 20 exports)
- 9 icon `.vue` sources included: IconUndo, IconRedo, IconHistory, IconSettings, IconDownload,
  IconShuffle, IconMoreVertical, IconArrow, IconX

### Shared UI primitives

- `frontend/apps/skriptoteket/src/components/ui/ToggleSwitch.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`

### Planner controls (de facto primitives + consuming surfaces)

- `PlannerToolbarIconButton.vue`, `PlannerToolbarOverflowMenu.vue`
- `PlannerExportActionGroup.vue`, `PlannerWorkspaceActionBar.vue`
- `PlannerWorkspaceShell.vue`, `PlannerSeatingWorkspacePane.vue`
- `PlannerRulesWorkspacePane.vue`, `PlannerRulesToolRail.vue`

### Editor controls

- `ScriptEditorPageShell.vue`, `EditorWorkspacePanel.vue`
- `EditorWorkspaceToolbar.vue`, `EditorWorkspaceModeSelector.vue`
- `EditorToolMenu.vue`

### Build config

- `frontend/package.json`, `frontend/apps/skriptoteket/package.json`
- `frontend/apps/skriptoteket/vite.config.ts`

## Review order

1. `REF-frontend-design-system-codemap-2026-03-28`
2. `REF-shared-tool-control-language-v1`
3. `045-huleedu-design-system`
4. `PR-0157`
5. Planner/editor implementation files
6. PNG references

## Desired output from the reviewer

Please comment on:

- symbol decisions that should be changed before implementation
- primitive contracts that are still too vague
- planner/editor inconsistencies that must be normalized
- whether the current stack and file placement are sufficient for the first shared primitive slice
- what should be postponed from `PR-0157` into later workspace-specific slices

## Current ship gate

The current merge gate for `PR-0157` is:

- `configure_context` must be resolved without a bare ambiguous gear
- dense-action controls must stop inheriting page-button behavior as their base
- editor undo/redo must use the canonical shared icon components
- split/menu components must expose generic shared APIs rather than planner-shaped ones
