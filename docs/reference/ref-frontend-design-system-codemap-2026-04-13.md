---
type: reference
id: REF-frontend-design-system-codemap-2026-04-13
title: "Frontend design-system codemap (trace-based for cross-repo alignment)"
status: active
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
topic: "frontend design system"
links:
  - "ADR-0017"
  - "ADR-0027"
  - "ADR-0029"
  - "ADR-0030"
  - "ADR-0032"
  - "ADR-0037"
  - "ADR-0077"
  - "ST-29-01"
  - "ST-30-01"
  - "REF-frontend-transition-continuity-v1"
  - "REF-shared-tool-control-language-v1"
  - "REF-klassrumskartan-workspace-ui-doctrine-2026-03-28"
  - "REF-tool-editor-framework-codemap"
---

## Purpose

This codemap maps the **Skriptoteket design system as a reusable pipeline** that other integrated repos can adopt for cohesive UI language. Use it when you need to:

- Understand the complete flow from HuleEdu tokens to application UI
- Replicate the design system in another repo
- Verify alignment between integrated repos
- Identify where to inject customizations without breaking the contract

## Cross-Repo Adoption Strategy

To adopt this design system in another repo:

1. **Copy the token pipeline** (Trace 1): Backend static CSS → Tailwind theme bridge
2. **Adopt the styling entry** (Trace 2): Single CSS entry point with Tailwind + tokens
3. **Import shared primitives** (Trace 3): Copy `denseToolPrimitives.ts` and dense UI components
4. **Follow governance** (Trace 6): ADRs and rules define the design principles

## Trace Map

```text
Trace 1: Token Pipeline (Backend → Frontend Bridge)
  ↓
Trace 2: SPA Styling Entry (Boot Sequence)
  ↓
Trace 3: Dense Tool Primitives (Class Builders → Components)
  ↓
Trace 4: Toast System (CSS Primitives → App Mount)
  ↓
Trace 5: Segmented Toggle (Shell Classes → Workspace Usage)
  ↓
Trace 6: Design System Governance (ADRs → Rules → Reference)
```

---

## Trace 1: Token Pipeline (Backend Static CSS → Frontend Theme Bridge)

**Purpose**: Establish the canonical source of design tokens and bridge them to Tailwind utilities.

### Trace 1 Flow Diagram

```text
Backend Static Assets
  └── huleedu-design-tokens.css [1a]
      ├── Color tokens (canvas, navy, burgundy) [1b]
      └── Shadow tokens (brutalist) [1c]

Frontend Import Layer
  └── tokens.css [1d]
      └── @import backend tokens via relative path

Tailwind 4 Theme Bridge
  └── tailwind-theme.css [1e]
      ├── @theme inline block
      ├── --color-canvas mapping [1f]
      └── --shadow-brutal mapping [1g]
          └── Generates Tailwind utilities
              ├── bg-canvas, text-navy
              └── shadow-brutal, shadow-brutal-sm
```

### Trace 1 Location Map

| ID   | Description                | Path                                                               |
|------|----------------------------|--------------------------------------------------------------------|
| 1a   | Canonical token source     | `src/skriptoteket/web/static/css/huleedu-design-tokens.css:22`     |
| 1b   | Core brand colors          | `src/skriptoteket/web/static/css/huleedu-design-tokens.css:20-24` |
| 1c   | Brutalist shadow tokens    | `src/skriptoteket/web/static/css/huleedu-design-tokens.css:130-134` |
| 1d   | Frontend import wrapper    | `frontend/apps/skriptoteket/src/styles/tokens.css:1`               |
| 1e   | Tailwind theme bridge      | `frontend/apps/skriptoteket/src/styles/tailwind-theme.css:1`        |
| 1f   | Color mapping              | `frontend/apps/skriptoteket/src/styles/tailwind-theme.css:8-10`    |
| 1g   | Shadow utility mapping     | `frontend/apps/skriptoteket/src/styles/tailwind-theme.css:16-20`   |

### Trace 1 Adoption Steps

1. **Copy `huleedu-design-tokens.css`** from Skriptoteket backend to your repo's static assets

2. **Create `tokens.css`** that imports the backend file

3. **Create `tailwind-theme.css`** with `@theme inline` block mapping tokens to Tailwind vars

4. **Never modify `huleedu-design-tokens.css` directly** - it's the shared source of truth

---

## Trace 2: SPA Styling Entry (main.ts → main.css Assembly)

**Purpose**: Define the single CSS entry point that loads the complete styling stack at boot time.

