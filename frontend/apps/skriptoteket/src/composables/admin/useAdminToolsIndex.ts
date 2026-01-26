import { ref } from "vue";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];
type AdminToolItem = components["schemas"]["AdminToolItem"];

const tools = ref<AdminToolItem[] | null>(null);
const isLoading = ref(false);
const error = ref<string | null>(null);

let inFlight: Promise<AdminToolItem[]> | null = null;

async function loadAdminTools(): Promise<AdminToolItem[]> {
  if (inFlight) return inFlight;

  isLoading.value = true;
  error.value = null;

  inFlight = (async () => {
    try {
      const response = await apiGet<ListAdminToolsResponse>("/api/v1/admin/tools");
      tools.value = response.tools;
      return response.tools;
    } catch (caught: unknown) {
      tools.value = null;
      if (isApiError(caught)) {
        error.value = caught.message;
      } else if (caught instanceof Error) {
        error.value = caught.message;
      } else {
        error.value = "Det gick inte att ladda verktyg.";
      }
      return [];
    } finally {
      isLoading.value = false;
      inFlight = null;
    }
  })();

  return inFlight;
}

export function useAdminToolsIndex() {
  async function ensureLoaded(): Promise<AdminToolItem[]> {
    if (tools.value) return tools.value;
    return loadAdminTools();
  }

  function clearCache(): void {
    tools.value = null;
    error.value = null;
  }

  return {
    tools,
    isLoading,
    error,
    ensureLoaded,
    clearCache,
  };
}
