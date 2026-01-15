import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";
import type { Diagnostic } from "@codemirror/lint";

function isBareYieldParseQuirk(
  state: EditorState,
  tree: ReturnType<typeof syntaxTree>,
  errorRange: { from: number; to: number },
): boolean {
  if (errorRange.to !== errorRange.from) return false;

  const pos = errorRange.from;
  if (pos <= 0) return false;

  if (pos < state.doc.length && state.doc.sliceString(pos, pos + 1) !== "\n") return false;

  const left = tree.resolveInner(pos - 1, -1);
  let current: typeof left | null = left;
  while (current && current.name !== "YieldStatement") current = current.parent;
  if (!current) return false;
  if (current.to !== pos) return false;

  const stmtText = state.doc.sliceString(current.from, current.to).trim();
  if (stmtText !== "yield") return false;

  let parent = current.parent;
  while (parent) {
    if (parent.name === "FunctionDefinition") return true;
    parent = parent.parent;
  }

  return false;
}

export function findPythonSyntaxErrors(
  state: EditorState,
  tree: ReturnType<typeof syntaxTree> = syntaxTree(state),
): Diagnostic[] {
  const cursor = tree.cursor();
  const result: Diagnostic[] = [];

  function walk(): void {
    do {
      if (cursor.name === "⚠") {
        if (isBareYieldParseQuirk(state, tree, { from: cursor.from, to: cursor.to })) continue;

        const from = cursor.from;
        const to = cursor.to > cursor.from ? cursor.to : Math.min(cursor.from + 1, state.doc.length);
        result.push({
          from,
          to,
          severity: "error",
          message: "Syntaxfel (ogiltig Python-syntax).",
        });
      }

      if (cursor.firstChild()) {
        walk();
        cursor.parent();
      }
    } while (cursor.nextSibling());
  }

  walk();
  return result;
}