### Trace 2 Flow Diagram

```text
main.ts application entry [2a]
  └── imports main.css [2b]
      ├── @import "tailwindcss" [2c]
      ├── @import "../styles/tokens.css" [2d]
      │   └── (loads huleedu-design-tokens.css) [2e]
      ├── @import "../styles/tailwind-theme.css" [2f]
      │   └── (@theme inline mappings) [2g]
      └── @layer components [2h]
          ├── .btn-primary definition [2i]
          │   ├── base styles (navy bg, border) [2j]
          │   ├── hover (burgundy fill) [2k]
          │   └── active press behavior [2l]
          ├── .btn-cta definition [2m]
          ├── .btn-ghost definition [2n]
          ├── .toast-* primitives [2o]
          ├── .planner-* workspace classes [2p]
          └── page transition styles [2q]
```

### Trace 2 Location Map

| ID   | Description                  | Path                                                              |
|------|------------------------------|-------------------------------------------------------------------|
| 2a   | SPA boot imports main.css    | `frontend/apps/skriptoteket/src/main.ts:4`                       |
| 2b   | Main CSS entry               | `frontend/apps/skriptoteket/src/assets/main.css:1`                |
| 2c   | Tailwind 4 import            | `frontend/apps/skriptoteket/src/assets/main.css:1`                |
| 2d   | Token import                 | `frontend/apps/skriptoteket/src/assets/main.css:3`                |
| 2e   | Token file loads backend CSS | `frontend/apps/skriptoteket/src/styles/tokens.css:1`              |
| 2f   | Theme bridge import          | `frontend/apps/skriptoteket/src/assets/main.css:4`                |
| 2g   | @theme inline block          | `frontend/apps/skriptoteket/src/styles/tailwind-theme.css:1`       |
| 2h   | Component layer              | `frontend/apps/skriptoteket/src/assets/main.css:46`               |
| 2i   | Button primitive definition  | `frontend/apps/skriptoteket/src/assets/main.css:88`               |
| 2j   | Base button styles           | `frontend/apps/skriptoteket/src/assets/main.css:93`               |
| 2k   | Hover behavior               | `frontend/apps/skriptoteket/src/assets/main.css:625`              |
| 2l   | Physical press behavior      | `frontend/apps/skriptoteket/src/assets/main.css:94`               |
| 2m   | CTA button                   | `frontend/apps/skriptoteket/src/assets/main.css:98`               |
| 2n   | Ghost button                 | `frontend/apps/skriptoteket/src/assets/main.css:108`              |
| 2o   | Toast primitives             | `frontend/apps/skriptoteket/src/assets/main.css:371`              |
| 2p   | Planner workspace classes    | `frontend/apps/skriptoteket/src/assets/main.css:729`              |
| 2q   | Page transitions             | `frontend/apps/skriptoteket/src/assets/main.css:886`              |

### Trace 2 Adoption Steps

1. **Create a single CSS entry point** (e.g., `main.css`) in your app

2. **Import Tailwind first**, then tokens, then theme bridge

3. **Define shared button primitives** in the `@layer components` block

4. **Keep the entry point minimal** - don't sprinkle extra Tailwind imports elsewhere

---

## Trace 3: Dense Tool Primitive (Class Builder → Component → Usage)

**Purpose**: Define the shared primitive class builders and components for dense toolbar controls.

### Trace 3 Flow Diagram

```text
Primitive Class Builder (denseToolPrimitives.ts)
  ├── DENSE_ACTION_RADIUS_CLASS constant [3a]
  └── denseActionButtonClass() function [3b]
      └── Returns computed Tailwind classes [3c]

Base Action Button Component
  └── UiDenseActionButton.vue
      ├── buttonClass computed property [3d]
      │   └── Calls denseActionButtonClass() [3e]
      └── <button> template with dynamic class [3f]

Icon Button Wrapper Component
  └── UiDenseIconButton.vue
      ├── <UiDenseActionButton> usage [3g]
      └── icon-only prop [3h]

Shared UI Export Surface
  └── index.ts [3i]
      └── Exports primitives for consumption
```

### Trace 3 Location Map

