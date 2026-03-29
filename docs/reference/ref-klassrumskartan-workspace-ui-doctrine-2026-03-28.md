---
type: reference
id: REF-klassrumskartan-workspace-ui-doctrine-2026-03-28
title: "Klassrumskartan workspace UI doctrine (2026-03-28)"
status: active
owners: "agents"
created: 2026-03-28
updated: 2026-03-29
topic: "klassrumskartan-workspace-ui-doctrine"
links:
  [
    "PRD-group-seating-studio-v0.3",
    "REF-group-seating-studio-product-direction-2026-03-21",
    "PR-0155",
    "045-huleedu-design-system",
  ]
---

## Purpose

This note defines how Klassrumskartan should feel now that the planning logic is largely in place
and the remaining product risk is presentation quality rather than missing capability.

The goal is not "more design." The goal is a calmer, denser, more instrument-like workspace that
helps teachers stay oriented while switching between overview, grouping, seating, and rules.

## Product stance

- Klassrumskartan is a multi-workspace planning instrument, not a marketing page and not a stack of
  independent cards.
- The shell must feel stable while the active task surface changes below it.
- The active work surface should dominate the screen.
- Secondary context must stay available, but visually subordinate.

## Core doctrine

- `Canvas first`: when a workspace has a map, board, room, or inspector-led task surface, that
  surface owns the layout. Surrounding chrome should support it, not compete with it.
- `One stable shell`: keep one anchored top shell for title, workspace mode, concise status, and
  exit. Do not keep reintroducing new full-width header cards below it.
- `Operational density`: teacher workspaces should prefer compact action bands, short labels,
  symbols, and visible state over paragraph-heavy helper copy.
- `Progressive disclosure`: history, metadata, setup help, and destructive actions belong in
  drawers, menus, inspectors, or compact strips unless they are the primary task.
- `Symbol-supported controls`: repeated workspace actions should be icon-first or icon-supported.
  Text-only buttons are for rare, high-commitment, or ambiguous actions.
- `Desktop-first composition`: workspace-heavy curated apps should be designed for laptop and
  desktop layouts first. Smaller screens are reduced ports, not the primary composition source.
- `Context stability`: mode switches, primary actions, and status locations should not jump between
  workspaces.
- `Secondary means secondary`: classroom selection, history, and summaries should stay present but
  should not visually outweigh the live group board, room canvas, or rules map.
- `Dead-space discipline`: empty margins, oversized headers, and large vertical gaps are a product
  smell in dense planning tools.

## Current failure pattern to avoid

The current screenshots show one repeated problem in different forms:

- the UI reaches the real workspace too late
- too many full-width framed bands stack before the live surface
- too many adjacent sections are treated as equal-weight cards
- the action language is too text-heavy for repeated teacher operations

In practice this creates a page that feels "maximal" even though the visual language itself is
fairly restrained.

## Screenshot-grounded diagnosis

### Overview

- The top shell is already a large framed surface, but the page then immediately introduces more
  large resume and management cards instead of a tighter class-first dashboard.
- `Fortsätt grupper` and `Fortsätt sittschema` are too large relative to their importance.
- Class and classroom management read as equally prominent destinations instead of secondary setup
  context below the active work.

### Grouping

- The workspace spends a full-width band on classroom context, then another on smart summaries,
  before the user reaches the actual group board.
- The toolbar reads like a row of independent text buttons instead of a fast operational strip.
- Student pool and group columns compete as equally framed blocks instead of one shared grouping
  surface.

### Seating

- The workspace stacks shell, action bar, export status, smart-summary bar, and only then the room
  canvas.
- The export/download state consumes a full-width band even though it is not the main task.
- The canvas is important, but the chrome above it currently owns too much vertical attention.

### Rules

- The rules workspace should not read as a set of equal-weight bordered cards or a persistent
  right-side inspector squeezing the authoring map.
- The map itself must stay dominant while transient rule creation/editing feedback lives in the
  tool rail and saved rules collapse into a compact summary surface above the map.
- Saved-rule summaries must stay calm, dense, and icon-led; they should not expand into a tall
  button-heavy secondary application beside the canvas.

## Layout rules

### 1. One dominant work surface

- `Grupper` should read as student pool plus group board, not as toolbar plus cards plus board.
- `Sittplatser` should read as student pool plus room canvas, with the canvas clearly winning the
  visual hierarchy.
- `Regler` should read as compact tool rail plus dominant shared map with a lightweight summary
  surface above it, not as three equal cards or a right-side inspector squeezing the canvas.

### 1b. Desktop is the source composition

