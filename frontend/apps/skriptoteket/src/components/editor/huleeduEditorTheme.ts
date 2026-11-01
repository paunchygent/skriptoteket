/**
 * Purpose:
 *     One CodeMirror editor theme and syntax highlight style whose colours all
 *     read the shared --huleedu-editor-* and --huleedu-syntax-* design tokens.
 *
 * Relationships:
 *     - The token values live in huleedu-design-tokens.css under each
 *       data-theme palette; because the colours are CSS variables, a
 *       data-theme change repaints the editors through CSS with no reload and
 *       no extension reconfigure.
 *     - CodeMirrorEditor.vue and CodeMirrorMergeDiff.vue add huleeduEditorTheme
 *       and syntaxHighlighting(huleeduHighlightStyle); each keeps its own
 *       layout and font rules.
 *     - huleeduEditorTheme.spec.ts asserts every colour value is a token
 *       reference.
 */

import { HighlightStyle } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags } from "@lezer/highlight";

export const huleeduEditorThemeSpec = {
  "&": {
    backgroundColor: "var(--huleedu-editor-bg)",
  },
  ".cm-gutters": {
    backgroundColor: "var(--huleedu-editor-gutter-bg)",
    color: "var(--huleedu-editor-gutter-text)",
  },
  ".cm-content": {
    caretColor: "var(--huleedu-editor-cursor)",
  },
  ".cm-cursor, .cm-dropCursor": {
    borderLeftColor: "var(--huleedu-editor-cursor)",
  },
  "&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, &.cm-focused .cm-content ::selection": {
    backgroundColor: "var(--huleedu-editor-selection)",
  },
  ".cm-selectionBackground, .cm-content ::selection": {
    backgroundColor: "var(--huleedu-editor-selection)",
  },
  ".cm-activeLine": {
    backgroundColor: "var(--huleedu-editor-active-line)",
  },
  ".cm-activeLineGutter": {
    backgroundColor: "var(--huleedu-editor-active-line)",
  },
};

export const huleeduEditorTheme = EditorView.theme(huleeduEditorThemeSpec);

export const huleeduHighlightStyle = HighlightStyle.define([
  { tag: tags.comment, color: "var(--huleedu-syntax-comment)" },
  {
    tag: [
      tags.function(tags.variableName),
      tags.function(tags.propertyName),
      tags.className,
      tags.definition(tags.variableName),
    ],
    color: "var(--huleedu-syntax-function)",
  },
  { tag: tags.keyword, color: "var(--huleedu-syntax-keyword)" },
  { tag: [tags.number, tags.bool], color: "var(--huleedu-syntax-number)" },
  { tag: [tags.string, tags.escape], color: "var(--huleedu-syntax-string)" },
]);