| ID   | Description                  | Path                                                               |
|------|------------------------------|--------------------------------------------------------------------|
| 3a   | Hard small radius constant   | `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts:37` |
| 3b   | Class builder function       | `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts:108` |
| 3c   | Returns Tailwind classes     | `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts:125` |
| 3d   | Component calls class builder | `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue:57` |
| 3e   | Calls denseActionButtonClass | `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue:55` |
| 3f   | Dynamic class binding        | `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue:91` |
| 3g   | Icon button wrapper          | `frontend/apps/skriptoteket/src/components/ui/UiDenseIconButton.vue:55` |
| 3h   | Icon-only mode               | `frontend/apps/skriptoteket/src/components/ui/UiDenseIconButton.vue:63` |
| 3i   | Primitive export surface     | `frontend/apps/skriptoteket/src/components/ui/index.ts:11` |

### Trace 3 Adoption Steps

1. **Copy `denseToolPrimitives.ts`** to your repo's UI components directory

2. **Copy the dense UI components**: `UiDenseActionButton.vue`, `UiDenseIconButton.vue`, etc.

3. **Create a shared UI index** that exports all primitives

4. **Use the class builders** in your toolbar and control surfaces

5. **Respect the frozen constants** (e.g., `DENSE_ACTION_RADIUS_CLASS = "rounded-[4px]"`)

---

## Trace 4: Toast System (Primitive Classes → Component → App Mount)

**Purpose**: Define the toast notification flow from CSS primitives through component to app-level mounting.

### Trace 4 Flow Diagram

```text
Application Boot
  └── main.ts imports main.css [4e]
      └── App.vue root component [4f]
          └── <ToastHost /> mounted globally [4g]

CSS Primitive Layer (main.css)
  ├── .toast-container positioning [4a]
  ├── .toast base styles [4b]
  └── .toast-info / success / warning [4c]
      └── 90% opacity backgrounds [4d]

Toast Component (ToastHost.vue) [4h]
  ├── <Teleport to="body"> [4i]
  ├── <TransitionGroup name="toast"> [4j]
  │   └── v-for toast loop [4k]
  │       ├── :class binding [4l]
  │       │   └── applies variant classes
  │       ├── Icon (Check/Warning/X/Info) [4m]
  │       └── Close button [4n]
  └── useToast() composable [4o]
      └── toast.toasts reactive array [4p]
```

### Trace 4 Location Map

| ID   | Description                  | Path                                                               |
|------|------------------------------|--------------------------------------------------------------------|
| 4a   | Toast container positioning  | `frontend/apps/skriptoteket/src/assets/main.css:345`              |
| 4b   | Toast base styles            | `frontend/apps/skriptoteket/src/assets/main.css:371`              |
| 4c   | Toast variant classes        | `frontend/apps/skriptoteket/src/assets/main.css:398`              |
| 4d   | 90% opacity backgrounds       | `frontend/apps/skriptoteket/src/assets/main.css:399`              |
| 4e   | SPA boot imports main.css    | `frontend/apps/skriptoteket/src/main.ts:4`                       |
| 4f   | Root component                | `frontend/apps/skriptoteket/src/App.vue:1`                        |
| 4g   | App-level toast mount        | `frontend/apps/skriptoteket/src/App.vue:214`                      |
| 4h   | Toast component              | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:1`    |
| 4i   | Teleport to body             | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:28`   |
| 4j   | TransitionGroup              | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:30`   |
| 4k   | Toast rendering loop         | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:35`   |
| 4l   | Dynamic variant binding      | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:39`   |
| 4m   | Icon rendering               | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:47`   |
| 4n   | Close button                 | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:70`   |
| 4o   | Toast composable             | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:6`    |
| 4p   | Reactive toasts array        | `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue:36`   |

### Trace 4 Adoption Steps

1. **Copy toast CSS primitives** from `main.css` to your entry CSS

2. **Copy `ToastHost.vue`** component to your UI components

3. **Mount `<ToastHost />`** in your root App component

4. **Use the `useToast()` composable** for programmatic toast notifications

---

## Trace 5: Segmented Toggle (Shell Classes → Component → Workspace Usage)

**Purpose**: Define the segmented toggle primitive for mode switchers in planner/editor workspaces.

### Trace 5 Flow Diagram

```text
Dense Tool Primitives Module
  └── DENSE_SEGMENTED_SHELL_CLASS export [5a]

UiSegmentedToggle Component
  ├── shellClass computed property [5b]
  ├── Template rendering [5c]
  │   ├── Animated navy slider [5d]
  │   └── Radio button options [5e]
  │       └── aria-checked binding [5f]
  └── Keyboard navigation (arrows/home/end) [5g]

Workspace Integration
  └── Planner workspace shell CSS [5h]
      ├── Mode selector (Översikt/Gruppering/etc) [5i]
      ├── Toolbar action bar [5j]
      └── Canvas/pool layout primitives [5k]
```

