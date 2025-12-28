import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter, type LocationQuery, type LocationQueryRaw } from "vue-router";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import type { CatalogItem } from "../types/catalog";

export type CatalogProfession = components["schemas"]["ProfessionItem"];
export type CatalogCategory = components["schemas"]["CategoryItem"];

type ListCatalogToolsResponse = {
  items: CatalogItem[];
  professions: CatalogProfession[];
  categories: CatalogCategory[];
};

type FilterState = {
  professions: string[];
  categories: string[];
  searchTerm: string;
  favoritesOnly: boolean;
  curatedOnly: boolean;
};

type ParsedFilters = FilterState & {
  normalizedQuery: LocationQueryRaw;
};

const SEARCH_DEBOUNCE_MS = 300;

function normalizeSlug(value: string): string {
  return value.trim().toLowerCase();
}

function normalizeSlugList(value: unknown): string[] {
  const raw: string[] = [];

  if (typeof value === "string") {
    raw.push(...value.split(","));
  } else if (Array.isArray(value)) {
    for (const entry of value) {
      if (typeof entry === "string") {
        raw.push(...entry.split(","));
      }
    }
  }

  const normalized = raw.map(normalizeSlug).filter(Boolean);
  const unique = Array.from(new Set(normalized));
  unique.sort((a, b) => a.localeCompare(b));
  return unique;
}

function normalizeSearchTerm(value: unknown): string {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim();
}

function normalizeFavorites(value: unknown): boolean {
  if (typeof value !== "string") {
    return false;
  }
  return value.trim().toLowerCase() === "true";
}

function normalizeCuratedOnly(value: unknown): boolean {
  if (typeof value !== "string") {
    return false;
  }
  return value.trim().toLowerCase() === "true";
}

function buildQuery(filters: FilterState): LocationQueryRaw {
  const query: LocationQueryRaw = {};

  if (filters.professions.length > 0) {
    query.professions = filters.professions.join(",");
  }

  if (filters.categories.length > 0) {
    query.categories = filters.categories.join(",");
  }

  const trimmedSearch = filters.searchTerm.trim();
  if (trimmedSearch) {
    query.q = trimmedSearch;
  }

  if (filters.favoritesOnly) {
    query.favorites = "true";
  }

  if (filters.curatedOnly) {
    query.curated_only = "true";
  }

  return query;
}

function parseRouteFilters(query: LocationQuery): ParsedFilters {
  const professions = normalizeSlugList(query.professions);
  const categories = normalizeSlugList(query.categories);
  const searchTerm = normalizeSearchTerm(query.q);
  const favoritesOnly = normalizeFavorites(query.favorites);
  const curatedOnly = normalizeCuratedOnly(query.curated_only);

  return {
    professions,
    categories,
    searchTerm,
    favoritesOnly,
    curatedOnly,
    normalizedQuery: buildQuery({ professions, categories, searchTerm, favoritesOnly, curatedOnly }),
  };
}

function toggleSelection(list: string[], value: string): string[] {
  const normalized = normalizeSlug(value);
  const next = list.includes(normalized)
    ? list.filter((item) => item !== normalized)
    : [...list, normalized];
  const unique = Array.from(new Set(next));
  unique.sort((a, b) => a.localeCompare(b));
  return unique;
}