- For workspace-heavy curated apps, desktop and laptop layouts define the real product.
- Mobile should be treated as a separate reduced experience with fewer simultaneous controls and, if
  necessary, fewer available operations.
- Do not flatten the desktop workspace into stacked cards merely to preserve one shared layout model
  across all breakpoints.
- Breakpoints should adapt the composition deliberately, not force the desktop into a phone-shaped
  compromise.

## Viewport proof matrix

- `phone`: `390x844` reduced companion proof below the full desktop-composition range
- `tablet`: `768x1024` reduced companion proof aligned to the `ADR-0020` tablet breakpoint
- `laptop`: `1366x768` minimum full desktop-composition proof for teacher workspaces
- `desktop`: `1440x900` roomy full desktop-composition proof for teacher workspaces

Use these named viewports in redesign reviews instead of vague references to "common widths" or
"canonical desktop widths."

### 2. Chrome stays thin

- Use the top shell for the workspace toggle, current context, compact status, and exit only.
- Avoid stacking another large explanatory panel directly under the top shell unless the workspace
  is blocked by missing prerequisites or a serious error.
- Prefer one compact action row per workspace over multiple full-width status and helper bands.
- When transient feedback is needed, prefer:
  - inline status inside the action row
  - a compact strip attached to the local surface
  - toast/inbox feedback for completed exports
  instead of a new page-wide band.

### 3. Stable side structures

- Rails, summary bands, drawers, and side pools should keep fixed jobs.
- Do not make the user rediscover where history, smart settings, or student metadata lives in each
  workspace.
- If a side surface is secondary, it should visually recede through border weight, scale, and copy
  density rather than through disappearance alone.
- In `Regler`, the tool rail owns pending selection and create/save confirmation, while the summary
  surface owns persisted rule overview and compact edit/remove actions.

## Control language

- Use segmented toggles and icon buttons for frequent mode and tool changes.
- Reserve large text buttons for start, save, export, destructive confirmation, or other
  commitment-heavy actions.
- Repeated verbs such as `Ångra`, `Gör om`, `Historik`, `Inställningar`, `Slumpa`, and close/dismiss
  actions should have consistent symbol support everywhere.
- Smart toggles, history toggles, and similar mode-local controls should be compact and adjacent to
  the workspace they affect.
- Dense action rows should have one obvious primary action, a small number of icon-supported
  secondary actions, and one overflow for the rest.

## Symbol system

- Repeated operations should map to one canonical symbol each across the planner.
- The symbol set should cover at minimum:
  - undo
  - redo
  - history
  - settings/rules
  - shuffle/randomize
  - add/create
  - close/dismiss
  - export/download
  - zoom in
  - zoom out
  - fit/reset view
  - overflow/more actions
- Use text labels when:
  - the action is app-specific or not industry-obvious
  - the action is destructive or high commitment
  - the user is still in a learnability-critical context
- Prefer icon-only or icon-led controls when the action is frequent, canonical, and space-sensitive.
- Tooltips, hover labels, nearby microcopy, and accessible names should explain symbols without
  forcing every control to become a text button.

## Copy density

- Workspace copy should be instructional, not essay-like.
- Default helper text should usually fit in one short line.
- Use badges, chips, count labels, and small status strips before adding another sentence block.
- The `40rem` reading rule applies to prose-heavy content, not to instrument panels that need to
  stay compact and scannable.

## Visual hierarchy

- The brutalist design language should provide structure, not bulk.
- Use hard borders and one major elevation surface, but do not multiply large framed cards when the
  user is already inside a framed workspace.
- Dense planner controls should avoid theatrical hover/press behavior that makes the UI feel noisy.
- Repeated nested white cards inside white cards should be treated as a warning sign.

## Anti-patterns to avoid

- Full-width explanatory panels above an already obvious workspace.
- Equal visual weight for header, toolbar, summaries, student pool, and canvas.
- Text-only action bars with many medium-priority buttons in one row.
- Multiple stacked status bars that each consume their own band.
- Repeating the same context in large prose blocks, headings, and helper lines.
- Treating every workspace subsection as its own "card page."
- Giving side rails or summary surfaces the same visual mass as the central map or board.

## Implications for the upcoming UI overhaul

- The next Klassrumskartan design pass should simplify and compress the shell before adding new
  visual treatments.
- We should remove or merge low-value status/helper bands before inventing new ornaments.
- We should prefer icon-supported, compact control language and stronger workspace dominance over
  more framed panels.
- We should design the desktop workspace as the canonical experience and define mobile as a reduced
  companion layout instead of letting mobile constraints shape the main composition.
- The correct target is "coherent planning instrument," not "more decorated brutalist UI."
