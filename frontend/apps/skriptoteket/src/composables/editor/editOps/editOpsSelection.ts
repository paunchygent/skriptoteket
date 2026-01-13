import type { EditorView } from "@codemirror/view";
import type { EditorEditOpsCursor, EditorEditOpsSelection } from "./editorEditOpsApi";

type ResolveSelectionParams = {
  view: EditorView | null;
  includeCursorWhenNoSelection: boolean;
};

type ResolveSelectionResult = {
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
};

export function resolveEditOpsSelection({
  view,
  includeCursorWhenNoSelection,
}: ResolveSelectionParams): ResolveSelectionResult {
  if (!view) {
    return { selection: null, cursor: null };
  }

  const main = view.state.selection.main;
  if (!main.empty) {
    return {
      selection: { from: main.from, to: main.to },
      cursor: { pos: main.to },
    };
  }

  return {
    selection: null,
    cursor: includeCursorWhenNoSelection ? { pos: main.from } : null,
  };
}
