import { ref } from "vue";

import { apiFetch, isApiError } from "../api/client";
import { useToast } from "./useToast";

export function useFavorites() {
  const togglingIds = ref(new Set<string>());
  const toast = useToast();

  function isToggling(id: string): boolean {
    return togglingIds.value.has(id);
  }

  function setToggling(id: string, value: boolean): void {
    const next = new Set(togglingIds.value);
    if (value) {
      next.add(id);
    } else {
      next.delete(id);
    }
    togglingIds.value = next;
  }

  async function toggleFavorite(catalogItemId: string, currentlyFavorite: boolean): Promise<boolean> {
    if (isToggling(catalogItemId)) {
      return currentlyFavorite;
    }

    setToggling(catalogItemId, true);

    try {
      const encodedId = encodeURIComponent(catalogItemId);
      if (currentlyFavorite) {
        await apiFetch(`/api/v1/favorites/${encodedId}`, { method: "DELETE" });
        return false;
      }

      await apiFetch(`/api/v1/favorites/${encodedId}`, { method: "POST" });
      return true;
    } catch (error: unknown) {
      toast.failure(isApiError(error) ? error.message : "Det gick inte att uppdatera favoriten.");
      return currentlyFavorite;
    } finally {
      setToggling(catalogItemId, false);
    }
  }

  return {
    toggleFavorite,
    isToggling,
  };
}
