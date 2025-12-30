import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";
import type { Diagnostic } from "@codemirror/lint";

export function findPythonSyntaxErrors(
  state: EditorState,
  tree: ReturnType<typeof syntaxTree> = syntaxTree(state),
): Diagnostic[] {
  const cursor = tree.cursor();
  const result: Diagnostic[] = [];

  function walk(): void {
    do {
      if (cursor.name === "⚠") {
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
