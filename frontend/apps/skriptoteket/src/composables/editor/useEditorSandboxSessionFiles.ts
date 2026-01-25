import { computed, ref, watch, type Ref } from "vue";

import { apiFetch, apiGet } from "../../api/client";
import type { FileFieldSelection, ToolFileFieldSpec } from "../tools/useToolInputs";

export type SessionFilesMode = "none" | "reuse" | "clear";
export type SessionFileInfo = { name: string; bytes: number; field?: string | null };

type SandboxSessionFilesResponse = {
  tool_id: string;
  version_id: string;
  snapshot_id: string;
  files: SessionFileInfo[];
};

type DeleteSandboxSessionFilesResponse = {
  tool_id: string;
  version_id: string;
  snapshot_id: string;
  deleted: number;
};

type UseEditorSandboxSessionFilesOptions = {
  versionId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  isRunning: Readonly<Ref<boolean>>;
  isSubmitting: Readonly<Ref<boolean>>;
  fileFields: Readonly<Ref<ToolFileFieldSpec[]>>;
  fileSelections: Readonly<Ref<Record<string, FileFieldSelection>>>;
  fileErrors: Readonly<Ref<Record<string, string | null>>>;
};

export function useEditorSandboxSessionFiles({
  versionId,
  isReadOnly,
  isRunning,
  isSubmitting,
  fileFields,
  fileSelections,
  fileErrors,
}: UseEditorSandboxSessionFilesOptions) {
  const sessionFiles = ref<SessionFileInfo[]>([]);
  const sessionFilesMode = ref<SessionFilesMode>("none");
  const sessionFilesSnapshotId = ref<string | null>(null);

  const hasSelections = computed(() => {
    return Object.values(fileSelections.value).some(
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
      return fileErrors.value;
    }

    const errors: Record<string, string | null> = {};
    for (const field of fileFields.value) {
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
      !isReadOnly.value &&
      !isRunning.value &&
      !isSubmitting.value &&
      !hasSelections.value &&
      hasSessionFiles.value &&
      fileFields.value.length > 0
    );
  });

  const canClearSessionFiles = computed(() => {
    return (
      !isReadOnly.value &&
      !isRunning.value &&
      !isSubmitting.value &&
      !hasSelections.value &&
      hasSessionFiles.value
    );
  });

  const helperText = computed(() => {
    if (isReadOnly.value) {
      return "Du saknar redigeringslåset. Sparade filer kan inte användas.";
    }
    if (hasSelections.value) {
      return "Väljer du filer används de istället för sparade.";
    }
    return null;
  });

  async function fetchSessionFiles(snapshotId: string): Promise<void> {
    try {
      const response = await apiGet<SandboxSessionFilesResponse>(
        `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}` +
          `/session-files?snapshot_id=${encodeURIComponent(snapshotId)}`,
      );
      sessionFiles.value = response.files;
    } catch {
      sessionFiles.value = [];
    }
  }

  async function deleteSessionFiles(snapshotId: string, names: string[]): Promise<void> {
    if (!snapshotId || names.length === 0) return;
    await apiFetch<DeleteSandboxSessionFilesResponse>(
      `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}` +
        `/session-files/delete?snapshot_id=${encodeURIComponent(snapshotId)}`,
      {
        method: "POST",
        body: { names },
      },
    );
    await fetchSessionFiles(snapshotId);
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

  watch(
    () => versionId.value,
    () => {
      sessionFiles.value = [];
      sessionFilesSnapshotId.value = null;
      sessionFilesMode.value = "none";
    },
  );

  return {
    sessionFiles,
    sessionFilesMode,
    sessionFilesSnapshotId,
    effectiveSessionFilesMode,
    effectiveFileErrors,
    canReuseSessionFiles,
    canClearSessionFiles,
    helperText,
    fetchSessionFiles,
    deleteSessionFiles,
  };
}
