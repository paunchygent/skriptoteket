import { computed, ref, watch, type Ref } from "vue";

import { apiGet } from "../../api/client";

export type SessionFilesMode = "none" | "reuse" | "clear";
export type SessionFileInfo = { name: string; bytes: number };

type SessionFilesResponse = {
  tool_id: string;
  context: string;
  files: SessionFileInfo[];
};

type FileFieldConstraints = { min: number; max: number } | null;

type UseToolSessionFilesOptions = {
  selectedFiles: Readonly<Ref<File[]>>;
  fileField: Readonly<Ref<FileFieldConstraints>>;
  fileError: Readonly<Ref<string | null>>;
  isSubmitting: Readonly<Ref<boolean>>;
  isRunning: Readonly<Ref<boolean>>;
};

const DEFAULT_SESSION_CONTEXT = "default";

export function useToolSessionFiles(options: UseToolSessionFilesOptions) {
  const sessionFiles = ref<SessionFileInfo[]>([]);
  const sessionFilesMode = ref<SessionFilesMode>("none");

  const hasFiles = computed(() => options.selectedFiles.value.length > 0);
  const hasSessionFiles = computed(() => sessionFiles.value.length > 0);

  const effectiveSessionFilesMode = computed<SessionFilesMode>(() => {
    if (hasFiles.value) return "none";
    if (sessionFilesMode.value === "reuse" && !hasSessionFiles.value) return "none";
    return sessionFilesMode.value;
  });

  const effectiveFileError = computed<string | null>(() => {
    const baseError = options.fileError.value;
    const fileField = options.fileField.value;

    if (!fileField) {
      if (effectiveSessionFilesMode.value === "reuse" && hasSessionFiles.value) {
        return "Det här verktyget tar inte emot filer.";
      }
      return baseError;
    }

    if (hasFiles.value) return baseError;
    if (effectiveSessionFilesMode.value !== "reuse") return baseError;

    const count = sessionFiles.value.length;
    const min = fileField.min;
    const max = fileField.max;

    if (count < min) {
      return min === 1 ? "Välj minst en fil." : `Välj minst ${min} filer.`;
    }
    if (count > max) {
      return max === 1 ? "Du kan välja max 1 fil." : `Du kan välja max ${max} filer.`;
    }
    return null;
  });

  const canReuseSessionFiles = computed(() => {
    return (
      !options.isSubmitting.value &&
      !options.isRunning.value &&
      !hasFiles.value &&
      hasSessionFiles.value &&
      options.fileField.value !== null
    );
  });

  const canClearSessionFiles = computed(() => {
    return (
      !options.isSubmitting.value &&
      !options.isRunning.value &&
      !hasFiles.value &&
      hasSessionFiles.value
    );
  });

  const sessionFilesHelperText = computed(() => {
    if (hasFiles.value) {
      return "Väljer du filer används de istället för sparade.";
    }
    return null;
  });

  async function fetchSessionFiles(toolId: string): Promise<void> {
    try {
      const response = await apiGet<SessionFilesResponse>(
        `/api/v1/tools/${encodeURIComponent(toolId)}/session-files?context=${DEFAULT_SESSION_CONTEXT}`,
      );
      sessionFiles.value = response.files ?? [];
    } catch {
      sessionFiles.value = [];
    }
  }

  function resetSessionFiles(): void {
    sessionFiles.value = [];
    sessionFilesMode.value = "none";
  }

  watch(
    () => options.selectedFiles.value.length,
    (count) => {
      if (count > 0 && sessionFilesMode.value !== "none") {
        sessionFilesMode.value = "none";
      }
    },
  );

  watch(
    () => sessionFiles.value.length,
    (count) => {
      if (count === 0 && sessionFilesMode.value === "reuse") {
        sessionFilesMode.value = "none";
      }
    },
  );

  return {
    sessionFiles,
    sessionFilesMode,
    hasSessionFiles,
    effectiveSessionFilesMode,
    effectiveFileError,
    sessionFilesHelperText,
    canReuseSessionFiles,
    canClearSessionFiles,
    fetchSessionFiles,
    resetSessionFiles,
  };
}
