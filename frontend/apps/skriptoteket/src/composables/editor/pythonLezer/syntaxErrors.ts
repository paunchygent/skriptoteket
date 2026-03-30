import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";
import type { Diagnostic } from "@codemirror/lint";

function hasFunctionDefinitionAncestor(node: ReturnType<typeof syntaxTree>["topNode"] | null): boolean {
  let current = node;
  while (current) {
    if (current.name === "FunctionDefinition") {
      return true;
    }
    current = current.parent;
  }
  return false;
}

function isBareYieldParseQuirk(
  state: EditorState,
  tree: ReturnType<typeof syntaxTree>,
  errorRange: { from: number; to: number },
): boolean {
  if (errorRange.to !== errorRange.from) return false;

  const pos = errorRange.from;
  const line = state.doc.lineAt(Math.min(Math.max(pos, 1), state.doc.length));
  if (line.text.trim() !== "yield") return false;
  if (pos < state.doc.length && state.doc.sliceString(pos, pos + 1) !== "\n") return false;

  const candidatePositions = [Math.max(pos - 1, line.from), line.from];
  for (const candidatePos of candidatePositions) {
    const resolvedNode = tree.resolveInner(candidatePos, -1);
    let current = resolvedNode;
    while (current && current.name !== "YieldStatement") {
      current = current.parent;
    }
    if (!current) {
      continue;
    }
    if (state.doc.sliceString(current.from, current.to).trim() !== "yield") {
      continue;
    }
    if (current.to === pos && hasFunctionDefinitionAncestor(current.parent)) {
      return true;
    }
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
