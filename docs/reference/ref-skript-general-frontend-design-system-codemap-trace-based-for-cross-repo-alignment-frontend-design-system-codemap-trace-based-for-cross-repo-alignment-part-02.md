---
type: reference
id: REF-SKRIPT-GENERAL-frontend-design-system-codemap-trace-based-for-cross-repo-alignment-PART-02
title: Frontend design-system codemap (trace-based for cross-repo alignment) — part
  02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-frontend-design-system-codemap-trace-based-for-cross-repo-alignment
part: 2
---

3. **Follow rule 045** for Brutalist Academic design principles

4. **Reference the codemap** for implementation details

5. **Adhere to the frozen primitive contracts** from PR-0157

---

### Source: Design Principles Summary


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

### Source: Token Reference


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

### Source: Frozen Primitive Constants


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

### Source: Verification Checklist


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

### Source: Related Files


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

## Decisions And Interpretation

No separate decisions and interpretation is stated in the source.
