import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { editorBaseRouteKey } from "./editorRouteKey";

type UseScriptEditorDrawersOptions = {
  route: RouteLocationNormalizedLoaded;
  router: Router;
  confirmDiscardChanges: (message: string) => boolean;
};

const HISTORY_SWITCH_MESSAGE = "Du har osparade ändringar. Vill du byta version?";
const CHAT_COLUMN_BREAKPOINT_QUERY = "(min-width: 1024px)";

export function useScriptEditorDrawers({
  route,
  router,
  confirmDiscardChanges,
}: UseScriptEditorDrawersOptions) {
  const isHistoryDrawerOpen = ref(false);
  const isChatDrawerOpen = ref(true);
  const isChatCollapsed = ref(false);
  const didAutoCollapseForNarrowViewport = ref(false);
  let viewportQuery: MediaQueryList | null = null;

  function toggleHistoryDrawer(): void {
    isHistoryDrawerOpen.value = !isHistoryDrawerOpen.value;
  }

  function closeDrawer(): void {
    if (isHistoryDrawerOpen.value) {
      isHistoryDrawerOpen.value = false;
      return;
    }
    if (isChatDrawerOpen.value) {
      didAutoCollapseForNarrowViewport.value = false;
      isChatCollapsed.value = true;
    }
  }

  function toggleChatCollapsed(): void {
    didAutoCollapseForNarrowViewport.value = false;
    isChatCollapsed.value = !isChatCollapsed.value;
  }

  function syncChatCollapsedForViewport(): void {
    if (typeof window === "undefined") {
      return;
    }

    if (!viewportQuery) {
      viewportQuery = window.matchMedia(CHAT_COLUMN_BREAKPOINT_QUERY);
    }

    if (!viewportQuery.matches) {
      if (!isChatCollapsed.value) {
        didAutoCollapseForNarrowViewport.value = true;
        isChatCollapsed.value = true;
      }
      return;
    }

    if (didAutoCollapseForNarrowViewport.value) {
      didAutoCollapseForNarrowViewport.value = false;
      isChatCollapsed.value = false;
    }
  }

  function handleViewportQueryChange(): void {
    syncChatCollapsedForViewport();
  }

  function selectHistoryVersion(versionId: string): void {
    if (!confirmDiscardChanges(HISTORY_SWITCH_MESSAGE)) {
      return;
    }

    const pathVersionId = typeof route.params.versionId === "string" ? route.params.versionId : "";
    if (pathVersionId) {
      const nextQuery = { ...route.query } as Record<string, string | string[] | null | undefined>;
      delete nextQuery.version;
      void router.replace({
        path: `/admin/tool-versions/${encodeURIComponent(versionId)}`,
        query: nextQuery,
      });
      isHistoryDrawerOpen.value = false;
      return;
    }

    void router.replace({
      query: {
        ...route.query,
        version: versionId,
      },
    });
    isHistoryDrawerOpen.value = false;
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape" && (isHistoryDrawerOpen.value || isChatDrawerOpen.value)) {
      closeDrawer();
    }
  }

  onMounted(() => {
    window.addEventListener("keydown", handleKeydown);
    viewportQuery = window.matchMedia(CHAT_COLUMN_BREAKPOINT_QUERY);
    syncChatCollapsedForViewport();
    viewportQuery.addEventListener?.("change", handleViewportQueryChange);
    viewportQuery.addListener?.(handleViewportQueryChange);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("keydown", handleKeydown);
    viewportQuery?.removeEventListener?.("change", handleViewportQueryChange);
    viewportQuery?.removeListener?.(handleViewportQueryChange);
  });

  watch(
    () => editorBaseRouteKey(route),
    () => {
      isChatDrawerOpen.value = true;
      isChatCollapsed.value = false;
      isHistoryDrawerOpen.value = false;
      syncChatCollapsedForViewport();
    },
  );

  return {
    isHistoryDrawerOpen,
    isChatDrawerOpen,
    isChatCollapsed,
    toggleHistoryDrawer,
    toggleChatCollapsed,
    closeDrawer,
    selectHistoryVersion,
  };
}
