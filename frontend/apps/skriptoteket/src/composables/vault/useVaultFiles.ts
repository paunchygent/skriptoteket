import { computed, ref, watch } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";

type VaultFileInfo = components["schemas"]["VaultFileInfo"];
type VaultListSort = components["schemas"]["VaultListSort"];
type VaultListState = components["schemas"]["VaultListState"];
type VaultUsageInfo = components["schemas"]["VaultUsageInfo"];
type VaultFileSourceKind = components["schemas"]["VaultFileSourceKind"];

type ListVaultFilesResult = components["schemas"]["ListVaultFilesResult"];
type SaveVaultFileResult = components["schemas"]["SaveVaultFileResult"];
type DeleteVaultFileResult = components["schemas"]["DeleteVaultFileResult"];
type RestoreVaultFileResult = components["schemas"]["RestoreVaultFileResult"];

type UseVaultFilesOptions = {
  initialState?: VaultListState;
  initialSort?: VaultListSort;
  limit?: number;
};

const DEFAULT_LIMIT = 50;
const RUN_ARTIFACT_SOURCE: VaultFileSourceKind = "run_artifact";

function toSearchQuery(search: string): string | null {
  const trimmed = search.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function parseNextCursor(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function buildVaultListUrl(params: {
  state: VaultListState;
  sort: VaultListSort;
  search: string | null;
  limit: number;
  cursor: number | null;
}): string {
  const query = new URLSearchParams();
  query.set("state", params.state);
  query.set("sort", params.sort);
  query.set("limit", String(params.limit));
  if (params.search !== null) {
    query.set("search", params.search);
  }
  if (params.cursor !== null) {
    query.set("cursor", String(params.cursor));
  }
  return `/api/v1/vault/files?${query.toString()}`;
}

export function useVaultFiles(options: UseVaultFilesOptions = {}) {
  const auth = useAuthStore();

  const state = ref<VaultListState>(options.initialState ?? "active");
  const sort = ref<VaultListSort>(options.initialSort ?? "newest");
  const search = ref<string>("");
  const limit = ref<number>(options.limit ?? DEFAULT_LIMIT);

  const files = ref<VaultFileInfo[]>([]);
  const usage = ref<VaultUsageInfo | null>(null);
  const nextCursor = ref<number | null>(null);

  const isLoading = ref(false);
  const errorMessage = ref<string | null>(null);

  const canLoadMore = computed(() => nextCursor.value !== null);

  async function fetchPage(cursor: number | null, mode: "replace" | "append"): Promise<void> {
    if (!auth.bootstrapped || !auth.isAuthenticated) {
      files.value = [];
      usage.value = null;
      nextCursor.value = null;
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;

    try {
      const response = await apiGet<ListVaultFilesResult>(
        buildVaultListUrl({
          state: state.value,
          sort: sort.value,
          search: toSearchQuery(search.value),
          limit: limit.value,
          cursor,
        }),
      );

      const responseFiles = response.files ?? [];
      files.value = mode === "append" ? [...files.value, ...responseFiles] : responseFiles;
      usage.value = response.usage ?? null;
      nextCursor.value = parseNextCursor(response.next_cursor);
    } catch (error: unknown) {
      files.value = mode === "append" ? files.value : [];
      nextCursor.value = null;

      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ladda valvet.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function refresh(): Promise<void> {
    nextCursor.value = null;
    await fetchPage(null, "replace");
  }

  async function loadMore(): Promise<void> {
    if (nextCursor.value === null) return;
    await fetchPage(nextCursor.value, "append");
  }

  async function saveFromRunArtifact(params: {
    runId: string;
    artifactId: string;
    name?: string | null;
  }): Promise<VaultFileInfo> {
    const payload = {
      source_kind: RUN_ARTIFACT_SOURCE,
      run_id: params.runId,
      artifact_id: params.artifactId,
      name: params.name ?? null,
    };

    const result = await apiFetch<SaveVaultFileResult>("/api/v1/vault/files", {
      method: "POST",
      body: payload,
    });
    return result.file;
  }

  async function deleteFile(fileId: string): Promise<VaultFileInfo> {
    const result = await apiFetch<DeleteVaultFileResult>(
      `/api/v1/vault/files/${encodeURIComponent(fileId)}/delete`,
      { method: "POST" },
    );
    return result.file;
  }

  async function restoreFile(fileId: string): Promise<VaultFileInfo> {
    const result = await apiFetch<RestoreVaultFileResult>(
      `/api/v1/vault/files/${encodeURIComponent(fileId)}/restore`,
      { method: "POST" },
    );
    return result.file;
  }

  watch([state, sort], () => {
    void refresh();
  });

  return {
    state,
    sort,
    search,
    limit,
    files,
    usage,
    nextCursor,
    canLoadMore,
    isLoading,
    errorMessage,
    refresh,
    loadMore,
    saveFromRunArtifact,
    deleteFile,
    restoreFile,
  };
}
