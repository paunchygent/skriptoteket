/**
 * Document Converter route-session history state.
 *
 * Domain purpose:
 *   Keep teacher-facing recent Document Converter results available inside the
 *   current route session without promising durable history or exposing raw
 *   backend identifiers in the visible UI.
 *
 * Relationships:
 *   - Consumed by `DocumentConverterView.vue`.
 *   - Receives ready/failed outcomes from the project-preview and single-file
 *     route state composables.
 */

import { computed, onScopeDispose, ref } from "vue";

import type { ApiBlobResponse } from "../../../api/client";

export type DocumentConverterHistoryStatus = "ready" | "failed";
export type DocumentConverterHistoryArtifact = {
  id: string;
  filename: string;
  loadPreview?: (() => Promise<ApiBlobResponse | null>) | null;
  download?: (() => Promise<void>) | null;
  save?: (() => Promise<void>) | null;
};

export type DocumentConverterHistoryEntry = {
  id: string;
  filename: string;
  resultTypeLabel: string;
  sourceLabel: string;
  status: DocumentConverterHistoryStatus;
  errorMessage?: string | null;
  artifacts?: DocumentConverterHistoryArtifact[] | null;
  loadPreview?: (() => Promise<ApiBlobResponse | null>) | null;
  download?: (() => Promise<void>) | null;
  save?: (() => Promise<void>) | null;
  retry?: (() => Promise<void>) | null;
};

type UpsertHistoryEntryOptions = {
  select?: boolean;
};

export function useDocumentConverterSessionHistory() {
  const entries = ref<DocumentConverterHistoryEntry[]>([]);
  const activeEntryId = ref<string | null>(null);
  const activeArtifactId = ref<string | null>(null);
  const activePreviewUrl = ref<string | null>(null);
  const activePreviewFilename = ref<string | null>(null);
  const activePreviewContentType = ref<string | null>(null);
  const isLoadingPreview = ref(false);
  const isDownloading = ref(false);
  const isSaving = ref(false);
  const isRetrying = ref(false);
  const actionErrorMessage = ref<string | null>(null);

  const activeEntry = computed(() => {
    if (activeEntryId.value === null) {
      return entries.value[0] ?? null;
    }
    return entries.value.find((entry) => entry.id === activeEntryId.value) ?? entries.value[0] ?? null;
  });
  const activeArtifact = computed(() => {
    const artifacts = activeEntry.value?.artifacts ?? [];
    if (artifacts.length === 0) {
      return null;
    }
    return artifacts.find((artifact) => artifact.id === activeArtifactId.value) ?? artifacts[0] ?? null;
  });
  const artifactOptions = computed(() => {
    return (activeEntry.value?.artifacts ?? []).map((artifact) => ({
      artifactId: artifact.id,
      filename: artifact.filename,
    }));
  });
  const activeArtifactFilename = computed(() => activeArtifact.value?.filename ?? null);

  const canDownloadActiveEntry = computed(() => {
    return Boolean(activeArtifact.value?.download ?? activeEntry.value?.download);
  });
  const canSaveActiveEntry = computed(() => {
    return Boolean(activeArtifact.value?.save ?? activeEntry.value?.save);
  });
  const canRetryActiveEntry = computed(() => Boolean(activeEntry.value?.retry));

  function replacePreviewUrl(nextUrl: string | null): void {
    if (activePreviewUrl.value && activePreviewUrl.value !== nextUrl) {
      URL.revokeObjectURL(activePreviewUrl.value);
    }
    activePreviewUrl.value = nextUrl;
  }

  function upsertEntry(
    entry: DocumentConverterHistoryEntry,
    options: UpsertHistoryEntryOptions = {},
  ): void {
    const withoutExisting = entries.value.filter((item) => item.id !== entry.id);
    entries.value = [entry, ...withoutExisting];
    if (options.select ?? entry.status === "ready") {
      void selectEntry(entry.id);
    }
  }

  async function loadSelectedPreview(): Promise<void> {
    const previewLoader = activeArtifact.value?.loadPreview ?? activeEntry.value?.loadPreview;
    if (!previewLoader) {
      replacePreviewUrl(null);
      activePreviewFilename.value = null;
      activePreviewContentType.value = null;
      return;
    }

    isLoadingPreview.value = true;
    try {
      const response = await previewLoader();
      if (!response) {
        replacePreviewUrl(null);
        activePreviewFilename.value = null;
        activePreviewContentType.value = null;
        return;
      }
      activePreviewFilename.value = response.filename;
      activePreviewContentType.value = response.contentType;
      replacePreviewUrl(URL.createObjectURL(response.blob));
    } catch {
      actionErrorMessage.value = "Det gick inte att visa resultatet igen.";
      replacePreviewUrl(null);
      activePreviewFilename.value = null;
      activePreviewContentType.value = null;
    } finally {
      isLoadingPreview.value = false;
    }
  }

  async function selectEntry(entryId: string): Promise<void> {
    const entry = entries.value.find((item) => item.id === entryId);
    if (!entry) {
      return;
    }
    activeEntryId.value = entry.id;
    activeArtifactId.value = entry.artifacts?.[0]?.id ?? null;
    actionErrorMessage.value = null;
    await loadSelectedPreview();
  }

  async function selectActiveArtifact(artifactId: string): Promise<void> {
    if (!activeEntry.value?.artifacts?.some((artifact) => artifact.id === artifactId)) {
      return;
    }
    activeArtifactId.value = artifactId;
    actionErrorMessage.value = null;
    await loadSelectedPreview();
  }

  async function downloadActiveEntry(): Promise<void> {
    const download = activeArtifact.value?.download ?? activeEntry.value?.download;
    if (!download) {
      return;
    }
    isDownloading.value = true;
    actionErrorMessage.value = null;
    try {
      await download();
    } catch {
      actionErrorMessage.value = "Det gick inte att ladda ned resultatet.";
    } finally {
      isDownloading.value = false;
    }
  }

  async function saveActiveEntry(): Promise<void> {
    const save = activeArtifact.value?.save ?? activeEntry.value?.save;
    if (!save) {
      return;
    }
    isSaving.value = true;
    actionErrorMessage.value = null;
    try {
      await save();
    } catch {
      actionErrorMessage.value = "Det gick inte att spara resultatet.";
    } finally {
      isSaving.value = false;
    }
  }

  async function retryActiveEntry(): Promise<void> {
    const retry = activeEntry.value?.retry;
    if (!retry) {
      return;
    }
    isRetrying.value = true;
    actionErrorMessage.value = null;
    try {
      await retry();
    } catch {
      actionErrorMessage.value = "Det gick inte att försöka igen.";
    } finally {
      isRetrying.value = false;
    }
  }

  onScopeDispose(() => {
    replacePreviewUrl(null);
  });

  return {
    activeEntry,
    activeArtifactFilename,
    activeArtifactId,
    activePreviewContentType,
    activePreviewFilename,
    activePreviewUrl,
    actionErrorMessage,
    artifactOptions,
    canDownloadActiveEntry,
    canRetryActiveEntry,
    canSaveActiveEntry,
    downloadActiveEntry,
    entries,
    isDownloading,
    isLoadingPreview,
    isRetrying,
    isSaving,
    retryActiveEntry,
    saveActiveEntry,
    selectActiveArtifact,
    selectEntry,
    upsertEntry,
  };
}