### Trace 5 Location Map

| ID   | Description                  | Path                                                               |
|------|------------------------------|--------------------------------------------------------------------|
| 5a   | Segmented shell constant      | `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts:38` |
| 5b   | Shell class selection        | `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue:98` |
| 5c   | Template rendering           | `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue:348` |
| 5d   | Animated slider background   | `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue:360` |
| 5e   | Radio button options         | `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue:371` |
| 5f   | aria-checked binding         | `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue:376` |
| 5g   | Keyboard navigation         | `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue:242` |
| 5h   | Workspace shell primitive    | `frontend/apps/skriptoteket/src/assets/main.css:729`              |
| 5i   | Mode selector                | `PlannerWorkspaceShell.vue`                                      |
| 5j   | Toolbar action bar           | `frontend/apps/skriptoteket/src/assets/main.css:743`              |
| 5k   | Canvas/pool layout           | `frontend/apps/skriptoteket/src/assets/main.css:771`              |

### Trace 5 Adoption Steps

1. **Copy `DENSE_SEGMENTED_SHELL_CLASS`** from `denseToolPrimitives.ts`

2. **Copy `UiSegmentedToggle.vue`** component to your UI components

3. **Use the segmented toggle** for mode switchers in your workspaces

4. **Respect the keyboard navigation** and ARIA semantics

---

## Trace 6: Design System Governance (ADRs → Rules → Reference Codemap)

**Purpose**: Define the decision records and rules that govern the design system's principles and implementation contracts.

### Trace 6 Flow Diagram

```text
Architecture Decision Records (ADRs)
  ├── ADR-0017: HuleEdu Adoption [6a]
  │   └── Mandates HuleEdu tokens [6b]
  └── ADR-0032: Tailwind 4 @theme [6c]
      └── CSS-first token bridge [6d]

Agent Implementation Rules
  └── 045-huleedu-design-system.md [6e]
      ├── Brutalist Academic principles [6f]
      └── Physical feedback rules [6g]
          └── 4px press, shadow removal [6h]

Reference Documentation
  ├── Frontend Design System Codemap [6i]
  │   └── Token pipeline mapping [6j]
  └── PR-0157: Dense Tool Primitives [6k]
      └── Shared primitive spec [6l]
```

### Trace 6 Location Map

| ID   | Description                  | Path                                                                               |
|------|------------------------------|------------------------------------------------------------------------------------|
| 6a   | HuleEdu adoption decision   | `docs/adr/adr-0017-huleedu-design-system-adoption.md:24`                          |
| 6b   | Mandates HuleEdu tokens      | `docs/adr/adr-0017-huleedu-design-system-adoption.md:15`                          |
| 6c   | Tailwind 4 @theme decision   | `docs/adr/adr-0032-tailwind-4-theme-tokens.md:33`                                 |
| 6d   | CSS-first token bridge       | `docs/adr/adr-0032-tailwind-4-theme-tokens.md:23`                                 |
| 6e   | Design system rules          | `.codex/rules/045-huleedu-design-system.md:14`                                   |
| 6f   | Design system principles     | `.codex/rules/045-huleedu-design-system.md:16`                                   |
| 6g   | Physical feedback rule       | `.codex/rules/045-huleedu-design-system.md:23`                                   |
| 6h   | 4px press behavior           | `.codex/rules/045-huleedu-design-system.md:25`                                   |
| 6i   | Design system codemap        | `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md:119`             |
| 6j   | Token pipeline mapping       | `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md:120`             |
| 6k   | Dense primitive implementation | `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md:34` |
| 6l   | Shared primitive spec        | `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md:38` |

### Trace 6 Adoption Steps

1. **Read ADR-0017** to understand HuleEdu design system adoption

2. **Read ADR-0032** to understand Tailwind 4 @theme bridge approach

3. **Follow rule 045** for Brutalist Academic design principles

4. **Reference the codemap** for implementation details

5. **Adhere to the frozen primitive contracts** from PR-0157

---

## Design Principles Summary

From rule 045, the core principles that must be preserved across repos:

### Physicality (Elevation & Feedback)

- **Lift on Hover**: `-2px` translation with increased hard shadow

- **Press on Active**: `1px` translation with shadow removal

- **Never use blurred shadows**: Always use "Brutal" (hard) shadows

- **Dense workspace exception**: Toolbars and controls should not all "perform" physical lift

