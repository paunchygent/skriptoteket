import { ref, watch, type Ref } from "vue";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import type { EditorCompareTarget } from "./useEditorCompareState";
import {
  virtualFileTextFromEditorBoot,
  virtualFileTextFromEditorFields,
  type EditorVirtualFileTextFields,
  type VirtualFileTextMap,
} from "./virtualFiles";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];

export type WorkingCopyProvider = () => Promise<EditorVirtualFileTextFields | null>;

export function useEditorCompareData(
  compareTarget: Readonly<Ref<EditorCompareTarget | null>>,
  options: { workingCopyProvider?: WorkingCopyProvider } = {},
) {
  const compareEditor = ref<EditorBootResponse | null>(null);
  const compareFiles = ref<VirtualFileTextMap | null>(null);
  const isLoading = ref(false);
  const errorMessage = ref<string | null>(null);

  let requestCounter = 0;

  watch(
    compareTarget,
    async (target) => {
      requestCounter += 1;
      const requestId = requestCounter;

      compareEditor.value = null;
      compareFiles.value = null;
      errorMessage.value = null;

      if (!target) {
        isLoading.value = false;
        return;
      }

      if (target.kind === "working") {
        const provider = options.workingCopyProvider;
        if (!provider) {
          isLoading.value = false;
          errorMessage.value = "Det finns inget lokalt arbetsexemplar att diffa.";
          return;
        }

        isLoading.value = true;
        try {
          const snapshot = await provider();
          if (requestId !== requestCounter) return;

          if (!snapshot) {
            compareFiles.value = null;
            errorMessage.value = "Det finns inget lokalt arbetsexemplar att diffa.";
          } else {
            compareFiles.value = virtualFileTextFromEditorFields(snapshot);
          }
        } catch {
          if (requestId !== requestCounter) return;
          compareFiles.value = null;
          errorMessage.value = "Det gick inte att ladda lokalt arbetsexemplar.";
        } finally {
          if (requestId === requestCounter) {
            isLoading.value = false;
          }
        }
        return;
      }

      isLoading.value = true;
      try {
        const response = await apiGet<EditorBootResponse>(
          `/api/v1/editor/tool-versions/${encodeURIComponent(target.versionId)}`,
        );
        if (requestId !== requestCounter) return;
        compareEditor.value = response;
        compareFiles.value = virtualFileTextFromEditorBoot(response);
      } catch (error: unknown) {
        if (requestId !== requestCounter) return;

        compareEditor.value = null;
        compareFiles.value = null;
        if (isApiError(error)) {
          if (error.status === 403) {
            errorMessage.value =
              "Du saknar behörighet att se den här versionen, så den kan inte diffas.";
          } else if (error.status === 404) {
            errorMessage.value = "Versionen hittades inte, så den kan inte diffas.";
          } else {
            errorMessage.value = error.message;
          }
        } else if (error instanceof Error) {
          errorMessage.value = error.message;
        } else {
          errorMessage.value = "Det gick inte att ladda diffversionen.";
        }
      } finally {
        if (requestId === requestCounter) {
          isLoading.value = false;
        }
      }
    },
    { immediate: true },
  );

  return {
    compareEditor,
    compareFiles,
    isLoading,
    errorMessage,
  };
}
