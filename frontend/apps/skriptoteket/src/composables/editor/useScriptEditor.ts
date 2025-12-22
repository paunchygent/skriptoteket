import { computed, onMounted, ref, watch, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type SaveResult = components["schemas"]["SaveResult"];

type UseScriptEditorOptions = {
  toolId: Readonly<Ref<string>>;
  versionId: Readonly<Ref<string>>;
  route: RouteLocationNormalizedLoaded;
  router: Router;
};

export function useScriptEditor({
  toolId,
  versionId,
  route,
  router,
}: UseScriptEditorOptions) {
  const editor = ref<EditorBootResponse | null>(null);
  const entrypoint = ref("");
  const sourceCode = ref("");
  const changeSummary = ref("");

  const isLoading = ref(true);
  const isSaving = ref(false);
  const errorMessage = ref<string | null>(null);
  const successMessage = ref<string | null>(null);

  const initialSnapshot = ref<{ entrypoint: string; sourceCode: string } | null>(null);

  const selectedVersion = computed(() => editor.value?.selected_version ?? null);
  const editorToolId = computed(() => editor.value?.tool.id ?? "");

  const saveButtonLabel = computed(() => {
    if (isSaving.value) return "Sparar...";
    return editor.value?.save_mode === "snapshot" ? "Spara" : "Skapa utkast";
  });

  const hasDirtyChanges = computed(() => {
    if (!initialSnapshot.value) return false;
    return (
      initialSnapshot.value.entrypoint !== entrypoint.value ||
      initialSnapshot.value.sourceCode !== sourceCode.value
    );
  });

  function normalizedOptionalString(value: string): string | null {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }

  function resolveEditorPath(): string | null {
    if (toolId.value !== "") {
      return `/api/v1/editor/tools/${encodeURIComponent(toolId.value)}`;
    }
    if (versionId.value !== "") {
      return `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}`;
    }
    return null;
  }

  async function loadEditor(): Promise<void> {
    const path = resolveEditorPath();

    if (!path) {
      errorMessage.value = "Ingen editor hittades.";
      isLoading.value = false;
      editor.value = null;
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;
    successMessage.value = null;

    try {
      const response = await apiGet<EditorBootResponse>(path);
      editor.value = response;
      entrypoint.value = response.entrypoint;
      sourceCode.value = response.source_code;
      changeSummary.value = "";
      initialSnapshot.value = {
        entrypoint: response.entrypoint,
        sourceCode: response.source_code,
      };
    } catch (error: unknown) {
      editor.value = null;
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ladda editorn.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function navigateAfterSave(path: string): Promise<void> {
    if (!path) {
      await loadEditor();
      return;
    }

    if (path === route.path) {
      await loadEditor();
      return;
    }

    await router.push(path);
  }

  async function save(): Promise<void> {
    if (!editor.value || isSaving.value) return;

    const entrypointValue = entrypoint.value.trim();
    if (!entrypointValue) {
      errorMessage.value = "Startfunktion krävs.";
      return;
    }

    isSaving.value = true;
    errorMessage.value = null;
    successMessage.value = null;

    try {
      const summaryValue = normalizedOptionalString(changeSummary.value);

      if (editor.value.save_mode === "snapshot") {
        const version = selectedVersion.value;
        if (!version) {
          errorMessage.value = "Versionen stämmer inte längre. Ladda om och försök igen.";
          return;
        }

        const response = await apiPost<SaveResult>(
          `/api/v1/editor/tool-versions/${version.id}/save`,
          {
            entrypoint: entrypointValue,
            source_code: sourceCode.value,
            change_summary: summaryValue,
            expected_parent_version_id: version.id,
          },
        );

        successMessage.value = "Sparat.";
        await navigateAfterSave(response.redirect_url);
        return;
      }

      const response = await apiPost<SaveResult>(
        `/api/v1/editor/tools/${editor.value.tool.id}/draft`,
        {
          entrypoint: entrypointValue,
          source_code: sourceCode.value,
          change_summary: summaryValue,
          derived_from_version_id: editor.value.derived_from_version_id,
        },
      );

      successMessage.value = "Utkast skapat.";
      await navigateAfterSave(response.redirect_url);
    } catch (error: unknown) {
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att spara just nu.";
      }
    } finally {
      isSaving.value = false;
    }
  }

  onMounted(() => {
    void loadEditor();
  });

  watch(
    () => route.fullPath,
    () => {
      void loadEditor();
    },
  );

  return {
    editor,
    entrypoint,
    sourceCode,
    changeSummary,
    isLoading,
    isSaving,
    errorMessage,
    successMessage,
    selectedVersion,
    editorToolId,
    saveButtonLabel,
    hasDirtyChanges,
    loadEditor,
    save,
  };
}