### Stationarity (Natural Reflow)

- Use **Natural Grid Reflow** to prevent layout shifts

- Set content column to `1fr` and action column to fixed/measured widths

### Academic Typography (The Rule of 40rem)

- Content columns must be capped at `max-w-[40rem]` (~640px)

- Exception: Dense operational surfaces can be more compact

### Structure Before Labels

- Build hierarchy first with headings, spacing, section rules

- Use small labels only when they solve real ambiguity

- Avoid stacking multiple eyebrow labels

### Operational Density

- One live task surface must dominate the layout

- Use compact action rows instead of full-width panels

- Desktop-first composition for workspace-heavy apps

---

## Token Reference

### Core Brand Colors

| Token                  | Tailwind Class              | Hex     | Usage                              |
|------------------------|----------------------------|---------|------------------------------------|
| `--huleedu-canvas`     | `bg-canvas`, `text-canvas`  | #FAFAF6 | Background, button text on dark   |
| `--huleedu-navy`       | `bg-navy`, `text-navy`, `border-navy` | #1C2E4A | Primary text, borders, functional buttons |
| `--huleedu-burgundy`   | `bg-burgundy`, `text-burgundy` | #4D1521 | CTA accent, errors, publish actions |

### Feedback Colors

| Token                  | Tailwind Class              | Hex     | Usage                              |
|------------------------|----------------------------|---------|------------------------------------|
| `--huleedu-success`    | `text-success`, `border-success` | #059669 | Success states                    |
| `--huleedu-warning`    | `text-warning`, `bg-warning/20` | #D97706 | Attention, pending review          |
| `--huleedu-error`      | `text-error`               | #DC2626 | Error states                      |

### Shadows (Brutalist)

| Token                  | Tailwind Class              | Offset   | Usage               |
|------------------------|----------------------------|----------|---------------------|
| `--huleedu-shadow-brutal` | `shadow-brutal`           | 6px 6px  | Standard elevation  |
| `--huleedu-shadow-brutal-sm` | `shadow-brutal-sm`       | 4px 4px  | Small elevation     |
| `--huleedu-shadow-brutal-xs` | `shadow-brutal-xs`       | 2px 2px  | Minimal elevation   |

---

## Frozen Primitive Constants

These constants must be preserved across all repos for consistency:

```typescript
// Corner radius for dense controls (blocky, not soft)
DENSE_ACTION_RADIUS_CLASS = "rounded-[4px]"

// Dense control size tiers
dense_icon = 36px // h-9 w-9
dense_text = 28px // h-[28px]
compact_segment = 24px // For segmented/toggle internals

// Physical feedback
press_translation = 1px // Active state
hover_lift = -2px // Hover state
```

---

## Verification Checklist

When adopting this design system in another repo, verify:

- [ ] Token pipeline: Backend CSS → Tailwind theme bridge is complete
- [ ] Single CSS entry point imports Tailwind, tokens, then theme bridge
- [ ] Dense tool primitives are copied from `denseToolPrimitives.ts`
- [ ] Shared UI components use the class builders
- [ ] Toast system is mounted at app root
- [ ] Segmented toggles use the shell constants
- [ ] ADR-0017 and ADR-0032 are followed
- [ ] Rule 045 design principles are respected
- [ ] Frozen constants (radius, sizes, press behavior) are preserved
- [ ] No Tailwind default palette/spacing leaks into product UI
- [ ] Only mapped token utilities are used (bg-canvas, text-navy, etc.)

---

## Related Files

### Token Pipeline

- `src/skriptoteket/web/static/css/huleedu-design-tokens.css`

- `frontend/apps/skriptoteket/src/styles/tokens.css`

- `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`

- `frontend/apps/skriptoteket/src/assets/main.css`

### Shared Primitives

- `frontend/apps/skriptoteket/src/components/ui/denseToolPrimitives.ts`

- `frontend/apps/skriptoteket/src/components/ui/UiDenseActionButton.vue`

- `frontend/apps/skriptoteket/src/components/ui/UiDenseIconButton.vue`

- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`

- `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue`

- `frontend/apps/skriptoteket/src/components/ui/index.ts`

### Governance

- `docs/adr/adr-0017-huleedu-design-system-adoption.md`

- `docs/adr/adr-0032-tailwind-4-theme-tokens.md`

- `.codex/rules/045-huleedu-design-system.md`

### Reference

- `docs/reference/ref-frontend-design-system-codemap-2026-03-28.md` (file-list based)

- `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
