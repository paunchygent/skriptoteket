/**
 * Catalog item card tests.
 *
 * These tests cover compact dashboard cards used by the authenticated
 * home-page favorites and recent-items sections without widening the behavior
 * to catalog list rows.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { CatalogItem } from "../../types/catalog";
import CatalogItemCard from "./CatalogItemCard.vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({ name: "home" }),
  useRouter: () => ({ push: vi.fn() }),
}));

const classroomPlannerItem: CatalogItem = {
  id: "app-classroom",
  kind: "curated_app",
  app_id: "classroom.group-seating-studio",
  title: "Klassrumskartan",
  summary: "Planera grupper och sittplatser.",
  is_favorite: true,
};

describe("CatalogItemCard", () => {
  it("renders the Klassrumskartan symbol on compact dashboard cards", () => {
    const wrapper = mount(CatalogItemCard, {
      props: {
        item: classroomPlannerItem,
        variant: "compact",
      },
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a href='#'><slot /></a>",
          },
        },
      },
    });

    const symbol = wrapper.get('img[alt=""]');
    expect(symbol.attributes("src")).toContain("classroom-map-symbol");
  });

  it("keeps catalog list rows text-only", () => {
    const wrapper = mount(CatalogItemCard, {
      props: {
        item: classroomPlannerItem,
        variant: "list",
      },
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a href='#'><slot /></a>",
          },
        },
      },
    });

    expect(wrapper.find('img[alt=""]').exists()).toBe(false);
  });
});
