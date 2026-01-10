---
type: pr
id: PR-0012
title: "Editor cohesion pass: selectors + Testkör/Metadata/Diff panel language"
status: in_progress
owners: "agents"
created: 2026-01-09
updated: 2026-01-09
stories:
  - "ST-14-32"
tags: ["frontend", "editor", "ux"]
acceptance_criteria:
  - "Selectors (preset/entrypoint/diff target) use one compact size system and consistent tooltip/help pattern."
  - "Testkör mode uses the same in-editor utility hierarchy (no large CTA-style buttons) and the layout reads as one cohesive editor surface."
  - "Metadata/Diff modes use the same compact header density as Källkod mode; no drawer-style headers within the editor."
  - "Switching modes does not change the overall perceived spacing scale (no sudden 'page' vs 'panel' density shifts)."
  - "Playwright editor smoke remains stable and is updated only when selectors/labels change."
---

## Problem

The editor shell is cohesive, but **Diff/Metadata/Testkör** still have divergent density and control styling:

- Drawer-style headers inside the editor surface (large h2 + paragraphs).
- Inconsistent button hierarchy (CTA-ish buttons in some panels, compact utilities elsewhere).
- Input selectors drift in size and tooltip semantics, and some help buttons collide with label-based selection in tests.

## Goal

Define and apply a single "editor panel language" across all modes:

- One spacing + typography scale inside the editor.
- One utility control sizing system (buttons/selects/inputs).
- One tooltip/help pattern that is accessible and test-friendly.

## Non-goals

- Rewriting editor business logic, API contracts, or state management.
- Adding new features to Testkör/Metadata/Diff beyond cohesion fixes.

## Decision checkpoint (must settle before implementation)

Resolved (2026-01-09):

1) **Selector sizing**: **A** — compact `h-[28px]` + `text-[11px]` (matches editor utilities)
2) **Help tooltip pattern**: **Yes** — help button `aria-label` must not include field label text; inputs/selects use
   `aria-describedby` for the tooltip content.
3) **Testkör action hierarchy**: **Ghost/compact** editor-utilities (no CTA-ish buttons)
4) **Language**: `Preset` → `Förval`

Additional scope clarifications (2026-01-09):

5) **Diff virtual file selector**
   - Replace the file "tabs" with a compact selector (dropdown).
   - Diff focuses on: `tool.py`, `settings_schema.json`, `input_schema.json`, `usage_instructions.md`.
   - `entrypoint.txt` is intentionally excluded from diff view (entrypoint is edited elsewhere; keeping it in the diff
     adds noise without practical value for authors).

6) **Diff download controls**
   - Move downloads so it is obvious **Före** downloads *before* and **Efter** downloads *after* (place actions directly
     under/next to their respective side labels).
   - File names should reflect the selected virtual file (`before-tool.py`, `after-tool.py`, `tool.py.patch`, etc.).

## Refactor path (proposed)

1) **Define primitives**
   - Introduce a single set of utility classes (or a tiny shared component) for:
     - editor utility buttons
     - editor selects/inputs
     - field label + optional help tooltip

2) **Normalize selectors**
   - Apply the primitives to:
     - schema preset selector
     - entrypoint selector + custom value
     - diff target selector

3) **Normalize panel headers**
   - For panel variants used *inside the editor grid*, replace drawer-style headers with compact section headers.

4) **Testkör mode cohesion**
   - Update Sandbox input/actions and sub-panels to use the same sizing + hierarchy.

5) **Verification**
   - Update Playwright editor smoke if labels/controls change.
   - Manual check: mode switching + scrolling + chat + long prompt behavior.

## Progress (as of 2026-01-09)

- Implemented compact selector baseline + tooltip `aria-describedby` pattern for entrypoint + schema preset (`Preset` → `Förval`).
- Diff view: dropdown file selector (no tabs), clearer per-side copy/download actions, filenames reflect selected virtual file.
- Testkör actions aligned to compact ghost utilities (no CTA-ish buttons).
- Testkör subpanels (inputs/sessionfiler/inställningar/debug/actions/artifacts) now follow the same compact card/header language inside the editor grid.
- Testkör outputs now render in compact density and match the same card/border language as the rest of the editor.
- Metadata/Instructions/Behörigheter panels now use compact panel headers (no drawer-style headers inside the editor grid).
- Diff viewer header/actions now align directly with the diff panes (file selector + patch actions above; per-side actions above their respective pane).
- Spara/Öppna: restore-point naming is explicit (no "lokal"), and Öppna sparade popover is now compact “ledger/menu” rows with timestamps, subtle active-row fill, secondary status text, and lightweight action links (no nested brutalist shadows).
- Chat drawer responsive fix: auto-collapses on narrow viewports (rail width) and avoids a modal backdrop in column mode, keeping the editor usable while still allowing expand via the rail button.

## Envisioned endstate (ASCII)

### Shared editor shell (all modes)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Title/summary/slug (inline)             Workflow actions      Mode toggles    │
│ Save/Open ▾  Lock badge  Status                                              │
├──────────────────────────────────────────┬───────────────────────────────────┤
│ MAIN (mode content; internal scroll)     │ CHAT (always available)           │
│                                          │ ┌───────────────────────────────┐ │
│ [Källkod | Diff | Metadata | Testkör]    │ │ Messages (scroll)              │ │
│                                          │ └───────────────────────────────┘ │
│                                          │ [Prompt textarea (auto-grow ↑)]  │
│                                          │ [Ny chatt] [Avbryt?] [Skicka]     │
├──────────────────────────────────────────┴───────────────────────────────────┤
│ Schemas (only in Källkod; collapsible; 2-col)                                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Metadata mode (compact sections, no big drawer header)

```
MAIN:
  [Verktygsinfo]  [Titel/URL-namn/Sammanfattning...]
  [Sökord]        [Yrken...] [Kategorier...]
  [Instruktioner] [Markdown editor/preview toggle (compact)]
  [Behörigheter]  [Maintainers list + add/remove (compact)]
```

### Testkör mode (same utility sizing; no CTA-ish controls)

```
MAIN:
  [Startfunktion ▾] [Välj filer] [Testkör] [Rensa?]
  [Indata (JSON)]  (details)
  [Sessionfiler]   (panel)
  [Inställningar]  (panel)
  [Resultat + Debug] (panels)
```

## Test plan

- FE lint: `pdm run fe-lint`
- UI smoke: `pdm run ui-editor-smoke --base-url http://127.0.0.1:5173`

## Rollback plan

- Revert PR-0012 only; PR-0011 remains done and unaffected.
