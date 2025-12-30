import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter, type LocationQueryRaw } from "vue-router";

import { ApiError, apiGet } from "../api/client";
import type { CatalogItem } from "../types/catalog";
import { useCatalogFilters } from "./useCatalogFilters";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    apiGet: vi.fn(),
  };
});

type CatalogFiltersVm = {
  items: CatalogItem[];
  selectedProfessions: string[];
  selectedCategories: string[];
  searchTerm: string;
  searchInput: string;
  favoritesOnly: boolean;
  curatedOnly: boolean;
  isLoading: boolean;
  errorMessage: string | null;
};

const TestComponent = defineComponent({
  name: "TestCatalogFilters",
  setup() {
    return useCatalogFilters();
  },
  template: "<div />",
});

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

async function mountWithRouter(initialQuery: LocationQueryRaw = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/catalog", component: TestComponent }],
  });

  await router.push({ path: "/catalog", query: initialQuery });
  await router.isReady();

  const wrapper = mount(TestComponent, {
    global: { plugins: [router] },
  });

  await flushPromises();

  return { router, wrapper };
}

type CatalogResponse = {
  items: CatalogItem[];
  professions: unknown[];
  categories: unknown[];
};

function createCatalogResponse(items: CatalogItem[]): CatalogResponse {
  return {
    items,
    professions: [],
    categories: [],
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useCatalogFilters", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("normalizes route query and hydrates state", async () => {
    vi.mocked(apiGet).mockResolvedValue(createCatalogResponse([]) as never);

    const { wrapper, router } = await mountWithRouter();
    const replaceSpy = vi.spyOn(router, "replace");

    await router.push({
      path: "/catalog",
      query: {
        professions: [" Teacher ", "science,Math", "science"],
        categories: " Apps ,Scripts ,apps",
        q: "  hello ",
        favorites: "TRUE",
        curated_only: " true ",
      },
    });
    await flushPromises();
    const replacePromise = replaceSpy.mock.results[0]?.value as Promise<unknown> | undefined;
    if (replacePromise) {
      await replacePromise;
      await flushPromises();
    }

    expect(replaceSpy).toHaveBeenCalledWith({
      path: "/catalog",
      query: {
        professions: "math,science,teacher",
        categories: "apps,scripts",
        q: "hello",
        favorites: "true",
        curated_only: "true",
      },
    });
    expect({
      professions: (wrapper.vm as CatalogFiltersVm).selectedProfessions,
      categories: (wrapper.vm as CatalogFiltersVm).selectedCategories,
      searchTerm: (wrapper.vm as CatalogFiltersVm).searchTerm,
      favoritesOnly: (wrapper.vm as CatalogFiltersVm).favoritesOnly,
      curatedOnly: (wrapper.vm as CatalogFiltersVm).curatedOnly,
    }).toEqual({
      professions: ["math", "science", "teacher"],
      categories: ["apps", "scripts"],
      searchTerm: "hello",
      favoritesOnly: true,
      curatedOnly: true,
    });
    const expectedParams = new URLSearchParams({
      professions: "math,science,teacher",
      categories: "apps,scripts",
      q: "hello",
    });
    expect(apiGet).toHaveBeenLastCalledWith(`/api/v1/catalog/tools?${expectedParams.toString()}`);

    wrapper.unmount();
  });

  it("debounces search input before updating the route", async () => {
    vi.useFakeTimers();
    vi.mocked(apiGet).mockResolvedValueOnce(createCatalogResponse([]) as never);

    const { wrapper, router } = await mountWithRouter();
    const replaceSpy = vi.spyOn(router, "replace");

    (wrapper.vm as CatalogFiltersVm).searchInput = "first";
    await nextTick();

    (wrapper.vm as CatalogFiltersVm).searchInput = "second";
    await nextTick();

    await vi.advanceTimersByTimeAsync(299);
    expect(replaceSpy).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    await flushPromises();

    expect(replaceSpy).toHaveBeenCalledTimes(1);
    expect(replaceSpy).toHaveBeenLastCalledWith({
      path: "/catalog",
      query: { q: "second" },
    });

    wrapper.unmount();
  });

  it("ignores stale catalog responses", async () => {
    const first = createDeferred<CatalogResponse>();
    const second = createDeferred<CatalogResponse>();

    vi.mocked(apiGet)
      .mockImplementationOnce(() => first.promise as never)
      .mockImplementationOnce(() => second.promise as never);

    const { wrapper, router } = await mountWithRouter();

    await router.replace({ path: "/catalog", query: { q: "latest" } });
    await flushPromises();

    expect(apiGet).toHaveBeenCalledTimes(2);

    const newerItems: CatalogItem[] = [
      { id: "newer", title: "New", summary: null, is_favorite: false, kind: "tool", slug: "new" },
    ];
    second.resolve(createCatalogResponse(newerItems));
    await flushPromises();

    expect({
      items: (wrapper.vm as CatalogFiltersVm).items,
      isLoading: (wrapper.vm as CatalogFiltersVm).isLoading,
    }).toEqual({
      items: newerItems,
      isLoading: false,
    });

    const olderItems: CatalogItem[] = [
      { id: "older", title: "Old", summary: null, is_favorite: false, kind: "tool", slug: "old" },
    ];
    first.resolve(createCatalogResponse(olderItems));
    await flushPromises();

    expect((wrapper.vm as CatalogFiltersVm).items).toEqual(newerItems);

    wrapper.unmount();
  });

  it("filters favorites and curated items client-side", async () => {
    const items: CatalogItem[] = [
      { id: "fav", title: "Fav", summary: null, is_favorite: true, kind: "curated_app", app_id: "app-1" },
      { id: "tool", title: "Tool", summary: null, is_favorite: true, kind: "tool", slug: "tool" },
      { id: "other", title: "Other", summary: null, is_favorite: false, kind: "curated_app", app_id: "app-2" },
    ];

    vi.mocked(apiGet).mockResolvedValueOnce(createCatalogResponse(items) as never);

    const { wrapper } = await mountWithRouter({ favorites: "true", curated_only: "true" });

    expect((wrapper.vm as CatalogFiltersVm).items).toEqual([items[0]]);
    expect({
      favoritesOnly: (wrapper.vm as CatalogFiltersVm).favoritesOnly,
      curatedOnly: (wrapper.vm as CatalogFiltersVm).curatedOnly,
    }).toEqual({
      favoritesOnly: true,
      curatedOnly: true,
    });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/catalog/tools");

    wrapper.unmount();
  });

  it("surfaces API errors on load", async () => {
    vi.mocked(apiGet).mockRejectedValueOnce(
      new ApiError({ code: "FAIL", message: "Boom", status: 500, details: null, correlationId: null }),
    );

    const { wrapper } = await mountWithRouter();
    await flushPromises();

    expect((wrapper.vm as CatalogFiltersVm).errorMessage).toBe("Boom");
    expect((wrapper.vm as CatalogFiltersVm).isLoading).toBe(false);

    wrapper.unmount();
  });
});