export function useCatalogFilters() {
  const route = useRoute();
  const router = useRouter();

  const items = ref<CatalogItem[]>([]);
  const professions = ref<CatalogProfession[]>([]);
  const categories = ref<CatalogCategory[]>([]);
  const selectedProfessions = ref<string[]>([]);
  const selectedCategories = ref<string[]>([]);
  const searchTerm = ref("");
  const searchInput = ref("");
  const favoritesOnly = ref(false);
  const curatedOnly = ref(false);
  const isLoading = ref(true);
  const errorMessage = ref<string | null>(null);

  let searchTimer: number | null = null;
  let requestCounter = 0;

  function clearSearchTimer(): void {
    if (searchTimer !== null) {
      window.clearTimeout(searchTimer);
      searchTimer = null;
    }
  }

  async function updateRouteQuery(filters: FilterState): Promise<void> {
    const normalizedQuery = buildQuery(filters);
    const nextLocation = { path: route.path, query: normalizedQuery };
    const nextUrl = router.resolve(nextLocation).fullPath;

    if (nextUrl === route.fullPath) {
      return;
    }

    await router.replace(nextLocation);
  }

  async function fetchCatalog(filters: FilterState): Promise<void> {
    const requestId = ++requestCounter;
    isLoading.value = true;
    errorMessage.value = null;

    const searchParams = new URLSearchParams();
    if (filters.professions.length > 0) {
      searchParams.set("professions", filters.professions.join(","));
    }
    if (filters.categories.length > 0) {
      searchParams.set("categories", filters.categories.join(","));
    }
    if (filters.searchTerm.trim()) {
      searchParams.set("q", filters.searchTerm.trim());
    }

    const path = searchParams.toString()
      ? `/api/v1/catalog/tools?${searchParams.toString()}`
      : "/api/v1/catalog/tools";

    try {
      const response = await apiGet<ListCatalogToolsResponse>(path);
      if (requestId !== requestCounter) {
        return;
      }
      professions.value = response.professions;
      categories.value = response.categories;
      let filteredItems = response.items;
      if (filters.favoritesOnly) {
        filteredItems = filteredItems.filter((item) => item.is_favorite);
      }
      if (filters.curatedOnly) {
        filteredItems = filteredItems.filter((item) => item.kind === "curated_app");
      }
      items.value = filteredItems;
    } catch (error: unknown) {
      if (requestId !== requestCounter) {
        return;
      }
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ladda katalogen.";
      }
    } finally {
      if (requestId === requestCounter) {
        isLoading.value = false;
      }
    }
  }

  async function syncFromRoute(): Promise<void> {
    const parsed = parseRouteFilters(route.query);
    const normalizedUrl = router.resolve({
      path: route.path,
      query: parsed.normalizedQuery,
    }).fullPath;

    if (normalizedUrl !== route.fullPath) {
      await router.replace({ path: route.path, query: parsed.normalizedQuery });
      return;
    }

    selectedProfessions.value = parsed.professions;
    selectedCategories.value = parsed.categories;
    searchTerm.value = parsed.searchTerm;
    searchInput.value = parsed.searchTerm;
    favoritesOnly.value = parsed.favoritesOnly;
    curatedOnly.value = parsed.curatedOnly;

    await fetchCatalog(parsed);
  }

  function toggleProfession(slug: string): void {
    const nextProfessions = toggleSelection(selectedProfessions.value, slug);
    void updateRouteQuery({
      professions: nextProfessions,
      categories: selectedCategories.value,
      searchTerm: searchInput.value,
      favoritesOnly: favoritesOnly.value,
      curatedOnly: curatedOnly.value,
    });
  }

  function toggleCategory(slug: string): void {
    const nextCategories = toggleSelection(selectedCategories.value, slug);
    void updateRouteQuery({
      professions: selectedProfessions.value,
      categories: nextCategories,
      searchTerm: searchInput.value,
      favoritesOnly: favoritesOnly.value,
      curatedOnly: curatedOnly.value,
    });
  }

  function setFavoritesOnly(value: boolean): void {
    void updateRouteQuery({
      professions: selectedProfessions.value,
      categories: selectedCategories.value,
      searchTerm: searchInput.value,
      favoritesOnly: value,
      curatedOnly: curatedOnly.value,
    });
  }

  function setCuratedOnly(value: boolean): void {
    void updateRouteQuery({
      professions: selectedProfessions.value,
      categories: selectedCategories.value,
      searchTerm: searchInput.value,
      favoritesOnly: favoritesOnly.value,
      curatedOnly: value,
    });
  }

  function clearFilters(): void {
    searchInput.value = "";
    void updateRouteQuery({
      professions: [],
      categories: [],
      searchTerm: "",
      favoritesOnly: false,
      curatedOnly: false,
    });
  }

  watch(
    () => route.query,
    () => {
      void syncFromRoute();
    },
  );

  watch(searchInput, (value) => {
    if (value === searchTerm.value) {
      return;
    }

    clearSearchTimer();
    searchTimer = window.setTimeout(() => {
      void updateRouteQuery({
        professions: selectedProfessions.value,
        categories: selectedCategories.value,
        searchTerm: value,
        favoritesOnly: favoritesOnly.value,
        curatedOnly: curatedOnly.value,
      });
    }, SEARCH_DEBOUNCE_MS);
  });

  onMounted(() => {
    void syncFromRoute();
  });

  onBeforeUnmount(() => {
    clearSearchTimer();
  });

  return {
    items,
    professions,
    categories,
    selectedProfessions,
    selectedCategories,
    searchTerm,
    searchInput,
    favoritesOnly,
    curatedOnly,
    isLoading,
    errorMessage,
    toggleProfession,
    toggleCategory,
    setFavoritesOnly,
    setCuratedOnly,
    clearFilters,
  };
}
