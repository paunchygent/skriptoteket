import { computed, ref, watch, type Ref } from "vue";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import type { EditorCompareTarget } from "./useEditorCompareState";
import { virtualFileTextFromEditorBoot } from "./virtualFiles";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];

export function useEditorCompareData(compareTarget: Readonly<Ref<EditorCompareTarget | null>>) {
  const compareEditor = ref<EditorBootResponse | null>(null);
  const isLoading = ref(false);
  const errorMessage = ref<string | null>(null);

  let requestCounter = 0;

  watch(
    compareTarget,
    async (target) => {
      requestCounter += 1;
      const requestId = requestCounter;

      compareEditor.value = null;
      errorMessage.value = null;

      if (!target) {
        isLoading.value = false;
        return;
      }

      if (target.kind === "working") {
        isLoading.value = false;
        errorMessage.value = "Jämförelse mot lokalt arbetsexemplar stöds inte ännu (ST-14-30).";
        return;
      }

      isLoading.value = true;
      try {
        const response = await apiGet<EditorBootResponse>(
          `/api/v1/editor/tool-versions/${encodeURIComponent(target.versionId)}`,
        );
        if (requestId !== requestCounter) return;
        compareEditor.value = response;
      } catch (error: unknown) {
        if (requestId !== requestCounter) return;

        compareEditor.value = null;
        if (isApiError(error)) {
          if (error.status === 403) {
            errorMessage.value =
              "Du saknar behörighet att se den här versionen, så den kan inte jämföras.";
          } else if (error.status === 404) {
            errorMessage.value = "Versionen hittades inte, så den kan inte jämföras.";
          } else {
            errorMessage.value = error.message;
          }
        } else if (error instanceof Error) {
          errorMessage.value = error.message;
        } else {
          errorMessage.value = "Det gick inte att ladda jämförelseversionen.";
        }
      } finally {
        if (requestId === requestCounter) {
          isLoading.value = false;
        }
      }
    },
    { immediate: true },
  );

  const compareFiles = computed(() => {
    if (!compareEditor.value) return null;
    return virtualFileTextFromEditorBoot(compareEditor.value);
  });

  return {
    compareEditor,
    compareFiles,
    isLoading,
    errorMessage,
  };
}
