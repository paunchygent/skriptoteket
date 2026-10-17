import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";
import { useAdminToolsIndex } from "../admin/useAdminToolsIndex";
import { searchTools } from "../tools/toolSearch";
import {
  getLastRecentEditorToolId,
  listRecentEditorTools,
  removeRecentEditorTool,
} from "./editorRecentTools";

type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type MyToolItem = components["schemas"]["MyToolItem"];
type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type SearchCandidate = { id: string; title: string; slug: string };

export function useEditorHub() {
  const auth = useAuthStore();
  const route = useRoute();
  const router = useRouter();
  const {
    tools: adminTools,
    isLoading: isAdminToolsLoading,
    error: adminToolsError,
    ensureLoaded: ensureAdminToolsLoaded,
  } = useAdminToolsIndex();

  const isForcedPick = computed(() => route.query.pick === "1");
  const canCreateTool = computed(() => auth.hasAtLeastRole("admin"));
  const searchQuery = ref("");
  const recentTools = ref(listRecentEditorTools(auth.user?.id ?? ""));
  const myTools = ref<MyToolItem[]>([]);
  const isLoadingMyTools = ref(false);
  const myToolsError = ref<string | null>(null);
  const redirectError = ref<string | null>(null);
  const isRedirecting = ref(false);
  const searchRef = ref<HTMLElement | null>(null);
  const isSearchOpen = ref(false);

  function refreshRecents(): void {
    recentTools.value = listRecentEditorTools(auth.user?.id ?? "");
  }

  const normalizedSearch = computed(() => searchQuery.value.trim().toLowerCase());
  const recencyByToolId = computed(() => {
    const entries = recentTools.value.map((tool) => [tool.toolId, tool.openedAt] as const);
    return new Map(entries);
  });

  const sortedMyTools = computed(() => {
    const tools = [...myTools.value];
    const recency = recencyByToolId.value;
    tools.sort((a, b) => {
      const aRecency = recency.get(a.id) ?? null;
      const bRecency = recency.get(b.id) ?? null;
      if (aRecency !== null && bRecency !== null) return bRecency - aRecency;
      if (aRecency !== null) return -1;
      if (bRecency !== null) return 1;
      return a.title.localeCompare(b.title, "sv-SE");
    });
    return tools;
  });

  const searchCandidates = computed<SearchCandidate[]>(() => {
    if (canCreateTool.value) {
      const allTools = adminTools.value ?? [];
      return allTools.map((tool) => ({ id: tool.id, title: tool.title, slug: tool.slug }));
    }
    return myTools.value.map((tool) => ({ id: tool.id, title: tool.title, slug: tool.slug }));
  });

  const toolSearch = computed(() => searchTools({
    candidates: searchCandidates.value,
    query: searchQuery.value,
    limit: 5,
    locale: "sv-SE",
    recencyById: recencyByToolId.value,
  }));

  const searchErrorMessage = computed(() => {
    if (canCreateTool.value) return adminToolsError.value;
    return myToolsError.value;
  });
  const isSearchLoading = computed(() => {
    if (!normalizedSearch.value) return false;
    if (canCreateTool.value) return isAdminToolsLoading.value;
    return isLoadingMyTools.value;
  });
  const shouldShowSearchOverflow = computed(() => {
    if (!toolSearch.value.normalizedQuery) return false;
    if (searchErrorMessage.value) return false;
    if (isSearchLoading.value) return false;
    return toolSearch.value.totalMatches > toolSearch.value.results.length;
  });

  async function loadMyTools(): Promise<void> {
    isLoadingMyTools.value = true;
    myToolsError.value = null;
    try {
      const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
      myTools.value = response.tools;
    } catch (error: unknown) {
      if (isApiError(error)) {
        myToolsError.value = error.message;
      } else if (error instanceof Error) {
        myToolsError.value = error.message;
      } else {
        myToolsError.value = "Det gick inte att ladda verktyg.";
      }
    } finally {
      isLoadingMyTools.value = false;
    }
  }

  function closeSearch(): void {
    isSearchOpen.value = false;
    searchQuery.value = "";
  }

  async function openTool(toolId: string): Promise<void> {
    if (!toolId) return;
    closeSearch();
    await router.push(`/admin/tools/${toolId}`);
  }

  function handleDocumentClick(event: MouseEvent): void {
    const target = event.target as Node | null;
    if (!target) return;
    if (isSearchOpen.value && searchRef.value && !searchRef.value.contains(target)) {
      closeSearch();
    }
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key !== "Escape") return;
    if (isSearchOpen.value) {
      event.preventDefault();
      closeSearch();
    }
  }

  async function tryRedirectToLastTool(): Promise<boolean> {
    const userId = auth.user?.id ?? "";
    if (!userId) return false;
    const lastToolId = getLastRecentEditorToolId(userId);
    if (!lastToolId) return false;

    isRedirecting.value = true;
    redirectError.value = null;
    try {
      await apiGet<EditorBootResponse>(`/api/v1/editor/tools/${encodeURIComponent(lastToolId)}`);
      await router.replace(`/admin/tools/${lastToolId}`);
      return true;
    } catch (error: unknown) {
      if (isApiError(error) && (error.status === 403 || error.status === 404)) {
        removeRecentEditorTool(userId, lastToolId);
        refreshRecents();
        redirectError.value = "Det senaste verktyget gick inte att öppna längre. Välj ett annat.";
        return false;
      }
      redirectError.value =
        error instanceof Error ? error.message : "Det gick inte att öppna det senaste verktyget.";
      return false;
    } finally {
      isRedirecting.value = false;
    }
  }

  onMounted(() => {
    document.addEventListener("click", handleDocumentClick);
    document.addEventListener("keydown", handleKeydown);
    void (async () => {
      await auth.bootstrap();
      refreshRecents();
      if (!isForcedPick.value) {
        const didRedirect = await tryRedirectToLastTool();
        if (didRedirect) return;
      }
      await loadMyTools();
    })();
  });

  onBeforeUnmount(() => {
    document.removeEventListener("click", handleDocumentClick);
    document.removeEventListener("keydown", handleKeydown);
  });

  watch(
    () => normalizedSearch.value,
    async (value) => {
      if (!value) {
        isSearchOpen.value = false;
        return;
      }
      if (!canCreateTool.value) return;
      await ensureAdminToolsLoaded();
    },
  );

  return {
    canCreateTool,
    searchQuery,
    searchRef,
    isSearchOpen,
    toolSearch,
    searchErrorMessage,
    isSearchLoading,
    shouldShowSearchOverflow,
    recentTools,
    sortedMyTools,
    isLoadingMyTools,
    myToolsError,
    redirectError,
    isRedirecting,
    openTool,
  };
}
