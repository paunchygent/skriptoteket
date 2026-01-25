import { computed, ref, watch, type Ref } from "vue";

import { apiFetch, apiGet } from "../../api/client";
import type { FileFieldSelection, ToolFileFieldSpec } from "./useToolInputs";

type SessionFilesMode = "none" | "reuse" | "clear";
export type SessionFileInfo = { name: string; bytes: number; field?: string | null };

const DEFAULT_SESSION_CONTEXT = "default";

type SessionFilesResponse = {
  tool_id: string;
  context: string;
  files: SessionFileInfo[];
};

type DeleteSessionFilesResponse = {
  tool_id: string;
  context: string;
  deleted: number;
};

type UseToolSessionFilesOptions = {
  fileFields: Readonly<Ref<ToolFileFieldSpec[]>>;
  fileSelections: Readonly<Ref<Record<string, FileFieldSelection>>>;
  fileErrors: Readonly<Ref<Record<string, string | null>>>;
  isSubmitting: Readonly<Ref<boolean>>;
  isRunning: Readonly<Ref<boolean>>;
};

export function useToolSessionFiles(options: UseToolSessionFilesOptions) {
  const sessionFiles = ref<SessionFileInfo[]>([]);
  const sessionFilesMode = ref<SessionFilesMode>("none");

  const hasSelections = computed(() => {
    return Object.values(options.fileSelections.value).some(
      (selection) => selection.uploads.length > 0 || selection.refs.length > 0,
    );
  });

  const hasSessionFiles = computed(() => sessionFiles.value.length > 0);

  const sessionCountsByField = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    for (const file of sessionFiles.value) {
      if (!file.field) continue;
      counts[file.field] = (counts[file.field] ?? 0) + 1;
    }
    return counts;
  });

  const effectiveSessionFilesMode = computed<SessionFilesMode>(() => {
    if (hasSelections.value) return "none";
    if (sessionFilesMode.value === "reuse" && !hasSessionFiles.value) return "none";
    return sessionFilesMode.value;
  });

  const effectiveFileErrors = computed<Record<string, string | null>>(() => {
    if (effectiveSessionFilesMode.value !== "reuse") {
      return options.fileErrors.value;
    }

    const errors: Record<string, string | null> = {};
    for (const field of options.fileFields.value) {
      const count = sessionCountsByField.value[field.name] ?? 0;
      if (count < field.min) {
        errors[field.name] = field.min === 1 ? "Välj minst en fil." : `Välj minst ${field.min} filer.`;
        continue;
      }
      if (count > field.max) {
        errors[field.name] = field.max === 1 ? "Du kan välja max 1 fil." : `Du kan välja max ${field.max} filer.`;
        continue;
      }
      errors[field.name] = null;
    }
    return errors;
  });

  const canReuseSessionFiles = computed(() => {
    return (
      !options.isSubmitting.value &&
      !options.isRunning.value &&
      !hasSelections.value &&
      hasSessionFiles.value &&
      options.fileFields.value.length > 0
    );
  });

  const canClearSessionFiles = computed(() => {
    return (
      !options.isSubmitting.value &&
      !options.isRunning.value &&
      !hasSelections.value &&
      hasSessionFiles.value
    );
  });

  const sessionFilesHelperText = computed(() => {
    if (hasSelections.value) {
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

  async function deleteSessionFiles(toolId: string, names: string[]): Promise<void> {
    if (!toolId || names.length === 0) return;
    await apiFetch<DeleteSessionFilesResponse>(
      `/api/v1/tools/${encodeURIComponent(toolId)}/session-files/delete` +
        `?context=${encodeURIComponent(DEFAULT_SESSION_CONTEXT)}`,
      {
        method: "POST",
        body: { names },
      },
    );
    await fetchSessionFiles(toolId);
  }

  function resetSessionFiles(): void {
    sessionFiles.value = [];
    sessionFilesMode.value = "none";
  }

  watch(
    () => hasSelections.value,
    (hasAny) => {
      if (hasAny && sessionFilesMode.value !== "none") {
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
    effectiveFileErrors,
    sessionFilesHelperText,
    canReuseSessionFiles,
    canClearSessionFiles,
    fetchSessionFiles,
    deleteSessionFiles,
    resetSessionFiles,
  };
}
