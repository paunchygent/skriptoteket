import { ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type ToolTaxonomyResponse = components["schemas"]["ToolTaxonomyResponse"];

type UseToolTaxonomyOptions = {
  toolId: Readonly<Ref<string>>;
  canEdit: Readonly<Ref<boolean>>;
};

export function useToolTaxonomy({ toolId, canEdit }: UseToolTaxonomyOptions) {
  const professions = ref<ProfessionItem[]>([]);
  const categories = ref<CategoryItem[]>([]);
  const selectedProfessionIds = ref<string[]>([]);
  const selectedCategoryIds = ref<string[]>([]);
  const taxonomyError = ref<string | null>(null);
  const taxonomySuccess = ref<string | null>(null);
  const isTaxonomyLoading = ref(false);
  const isTaxonomySaving = ref(false);

  function toggleSelection(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  }

  async function loadTaxonomy(toolIdValue: string): Promise<void> {
    if (!toolIdValue || !canEdit.value) {
      return;
    }

    isTaxonomyLoading.value = true;
    taxonomyError.value = null;
    taxonomySuccess.value = null;

    try {
      const [profResp, catResp, taxonomyResp] = await Promise.all([
        apiGet<{ professions: ProfessionItem[] }>("/api/v1/catalog/professions"),
        apiGet<{ categories: CategoryItem[] }>("/api/v1/catalog/categories"),
        apiGet<ToolTaxonomyResponse>(
          `/api/v1/editor/tools/${encodeURIComponent(toolIdValue)}/taxonomy`,
        ),
      ]);

      professions.value = profResp.professions;
      categories.value = catResp.categories;
      selectedProfessionIds.value = taxonomyResp.profession_ids;
      selectedCategoryIds.value = taxonomyResp.category_ids;
    } catch (error: unknown) {
      if (isApiError(error)) {
        taxonomyError.value = error.message;
      } else if (error instanceof Error) {
        taxonomyError.value = error.message;
      } else {
        taxonomyError.value = "Det gick inte att ladda taxonomi.";
      }
    } finally {
      isTaxonomyLoading.value = false;
    }
  }

  async function saveTaxonomy(): Promise<void> {
    const toolIdValue = toolId.value;
    if (!toolIdValue || isTaxonomySaving.value) {
      return;
    }

    taxonomyError.value = null;
    taxonomySuccess.value = null;

    if (selectedProfessionIds.value.length === 0) {
      taxonomyError.value = "Välj minst ett yrke.";
      return;
    }
    if (selectedCategoryIds.value.length === 0) {
      taxonomyError.value = "Välj minst en kategori.";
      return;
    }

    isTaxonomySaving.value = true;

    try {
      const response = await apiFetch<ToolTaxonomyResponse>(
        `/api/v1/editor/tools/${encodeURIComponent(toolIdValue)}/taxonomy`,
        {
          method: "PATCH",
          body: {
            profession_ids: selectedProfessionIds.value,
            category_ids: selectedCategoryIds.value,
          },
        },
      );
      selectedProfessionIds.value = response.profession_ids;
      selectedCategoryIds.value = response.category_ids;
      taxonomySuccess.value = "Taxonomi sparad.";
    } catch (error: unknown) {
      if (isApiError(error)) {
        taxonomyError.value = error.message;
      } else if (error instanceof Error) {
        taxonomyError.value = error.message;
      } else {
        taxonomyError.value = "Det gick inte att spara taxonomi.";
      }
    } finally {
      isTaxonomySaving.value = false;
    }
  }

  watch(
    [toolId, canEdit],
    ([toolIdValue, isAllowed]) => {
      if (!toolIdValue || !isAllowed) {
        return;
      }
      void loadTaxonomy(toolIdValue);
    },
    { immediate: true },
  );

  return {
    professions,
    categories,
    selectedProfessionIds,
    selectedCategoryIds,
    taxonomyError,
    taxonomySuccess,
    isTaxonomyLoading,
    isTaxonomySaving,
    loadTaxonomy,
    saveTaxonomy,
    toggleSelection,
  };
}
