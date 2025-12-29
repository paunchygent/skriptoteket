---
type: reference
id: REF-codemirror-integration
title: "CodeMirror integration reference (Skriptoteket SPA)"
status: active
owners: "agents"
created: 2025-12-29
topic: "codemirror"
---

This reference documents the CodeMirror 6 feature surface we rely on in Skriptoteket, with an IDE-like goal (VS Code
style): fast feedback, discoverable problems list, keyboard navigation, and quick-fix actions that are safe and
predictable.

## Packages (installed)

From `frontend/apps/skriptoteket/package.json`:

- `@codemirror/autocomplete` `^6.20.0`
- `@codemirror/commands` `^6.10.1`
- `@codemirror/lang-python` `^6.2.1`
- `@codemirror/language` `^6.11.3`
- `@codemirror/lint` `^6.9.2`
- `@codemirror/search` `^6.5.11`
- `@codemirror/state` `^6.5.2`
- `@codemirror/view` `^6.39.4`

## Linting primitives (`@codemirror/lint`)

### Diagnostics

Diagnostics are plain objects:

- `from` / `to`: document offsets
- `severity`: `"error" | "warning" | "info" | "hint"`
- `message`: user-facing message
- `source?`: stable identifier (use this for rule IDs, grouping, and future toggles)
- `markClass?`: extra CSS class for the marked range
- `actions?`: “quick fixes” (see below)

**Convention (Skriptoteket):** always set `source` for every diagnostic (rule ID or subsystem ID). This makes the lint
panel and future filtering behave predictably.

### Quick-fix actions (`Diagnostic.actions`)

CodeMirror represents “code actions” via `Diagnostic.actions`, where each action contains:

- `name`: button label
- `apply(view, from, to)`: performs the edit using CodeMirror transactions
- `markClass?`: optional CSS class for the action button

**Convention (Skriptoteket):**

- Actions MUST be idempotent (re-running doesn’t corrupt code).
- Actions MUST never depend on stale offsets; `apply` receives the diagnostic’s current `from/to`.
- Prefer minimal edits (single change-set) and keep formatting stable.

### Linter extension (`linter(source, config)`)

`linter` installs a linting pipeline and re-runs after typing pauses.

- `source(view) => Diagnostic[] | Promise<Diagnostic[]>`
- `config.delay` (ms, default 750)
- `config.autoPanel` (defaults off): auto open/close lint panel based on diagnostics
- `config.markerFilter` / `config.tooltipFilter`: select which diagnostics create document markers / show in tooltip

**Convention (IDE-like behavior):** keep `autoPanel` off and let the user open the panel via keybinding/UI toggle.

### Lint gutter (`lintGutter(config)`)

`lintGutter` shows per-line markers in the gutter and a hover tooltip.

Recommended filtering:

```ts
lintGutter({
  markerFilter: (ds) => ds.filter(d => d.severity === "error" || d.severity === "warning"),
  tooltipFilter: (ds) => ds
})
```

Rationale: errors/warnings deserve constant attention; info/hint remain discoverable via hover and the lint panel.

### Lint panel + keyboard navigation

Commands:

- `openLintPanel` / `closeLintPanel`
- `nextDiagnostic` / `previousDiagnostic`

Keymaps:

- `lintKeymap` includes `Mod-Shift-m` (open panel) and `F8` (next diagnostic)
- Add `Shift-F8` binding for `previousDiagnostic` to match IDE expectations

### Introspection helpers

- `diagnosticCount(state)`: number of active diagnostics (status bar / toolbar)
- `forEachDiagnostic(state, fn)`: iterate active diagnostics
- `setDiagnostics(state, diagnostics)`: programmatic update (also enables lint if needed)
- `setDiagnosticsEffect`: state effect behind `setDiagnostics` (for advanced extensions)
- `forceLinting(view)`: triggers linting immediately (use sparingly; prefer debounce)

## Where this fits in Skriptoteket

See:

- `docs/reference/ref-linter-architecture.md` (Context-Rule linter design, diagnostics + quick-fixes)
- `docs/adr/adr-0048-linter-context-and-data-flow.md` (data flow + syntax error strategy)
