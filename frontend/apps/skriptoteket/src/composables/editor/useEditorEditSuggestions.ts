import type { Text } from "@codemirror/state";
import type { EditorView } from "@codemirror/view";
import { computed, ref, type Ref } from "vue";

import { apiFetch, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type EditSuggestionResponse = components["schemas"]["EditorEditSuggestionResponse"];

type SelectionSnapshot = {
  from: number;
  to: number;
  doc: Text;
};

type UseEditorEditSuggestionsOptions = {
  editorView: Readonly<Ref<EditorView | null>>;
  isReadOnly: Readonly<Ref<boolean>>;
  beforeApply?: () => Promise<void> | void;
};

const MAX_PREFIX_CHARS = 4000;
const MAX_SUFFIX_CHARS = 4000;

function buildSelectionSnapshot(view: EditorView): {
  snapshot: SelectionSnapshot;
  prefix: string;
  selection: string;
  suffix: string;
} | null {
  const selectionRange = view.state.selection.main;
  if (selectionRange.empty) return null;

  const doc = view.state.doc;
  const from = selectionRange.from;
  const to = selectionRange.to;
  const selection = doc.sliceString(from, to);
  const prefixFrom = Math.max(0, from - MAX_PREFIX_CHARS);
  const suffixTo = Math.min(doc.length, to + MAX_SUFFIX_CHARS);
  const prefix = doc.sliceString(prefixFrom, from);
  const suffix = doc.sliceString(to, suffixTo);

  return {
    snapshot: { from, to, doc },
    prefix,
    selection,
    suffix,
  };
}

export function useEditorEditSuggestions({
  editorView,
  isReadOnly,
  beforeApply,
}: UseEditorEditSuggestionsOptions) {
  const instruction = ref("");
  const suggestion = ref("");
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const selectionSnapshot = ref<SelectionSnapshot | null>(null);

  const canApply = computed(() => {
    if (isReadOnly.value) return false;
    if (isLoading.value) return false;
    if (!suggestion.value) return false;
    return selectionSnapshot.value !== null;
  });

  async function requestSuggestion(): Promise<void> {
    error.value = null;
    suggestion.value = "";

    if (isReadOnly.value) {
      error.value = "Editorn är låst för redigering.";
      return;
    }

    const view = editorView.value;
    if (!view) {
      error.value = "Editorn är inte redo ännu.";
      return;
    }

    const selection = buildSelectionSnapshot(view);
    if (!selection || !selection.selection.trim()) {
      error.value = "Markera ett kodavsnitt först.";
      return;
    }

    const instructionText = instruction.value.trim();
    selectionSnapshot.value = selection.snapshot;
    isLoading.value = true;

    try {
      const response = await apiFetch<EditSuggestionResponse>("/api/v1/editor/edits", {
        method: "POST",
        body: {
          prefix: selection.prefix,
          selection: selection.selection,
          suffix: selection.suffix,
          instruction: instructionText || null,
        },
      });

      if (!response.enabled) {
        error.value = "AI-redigering är inte aktiverad.";
        suggestion.value = "";
        return;
      }

      suggestion.value = response.suggestion ?? "";
      if (!suggestion.value) {
        error.value = "Inget förslag kunde skapas.";
      }
    } catch (err: unknown) {
      if (isApiError(err)) {
        error.value = err.message;
      } else {
        error.value = "Det gick inte att hämta ett AI-förslag.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function applySuggestion(): Promise<void> {
    error.value = null;

    const view = editorView.value;
    const snapshot = selectionSnapshot.value;
    if (!view || !snapshot) {
      error.value = "Ingen aktiv markering att ersätta.";
      return;
    }

    if (!suggestion.value) {
      error.value = "Det finns inget förslag att använda.";
      return;
    }

    if (!view.state.doc.eq(snapshot.doc)) {
      error.value = "Koden har ändrats. Begär ett nytt förslag.";
      return;
    }

    if (beforeApply) {
      await beforeApply();
    }

    view.dispatch({
      changes: { from: snapshot.from, to: snapshot.to, insert: suggestion.value },
      selection: { anchor: snapshot.from + suggestion.value.length },
      scrollIntoView: true,
    });

    suggestion.value = "";
    selectionSnapshot.value = null;
  }

  function clearSuggestion(): void {
    suggestion.value = "";
    error.value = null;
    selectionSnapshot.value = null;
  }

  return {
    instruction,
    suggestion,
    isLoading,
    error,
    canApply,
    requestSuggestion,
    applySuggestion,
    clearSuggestion,
  };
}
