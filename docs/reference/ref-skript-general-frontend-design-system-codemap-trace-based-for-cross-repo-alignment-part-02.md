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

3. **Follow `huleedu-ui-design`** for current presentation guidance

4. **Reference the codemap** for implementation details

5. **Use the current `huleedu-integrated` resource contracts** from
   `resources/frontend-design-system/huleedu-integrated/` in `skill-repository`.
   PR-0157 records the historical extraction, not current presentation authority.

---

### Source: Design Principles Summary


Current presentation guidance belongs to `huleedu-ui-design`, especially
`references/visual-system.md`; workflow composition belongs to its
`references/interaction-design.md` and `references/dense-workspaces.md`.
This codemap records implementation locations, not a separate design doctrine.

Token values, Tailwind mappings, Vue primitives and glyphs belong to the
`huleedu-integrated` package in
`skill-repository/resources/frontend-design-system/huleedu-integrated/`.
Use the current package contracts rather than freezing an earlier snapshot.
`integrated-frontend-stack` owns token integration and CSS layout mechanics.

---

### Source: Token Reference


The current consumer mappings in `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`
include the following token names. Resolve values and component usage through the
current package and `huleedu-ui-design`, not a copied palette or shadow table.

| Token | Example mapped utility |
|-------|------------------------|
| `--huleedu-canvas` | `bg-canvas` |
| `--huleedu-navy` | `text-navy`, `border-navy` |
| `--huleedu-action` | `bg-action` |
| `--huleedu-critical` | `text-critical` |
| `--huleedu-success` | `text-success` |
| `--huleedu-warning` | `text-warning` |
| `--huleedu-error` | `text-error` |

---

### Source: Primitive Constants


`frontend/apps/skriptoteket/src/components/ui/shared/denseToolPrimitives.ts`
contains these synced package exports:

| Export | Current class |
|--------|---------------|
| `DENSE_ACTION_RADIUS_CLASS` | `rounded-[4px]` |
| `DENSE_ICON_SIZE_CLASS` | `h-9 w-9` |
| `DENSE_TEXT_HEIGHT_CLASS` | `h-[28px]` |
| `DENSE_COMPACT_SEGMENT_HEIGHT_CLASS` | `h-6` |

These are implementation facts, not independent cross-repo requirements.
The current package owns primitive contracts; `huleedu-ui-design` owns which
control role and feedback suit a surface.

---

### Source: Verification Checklist


When adopting this design system in another repo, verify:

- [ ] Token pipeline: Backend CSS → Tailwind theme bridge is complete
- [ ] Single CSS entry point imports Tailwind, tokens, then theme bridge
- [ ] Shared primitives and resources match the current `huleedu-integrated` package contracts
- [ ] Shared UI components use the class builders
- [ ] Toast system is mounted at app root
- [ ] Segmented toggles use the shell constants
- [ ] Token and Tailwind integration follows the applicable mechanics in ADR-0032, not its historical presentation prescriptions
- [ ] Presentation follows `huleedu-ui-design` and its task-relevant references
- [ ] Primitive contracts come from the current package, not historical constants
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

- `frontend/apps/skriptoteket/src/components/ui/shared/denseToolPrimitives.ts`

- `frontend/apps/skriptoteket/src/components/ui/shared/components/UiDenseActionButton.vue`

- `frontend/apps/skriptoteket/src/components/ui/shared/components/UiDenseIconButton.vue`

- `frontend/apps/skriptoteket/src/components/ui/shared/components/UiSegmentedToggle.vue`

- `frontend/apps/skriptoteket/src/components/ui/shared/components/ToastHost.vue`

- `frontend/apps/skriptoteket/src/components/ui/SkriptoteketToastHost.vue`

- `frontend/apps/skriptoteket/src/components/ui/index.ts`

### Governance

- `docs/decisions/adr-skript-0017-huleedu-design-system-adoption-for-frontend-harmonization.md`
  (proposed historical adoption record; non-authorizing, not a compliance requirement)

- `docs/decisions/adr-skript-0032-frontend-styling-tailwind-css-4-with-theme-design-tokens.md`
  (token and Tailwind integration mechanics only; not current presentation authority)

- `huleedu-ui-design` skill (current presentation authority)

### Reference

- `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
  (historical extraction record; not current presentation authority)

## Decisions And Interpretation

No separate decisions and interpretation is stated in the source.
