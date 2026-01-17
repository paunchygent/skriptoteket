import { computed, ref } from "vue";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useFavorites } from "../useFavorites";
import type { CatalogItem } from "../../types/catalog";

type ListMyRunsResponse = components["schemas"]["ListMyRunsResponse"];
type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type ListAdminToolsResponse = components["schemas"]["ListAdminToolsResponse"];
type ListFavoritesResponse = components["schemas"]["ListFavoritesResponse"];
type ListRecentToolsResponse = components["schemas"]["ListRecentToolsResponse"];

type DashboardRoles = {
  isContributor: boolean;
  isAdmin: boolean;
};

const FAVORITES_LIMIT = 5;

function formatCount(n: number): string {
  if (n >= 1000) {
    const k = n / 1000;
    return k % 1 === 0 ? `${k}k` : `${k.toFixed(1)}k`;
  }
  return String(n);
}

function catalogKey(item: CatalogItem): string {
  return `${item.kind}:${item.id}`;
}

export function useHomeDashboard() {
  const { toggleFavorite, isToggling } = useFavorites();

  const runsCount = ref(0);
  const runsInList = ref(0);
  const runsLoading = ref(false);
  const currentMonth = new Date().toLocaleString("sv-SE", { month: "long" });

  const toolsTotal = ref(0);
  const toolsPublished = ref(0);
  const toolsLoading = ref(false);

  const adminToolsTotal = ref(0);
  const adminToolsPublished = ref(0);
  const adminPendingReview = ref(0);
  const adminLoading = ref(false);

  const dashboardError = ref<string | null>(null);

  const favorites = ref<CatalogItem[]>([]);
  const recentTools = ref<CatalogItem[]>([]);

  const favoriteKeys = computed(() => new Set(favorites.value.map(catalogKey)));
  const recentNonFavorites = computed(() =>
    recentTools.value.filter(
      (item) => !item.is_favorite && !favoriteKeys.value.has(catalogKey(item))
    )
  );

  async function loadUserDashboard(): Promise<void> {
    runsLoading.value = true;
    try {
      const response = await apiGet<ListMyRunsResponse>("/api/v1/my-runs");
      runsCount.value = response.total_count;
      runsInList.value = response.runs.length;
    } catch (error: unknown) {
      if (isApiError(error)) {
        dashboardError.value = error.message;
      }
    } finally {
      runsLoading.value = false;
    }
  }

  async function loadContributorDashboard(): Promise<void> {
    toolsLoading.value = true;
    try {
      const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
      toolsTotal.value = response.tools.length;
      toolsPublished.value = response.tools.filter((t) => t.is_published).length;
    } catch (error: unknown) {
      if (isApiError(error)) {
        dashboardError.value = error.message;
      }
    } finally {
      toolsLoading.value = false;
    }
  }

  async function loadAdminDashboard(): Promise<void> {
    adminLoading.value = true;
    try {
      const response = await apiGet<ListAdminToolsResponse>("/api/v1/admin/tools");
      adminToolsTotal.value = response.tools.length;
      adminToolsPublished.value = response.tools.filter((t) => t.is_published).length;
      adminPendingReview.value = response.tools.filter((t) => t.has_pending_review).length;
    } catch (error: unknown) {
      if (isApiError(error)) {
        dashboardError.value = error.message;
      }
    } finally {
      adminLoading.value = false;
    }
  }

  async function loadFavorites(): Promise<void> {
    try {
      const response = await apiGet<ListFavoritesResponse>(
        `/api/v1/favorites?limit=${FAVORITES_LIMIT}`
      );
      favorites.value = response.items as CatalogItem[];
    } catch {
      // Silent fail - section just won't show
    }
  }

  async function loadRecentTools(): Promise<void> {
    try {
      const response = await apiGet<ListRecentToolsResponse>(
        "/api/v1/me/recent-tools?limit=5"
      );
      recentTools.value = response.items as CatalogItem[];
    } catch {
      // Silent fail - section just won't show
    }
  }

  async function loadDashboard(roles: DashboardRoles): Promise<void> {
    await Promise.all([
      loadUserDashboard(),
      loadFavorites(),
      loadRecentTools(),
      roles.isContributor ? loadContributorDashboard() : Promise.resolve(),
      roles.isAdmin ? loadAdminDashboard() : Promise.resolve(),
    ]);
  }

  async function handleFavoriteToggled(payload: {
    id: string;
    isFavorite: boolean;
  }): Promise<void> {
    if (isToggling(payload.id)) return;

    const nextIsFavorite = !payload.isFavorite;
    const targetItem =
      favorites.value.find((item) => item.id === payload.id) ??
      recentTools.value.find((item) => item.id === payload.id);
    const targetKey = targetItem ? catalogKey(targetItem) : null;

    const prevFavorites = favorites.value;
    if (nextIsFavorite) {
      if (!targetItem || !targetKey) {
        favorites.value = prevFavorites;
      } else {
        const nextItem = { ...targetItem, is_favorite: true };
        const nextFavorites = prevFavorites.some((item) => catalogKey(item) === targetKey)
          ? prevFavorites.map((item) =>
              catalogKey(item) === targetKey ? { ...item, is_favorite: true } : item
            )
          : [nextItem, ...prevFavorites];
        favorites.value = nextFavorites.slice(0, FAVORITES_LIMIT);
      }
    } else if (targetKey) {
      favorites.value = prevFavorites.filter((item) => catalogKey(item) !== targetKey);
    }

    const prevRecent = recentTools.value;
    recentTools.value = prevRecent.map((item) => {
      if (targetKey) {
        return catalogKey(item) === targetKey ? { ...item, is_favorite: nextIsFavorite } : item;
      }
      return item.id === payload.id ? { ...item, is_favorite: nextIsFavorite } : item;
    });

    const finalIsFavorite = await toggleFavorite(payload.id, payload.isFavorite);
    if (finalIsFavorite !== nextIsFavorite) {
      favorites.value = prevFavorites;
      recentTools.value = prevRecent;
    }
  }

  return {
    runsCount,
    runsInList,
    runsLoading,
    currentMonth,
    toolsTotal,
    toolsPublished,
    toolsLoading,
    adminToolsTotal,
    adminToolsPublished,
    adminPendingReview,
    adminLoading,
    dashboardError,
    favorites,
    recentTools,
    recentNonFavorites,
    formatCount,
    isToggling,
    handleFavoriteToggled,
    loadDashboard,
  };
}
