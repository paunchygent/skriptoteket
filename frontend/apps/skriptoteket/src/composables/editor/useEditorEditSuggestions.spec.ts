import { describe, expect, it, vi } from "vitest";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { ref, shallowRef } from "vue";

import { apiFetch } from "../../api/client";
import { useEditorEditSuggestions } from "./useEditorEditSuggestions";

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
}));

function createEditor(doc: string, selection: { from: number; to: number }): { view: EditorView; parent: HTMLElement } {
  const parent = document.createElement("div");
  document.body.appendChild(parent);

  const view = new EditorView({
    state: EditorState.create({
      doc,
      selection: { anchor: selection.from, head: selection.to },
    }),
    parent,
  });

  return { view, parent };
}

describe("useEditorEditSuggestions", () => {
  it("requests and applies an edit suggestion", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ suggestion: "return 2\n", enabled: true });

    const doc = "def x():\n    return 1\n";
    const from = doc.indexOf("return 1");
    const to = from + "return 1".length;
    const { view, parent } = createEditor(doc, { from, to });

    const editorView = shallowRef<EditorView | null>(view);
    const isReadOnly = ref(false);

    const { suggestion, requestSuggestion, applySuggestion } = useEditorEditSuggestions({
      editorView,
      isReadOnly,
    });

    try {
      await requestSuggestion();
      expect(suggestion.value).toBe("return 2\n");

      applySuggestion();
      expect(view.state.doc.toString()).toContain("return 2");
    } finally {
      view.destroy();
      parent.remove();
    }
  });

  it("shows an error when no selection exists", async () => {
    const doc = "def x():\n    return 1\n";
    const { view, parent } = createEditor(doc, { from: 0, to: 0 });

    const editorView = shallowRef<EditorView | null>(view);
    const isReadOnly = ref(false);

    const { error, requestSuggestion } = useEditorEditSuggestions({
      editorView,
      isReadOnly,
    });

    try {
      await requestSuggestion();
      expect(error.value).toBe("Markera ett kodavsnitt först.");
    } finally {
      view.destroy();
      parent.remove();
    }
  });
});
