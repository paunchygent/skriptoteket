import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

const NON_CODE_CONTEXTS = new Set(["String", "FormatString", "Comment"]);

export function isInNonCodeContext(state: EditorState, pos: number): boolean {
  type NamedNode = { name: string; parent: NamedNode | null };

  const resolvedPos = Math.max(0, Math.min(pos, state.doc.length));
  let node: NamedNode | null = syntaxTree(state).resolveInner(resolvedPos, -1) as unknown as NamedNode;
  while (node) {
    if (NON_CODE_CONTEXTS.has(node.name)) return true;
    node = node.parent;
  }
  return false;
}

export function resolvePythonIdentifierNode(
  state: EditorState,
  pos: number,
  side: -1 | 0 | 1,
): { from: number; to: number; name: string } | null {
  const resolvedPos = Math.max(0, Math.min(pos, state.doc.length));
  const node = syntaxTree(state).resolveInner(resolvedPos, side);
  if (node.name !== "VariableName" && node.name !== "PropertyName") return null;
  return {
    from: node.from,
    to: node.to,
    name: state.doc.sliceString(node.from, node.to),
  };
}
