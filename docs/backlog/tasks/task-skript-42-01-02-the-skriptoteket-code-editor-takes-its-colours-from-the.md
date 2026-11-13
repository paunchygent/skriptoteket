---
type: task
id: TASK-SKRIPT-42-01-02
title: The Skriptoteket code editor takes its colours from the editor and syntax tokens and follows the theme
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-01'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - CodeMirror builds its editor theme and highlight style from --huleedu-editor-* and --huleedu-syntax-* and repaints when data-theme changes, without a reload
story: ST-SKRIPT-42-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Both CodeMirror editors take their colours from the shared editor and syntax
tokens, and repaint when `data-theme` changes, with no reload.

- A new module, `components/editor/huleeduEditorTheme.ts`, exports:
  - `huleeduEditorThemeSpec`, the plain style-spec object, and
    `huleeduEditorTheme = EditorView.theme(huleeduEditorThemeSpec)`. Its background, gutter, gutter
    text, cursor, selection and active line read `var(--huleedu-editor-bg)`,
    `-gutter-bg`, `-gutter-text`, `-cursor`, `-selection` and `-active-line`.
  - `huleeduHighlightStyle`, a `HighlightStyle.define`. Comment, function,
    keyword, number and string tags read `var(--huleedu-syntax-*)`.
- `CodeMirrorEditor.vue` and `CodeMirrorMergeDiff.vue` replace their inline
  themes and `syntaxHighlighting(defaultHighlightStyle)` with these exports.
- The values are CSS variables, so a `data-theme` change repaints through CSS.
  There is no `MutationObserver` and no `Compartment` reconfigure.
- Non-goals: editor layout and fonts, and new syntax tokens.

## Contract Inputs

- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`: the
  theme at lines 68-79 and `defaultHighlightStyle` at line 106.
- `components/editor/diff/CodeMirrorMergeDiff.vue`: the theme at lines 45-60
  and `defaultHighlightStyle` at line 68.
- Tokens: `--huleedu-editor-{bg,gutter-bg,gutter-text,cursor,selection,active-line}`
  and `--huleedu-syntax-{comment,function,keyword,number,string}` in
  `huleedu-design-tokens.css`.

## Core Vertical And Performance

One unit, U1: write the module, and use it in both editors.

No performance concern: the theme is built once per editor.

## Validation

- A new `huleeduEditorTheme.spec.ts` asserts that every colour value in
  `huleeduEditorThemeSpec` is a `var(--huleedu-editor-*)` reference, and that
  every colour in `huleeduHighlightStyle.specs` is a `var(--huleedu-syntax-*)`
  reference.

## Stop Conditions

- A CodeMirror tag that the current editors colour has no matching syntax
  token: stop and report it. Add no token.
- The `@codemirror/view` or `@codemirror/language` API differs from the current
  docs: report the version.

## Decided Contract Terms

| ID  | Decided contract term                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------- |
| M2  | CodeMirror builds its theme and highlight style from the editor and syntax tokens and follows `data-theme`. |
| X6  | One shared module, `huleeduEditorTheme.ts`, with CSS-variable values; there is no JavaScript theme swap.    |
