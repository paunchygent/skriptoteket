import { computed, ref, watch, type Ref } from "vue";

import type { UiNotifier } from "../notify";
import type { EditorWorkspaceMode } from "./useScriptEditorCompareMode";
import { useToolMaintainers } from "./useToolMaintainers";
import { useToolTaxonomy } from "./useToolTaxonomy";

type UseScriptEditorMetadataStateOptions = {
  toolId: Readonly<Ref<string>>;
  canEditTaxonomy: Readonly<Ref<boolean>>;
  canEditMaintainers: Readonly<Ref<boolean>>;
  canEditSlug: Readonly<Ref<boolean>>;
  notify: UiNotifier;
  isMetadataSaving: Readonly<Ref<boolean>>;
  isSlugSaving: Readonly<Ref<boolean>>;
  saveToolMetadata: () => Promise<void>;
  saveToolSlug: () => Promise<void>;
  editorMode: Readonly<Ref<EditorWorkspaceMode>>;
};

export function useScriptEditorMetadataState(options: UseScriptEditorMetadataStateOptions) {
  const {
    toolId,
    canEditTaxonomy,
    canEditMaintainers,
    canEditSlug,
    notify,
    isMetadataSaving,
    isSlugSaving,
    saveToolMetadata,
    saveToolSlug,
    editorMode,
  } = options;

  const {
    professions,
    categories,
    selectedProfessionIds,
    selectedCategoryIds,
    taxonomyError,
    isTaxonomyLoading,
    isTaxonomySaving,
    saveTaxonomy,
  } = useToolTaxonomy({
    toolId,
    canEdit: canEditTaxonomy,
    notify,
  });

  const {
    maintainers,
    ownerUserId,
    isLoading: isMaintainersLoading,
    isSaving: isMaintainersSaving,
    error: maintainersError,
    loadMaintainers,
    addMaintainer,
    removeMaintainer,
  } = useToolMaintainers({
    toolId,
    canEdit: canEditMaintainers,
    notify,
  });

  const isSavingAllMetadata = computed(
    () => isMetadataSaving.value || isTaxonomySaving.value || isSlugSaving.value,
  );

  async function saveAllMetadata(): Promise<void> {
    if (canEditSlug.value) {
      await saveToolSlug();
    }
    await saveToolMetadata();
    if (canEditTaxonomy.value) {
      await saveTaxonomy();
    }
  }

  const isTitleSaving = ref(false);
  const isSummarySaving = ref(false);

  async function saveTitle(): Promise<void> {
    isTitleSaving.value = true;
    try {
      await saveToolMetadata();
    } finally {
      isTitleSaving.value = false;
    }
  }

  async function saveSummary(): Promise<void> {
    isSummarySaving.value = true;
    try {
      await saveToolMetadata();
    } finally {
      isSummarySaving.value = false;
    }
  }

  watch(
    () => editorMode.value,
    (mode) => {
      if (mode !== "metadata") return;
      if (!canEditMaintainers.value) return;
      if (!toolId.value) return;
      void loadMaintainers(toolId.value);
    },
  );

  return {
    professions,
    categories,
    selectedProfessionIds,
    selectedCategoryIds,
    taxonomyError,
    isTaxonomyLoading,
    isTaxonomySaving,
    saveTaxonomy,
    maintainers,
    ownerUserId,
    isMaintainersLoading,
    isMaintainersSaving,
    maintainersError,
    addMaintainer,
    removeMaintainer,
    isSavingAllMetadata,
    saveAllMetadata,
    isTitleSaving,
    isSummarySaving,
    saveTitle,
    saveSummary,
  };
}
