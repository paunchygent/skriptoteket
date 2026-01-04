import { computed, ref, watch, type Ref } from "vue";

import { apiGet } from "../../api/client";

export type SessionFilesMode = "none" | "reuse" | "clear";
export type SessionFileInfo = { name: string; bytes: number };

type SandboxSessionFilesResponse = {
  tool_id: string;
  version_id: string;
  snapshot_id: string;
  files: SessionFileInfo[];
};

type FileFieldConstraints = { min: number; max: number };

type UseEditorSandboxSessionFilesOptions = {
  versionId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  isRunning: Readonly<Ref<boolean>>;
  isSubmitting: Readonly<Ref<boolean>>;
  selectedFiles: Ref<File[]>;
  fileError: Readonly<Ref<string | null>>;
  fileField: Readonly<Ref<FileFieldConstraints | null>>;
};

export function useEditorSandboxSessionFiles({
  versionId,
  isReadOnly,
  isRunning,
  isSubmitting,
  selectedFiles,
  fileError,
  fileField,
}: UseEditorSandboxSessionFilesOptions) {
  const sessionFiles = ref<SessionFileInfo[]>([]);
  const sessionFilesMode = ref<SessionFilesMode>("none");
  const sessionFilesSnapshotId = ref<string | null>(null);

  const hasFiles = computed(() => selectedFiles.value.length > 0);
  const hasSessionFiles = computed(() => sessionFiles.value.length > 0);

  const effectiveSessionFilesMode = computed<SessionFilesMode>(() => {
    if (hasFiles.value) return "none";
    if (sessionFilesMode.value === "reuse" && !hasSessionFiles.value) return "none";
    return sessionFilesMode.value;
  });

  const effectiveFileError = computed<string | null>(() => {
    const baseError = fileError.value;
    const field = fileField.value;
    if (!field) {
      if (effectiveSessionFilesMode.value === "reuse" && hasSessionFiles.value) {
        return "Det här verktyget tar inte emot filer.";
      }
      return baseError;
    }
    if (hasFiles.value) return baseError;
    if (effectiveSessionFilesMode.value !== "reuse") return baseError;

    const count = sessionFiles.value.length;
    const min = field.min;
    const max = field.max;

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
      !isReadOnly.value &&
      !isRunning.value &&
      !isSubmitting.value &&
      !hasFiles.value &&
      hasSessionFiles.value &&
      fileField.value !== null
    );
  });
  const canClearSessionFiles = computed(() => {
    return (
      !isReadOnly.value &&
      !isRunning.value &&
      !isSubmitting.value &&
      !hasFiles.value &&
      hasSessionFiles.value
    );
  });
  const helperText = computed(() => {
    if (isReadOnly.value) {
      return "Du saknar redigeringslåset. Sparade filer kan inte användas.";
    }
    if (hasFiles.value) {
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

  watch(
    () => selectedFiles.value.length,
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
    effectiveFileError,
    canReuseSessionFiles,
    canClearSessionFiles,
    helperText,
    fetchSessionFiles,
  };
}
