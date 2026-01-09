import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { editorBaseRouteKey } from "./editorRouteKey";

type UseScriptEditorDrawersOptions = {
  route: RouteLocationNormalizedLoaded;
  router: Router;
  confirmDiscardChanges: (message: string) => boolean;
};

const HISTORY_SWITCH_MESSAGE = "Du har osparade ändringar. Vill du byta version?";

export function useScriptEditorDrawers({
  route,
  router,
  confirmDiscardChanges,
}: UseScriptEditorDrawersOptions) {
  const isHistoryDrawerOpen = ref(false);
  const isChatDrawerOpen = ref(true);
  const isChatCollapsed = ref(false);

  function toggleHistoryDrawer(): void {
    isHistoryDrawerOpen.value = !isHistoryDrawerOpen.value;
  }

  function closeDrawer(): void {
    if (isHistoryDrawerOpen.value) {
      isHistoryDrawerOpen.value = false;
      return;
    }
    if (isChatDrawerOpen.value) {
      isChatCollapsed.value = true;
    }
  }

  function toggleChatCollapsed(): void {
    isChatCollapsed.value = !isChatCollapsed.value;
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
  });

  onBeforeUnmount(() => {
    window.removeEventListener("keydown", handleKeydown);
  });

  watch(
    () => editorBaseRouteKey(route),
    () => {
      isChatDrawerOpen.value = true;
      isChatCollapsed.value = false;
      isHistoryDrawerOpen.value = false;
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
