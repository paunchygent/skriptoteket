import { ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type MaintainerSummary = components["schemas"]["MaintainerSummary"];
type MaintainerListResponse = components["schemas"]["MaintainerListResponse"];

type UseToolMaintainersOptions = {
  toolId: Readonly<Ref<string>>;
  canEdit: Readonly<Ref<boolean>>;
};

export function useToolMaintainers({ toolId, canEdit }: UseToolMaintainersOptions) {
  const maintainers = ref<MaintainerSummary[]>([]);
  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);
  const success = ref<string | null>(null);

  async function loadMaintainers(toolIdValue: string): Promise<void> {
    if (!toolIdValue || !canEdit.value) {
      return;
    }

    isLoading.value = true;
    error.value = null;
    success.value = null;

    try {
      const path = `/api/v1/editor/tools/${encodeURIComponent(toolIdValue)}/maintainers`;
      const response = await apiGet<MaintainerListResponse>(path);
      maintainers.value = response.maintainers;
    } catch (err: unknown) {
      if (isApiError(err)) {
        error.value = err.message;
      } else if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = "Det gick inte att ladda redigeringsbehörigheter.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function addMaintainer(email: string): Promise<void> {
    const toolIdValue = toolId.value;
    if (!toolIdValue || isSaving.value) {
      return;
    }

    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      error.value = "E-post krävs.";
      return;
    }

    isSaving.value = true;
    error.value = null;
    success.value = null;

    try {
      const path = `/api/v1/editor/tools/${encodeURIComponent(toolIdValue)}/maintainers`;
      const response = await apiFetch<MaintainerListResponse>(path, {
        method: "POST",
        body: { email: normalizedEmail },
      });
      maintainers.value = response.maintainers;
      success.value = "Redigeringsbehörigheter uppdaterade.";
    } catch (err: unknown) {
      if (isApiError(err)) {
        error.value = err.message;
      } else if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = "Det gick inte att lägga till redigeringsbehörighet.";
      }
    } finally {
      isSaving.value = false;
    }
  }

  async function removeMaintainer(userId: string): Promise<void> {
    const toolIdValue = toolId.value;
    if (!toolIdValue || isSaving.value) {
      return;
    }

    isSaving.value = true;
    error.value = null;
    success.value = null;

    try {
      const path =
        `/api/v1/editor/tools/${encodeURIComponent(toolIdValue)}/maintainers/` +
        encodeURIComponent(userId);
      const response = await apiFetch<MaintainerListResponse>(path, {
        method: "DELETE",
      });
      maintainers.value = response.maintainers;
      success.value = "Redigeringsbehörigheter uppdaterade.";
    } catch (err: unknown) {
      if (isApiError(err)) {
        error.value = err.message;
      } else if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = "Det gick inte att ta bort redigeringsbehörighet.";
      }
    } finally {
      isSaving.value = false;
    }
  }

  watch(
    [toolId, canEdit],
    ([toolIdValue, isAllowed]) => {
      if (!toolIdValue || !isAllowed) {
        maintainers.value = [];
        return;
      }
      void loadMaintainers(toolIdValue);
    },
    { immediate: true },
  );

  return {
    maintainers,
    isLoading,
    isSaving,
    error,
    success,
    loadMaintainers,
    addMaintainer,
    removeMaintainer,
  };
}
