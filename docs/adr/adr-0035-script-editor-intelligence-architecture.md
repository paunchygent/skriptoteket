---
type: adr
id: ADR-0035
title: "Script editor intelligence architecture (CodeMirror 6)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-24
---

## Context

Script authors writing tools for Skriptoteket need to discover available helpers (`pdf_helper`, `tool_errors`) and follow
the runner contract. Currently, this information exists only in the KB documentation (`ref-ai-script-generation-kb.md`)
and is not surfaced in the editor.

We need an in-editor intelligence system that provides:

- Autocomplete for Skriptoteket-specific imports and contract keys
- Lint diagnostics for common errors (missing entrypoint, invalid contract, blocked APIs)
- Hover documentation for helper functions

### Constraints

- All analysis must run in-browser (no external services)
- Swedish UI for lint messages and hover docs
- Performance acceptable for ~500+ line scripts
- Maintainability: rules easy to extend as KB evolves

### Options Considered

1. **Regex-based scanning** - Simple but prone to false positives in strings/comments
2. **Lezer syntax tree** - Already bundled via `@codemirror/lang-python`, reliable structure detection
3. **Tree-sitter / Pyodide** - Heavy payload, unnecessary for this scope

## Decision

Use **Lezer-based syntax tree analysis** with the following architecture:

### Extension Composition

Create a unified extension suite that composes cleanly:

```
skriptoteketIntelligence(config)
├─ skriptoteketConfig facet (entrypoint name, language)
├─ autocomplete: helper imports + contract snippets
├─ hoverTooltip: helper docs (Swedish)
└─ linter: entrypoint + contract + security + best practices
```

### Analysis Approach

- Use the Python syntax tree (from `@codemirror/lang-python`) for structure-aware detection
- Parse imports, function definitions, return statements, and function calls
- Fall back to regex only for simple pattern detection where structure doesn't matter
- Always key analysis off the configured entrypoint name (default `run_tool`, but configurable per tool)
- Treat `return "<html>"` as supported legacy output and do not run Contract v2 linting on string returns

### State Sharing

- Define a `Facet` for configuration (entrypoint name, helper metadata)
- Use the shared language syntax tree (already part of editor state)
- Add a `StateField` cache only if profiling shows repeated tree walks are expensive

### Lint Performance Model

- Rely on CodeMirror's built-in debounce (default 750ms idle delay)
- Keep scanning linear, avoid backtracking regex
- Consider Web Worker only if profiling shows UI lag on large documents

### File Layout

```
frontend/apps/skriptoteket/src/composables/editor/
├─ skriptoteketIntelligence.ts    # Bundle export
├─ skriptoteketCompletions.ts     # Autocomplete sources
├─ skriptoteketLinter.ts          # Lint rules
├─ skriptoteketHover.ts           # Hover tooltips
└─ skriptoteketMetadata.ts        # Shared constants (kinds, levels, helper docs)
```

### Integration Point

Add an `extensions?: Extension[]` prop to `CodeMirrorEditor.vue` to keep it generic. Pass the ST-08-10 extensions from
`ScriptEditorView.vue`.

Implementation note: `extensions` injection must be reactive (use a CodeMirror `Compartment` + `reconfigure`) so changes
to entrypoint/config can update linting/completions without destroying the editor instance.

## Consequences

### Positive

- **Reliable detection**: Lezer provides robust parsing even on incomplete code
- **No new dependencies**: Python language support already bundled
- **Composable design**: Each feature (completions, lint, hover) is independent
- **Maintainable**: Single source of truth for helper docs and contract constants

### Negative

- **Static analysis limits**: Cannot trace dynamic return values; heuristics only
- **False positives possible**: Best-practice lints (encoding, mkdir) may be noisy
- **Swedish-only**: Lint messages hardcoded in Swedish (acceptable for target audience)

### Mitigations

- Only lint when patterns are confident (literal dict/list returns)
- Use `info` severity for uncertain best-practice hints
- Keep rule constants in `skriptoteketMetadata.ts` for easy updates

## Review Notes (2025-12-24)

Reviewed in ST-08-10 technical design review:

- Confirmed Lezer-first, regex only where structure doesn't matter
- Entrypoint-aware linting/completions (use current configured entrypoint)
- `extensions` injection must be reactive (`Compartment` + `reconfigure`)
- Autocomplete auto-trigger (`startCompletion`) must be gated to avoid strings/comments
- Prefer `pythonLanguage.data.of({ autocomplete: ... })` to add completions without overriding built-in Python sources
- Add `lintGutter()` in the Skriptoteket intelligence bundle for visibility
- Network lint scope: flag `aiohttp`, `requests`, `httpx`, `urllib3`, and `urllib.request`/`urlopen`-style usage
- Write-outside-output lint: warn only on obvious absolute string literal writes outside `/work/output` (exclude `/tmp`)
- Dynamic return handling: when entrypoint exists but has no literal dict/str returns, emit a single `hint` diagnostic
  about contract verification being unavailable

### Risks / Gaps

- Lezer Python node-name matching can be brittle; keep tree-walking utilities centralized and add focused fixtures/tests
- In incomplete `return { ... }` literals (before typing the first `:` separator), Lezer can classify the container as
  `SetExpression`/`SetComprehensionExpression` (especially with CodeMirror `closeBrackets()` auto-inserting `}`), so
  completions should treat those nodes as “in-progress dicts”.
- Ensure custom completions do not replace built-in Python completions (prefer language data over `autocompletion({override})`)
- Performance: avoid multiple full tree traversals per lint run; build a small per-run snapshot for rules to consume
- Tooltip styling may need a dedicated theme/CSS hook to match Skriptoteket’s brutalist UI (default CM6 tooltip is acceptable for MVP)

## References

- [ST-08-10: Script editor intelligence](../backlog/stories/story-08-10-script-editor-intelligence.md)
- [EPIC-08: Contextual help and onboarding](../backlog/epics/epic-08-contextual-help-and-onboarding.md)
- [ref-ai-script-generation-kb.md](../reference/ref-ai-script-generation-kb.md) - Source of truth for lint rules
