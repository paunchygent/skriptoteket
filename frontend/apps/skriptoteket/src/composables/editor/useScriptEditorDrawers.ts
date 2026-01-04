import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

type DrawerKey = "history" | "metadata" | "maintainers" | "instructions";

type UseScriptEditorDrawersOptions = {
  route: RouteLocationNormalizedLoaded;
  router: Router;
  editorToolId: Readonly<Ref<string>>;
  canEditTaxonomy: Readonly<Ref<boolean>>;
  canEditMaintainers: Readonly<Ref<boolean>>;
  loadMaintainers: (toolId: string) => Promise<void>;
  confirmDiscardChanges: (message: string) => boolean;
};

const HISTORY_SWITCH_MESSAGE = "Du har osparade ändringar. Vill du byta version?";

export function useScriptEditorDrawers({
  route,
  router,
  editorToolId,
  canEditTaxonomy,
  canEditMaintainers,
  loadMaintainers,
  confirmDiscardChanges,
}: UseScriptEditorDrawersOptions) {
  const activeDrawer = ref<DrawerKey | null>(null);

  const isHistoryDrawerOpen = computed(() => activeDrawer.value === "history");
  const isMetadataDrawerOpen = computed(() => activeDrawer.value === "metadata");
  const isMaintainersDrawerOpen = computed(() => activeDrawer.value === "maintainers");
  const isInstructionsDrawerOpen = computed(() => activeDrawer.value === "instructions");
  const isDrawerOpen = computed(() => activeDrawer.value !== null);

  function toggleHistoryDrawer(): void {
    activeDrawer.value = activeDrawer.value === "history" ? null : "history";
  }

  function toggleMetadataDrawer(): void {
    if (!canEditTaxonomy.value) return;
    activeDrawer.value = activeDrawer.value === "metadata" ? null : "metadata";
  }

  function toggleMaintainersDrawer(): void {
    if (!canEditMaintainers.value) return;

    const next = activeDrawer.value === "maintainers" ? null : "maintainers";
    activeDrawer.value = next;

    if (next === "maintainers" && editorToolId.value) {
      void loadMaintainers(editorToolId.value);
    }
  }

  function toggleInstructionsDrawer(): void {
    activeDrawer.value = activeDrawer.value === "instructions" ? null : "instructions";
  }

  function closeDrawer(): void {
    activeDrawer.value = null;
  }

  function selectHistoryVersion(versionId: string): void {
    if (!confirmDiscardChanges(HISTORY_SWITCH_MESSAGE)) {
      return;
    }

    void router.replace({
      query: {
        ...route.query,
        version: versionId,
      },
    });
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape" && isDrawerOpen.value) {
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
    () => route.fullPath,
    () => {
      if (activeDrawer.value && activeDrawer.value !== "history") {
        closeDrawer();
      }
    },
  );

  return {
    activeDrawer,
    isDrawerOpen,
    isHistoryDrawerOpen,
    isMetadataDrawerOpen,
    isMaintainersDrawerOpen,
    isInstructionsDrawerOpen,
    toggleHistoryDrawer,
    toggleMetadataDrawer,
    toggleMaintainersDrawer,
    toggleInstructionsDrawer,
    closeDrawer,
    selectHistoryVersion,
  };
}
