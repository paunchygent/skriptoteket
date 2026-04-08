/**
 * Home view tests.
 *
 * These tests keep the public landing page aligned with the current product
 * reality instead of the older open script-creation pitch.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomeView from "./HomeView.vue";

const homeMocks = vi.hoisted(() => ({
  auth: {
    isAuthenticated: false,
    hasAtLeastRole: vi.fn(() => false),
    displayName: null,
  },
  dashboard: {
    loadDashboard: vi.fn(),
    dashboardError: null,
    favorites: [],
    recentNonFavorites: [],
    isToggling: false,
    handleFavoriteToggled: vi.fn(),
    runsLoading: false,
    runsCount: 0,
    currentMonth: "mars",
    runsInList: 5,
    formatCount: vi.fn((value: number) => String(value)),
    toolsLoading: false,
    toolsTotal: 0,
    toolsPublished: 0,
    adminPendingReview: 0,
    adminLoading: false,
  },
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => homeMocks.auth,
}));

vi.mock("../composables/home/useHomeDashboard", () => ({
  useHomeDashboard: () => homeMocks.dashboard,
}));

vi.mock("vue-router", () => ({
  useRoute: () => ({
    name: "home",
    params: {},
  }),
}));

describe("HomeView", () => {
  beforeEach(() => {
    homeMocks.auth.isAuthenticated = false;
    homeMocks.auth.hasAtLeastRole.mockReset();
    homeMocks.auth.hasAtLeastRole.mockReturnValue(false);
    homeMocks.dashboard.loadDashboard.mockReset();
  });

  it("shows the public-entry hero hierarchy for signed-out users", () => {
    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Lärarverktyg direkt i webbläsaren.");
    expect(wrapper.text()).toContain("Klassrumskartan är en av Skriptotekets appar.");
    expect(wrapper.text()).toContain("Öppna Klassrumskartan");
    expect(wrapper.text()).toContain("skapa ett konto");
    expect(wrapper.html()).toContain('href="/public/apps/classroom.group-seating-studio"');
    expect(wrapper.html()).toContain('href="/register"');
    expect(homeMocks.dashboard.loadDashboard).not.toHaveBeenCalled();
  });

  it("renders the featured Klassrumskartan showcase and authenticated preview ledger", () => {
    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    // Featured Klassrumskartan showcase
    expect(wrapper.text()).toContain("Klassrumskartan");
    expect(wrapper.text()).toContain("Skapa salen, placera eleverna, spara som PDF.");
    expect(wrapper.text()).toContain("Öppna appen");
    expect(wrapper.text()).toContain("Skapa salen");
    expect(wrapper.text()).toContain("Placera eleverna");
    expect(wrapper.text()).toContain("Exportera");

    // Authenticated-only preview ledger
    expect(wrapper.text()).toContain("Mer när du loggar in");
    expect(wrapper.text()).toContain("Spara dina inställningar och filer");
    expect(wrapper.text()).toContain("Bygg egna verktyg i kodredigeraren");
    expect(wrapper.text()).toContain("Kräver konto");
    expect(wrapper.text()).toContain("Kräver ansökan");
    expect(wrapper.text()).toContain("Skapa konto");

    const heroPreview = wrapper.get('img[alt="Klassrum med tavla, dörr och placerade elever"]');
    expect(heroPreview.attributes("src")).toContain("hero-preview");

    const showcaseImages = wrapper.findAll('img[alt=""]');
    expect(showcaseImages).toHaveLength(3);
    expect(showcaseImages[0]?.attributes("src")).toContain("step-01-skapa-salen");
    expect(showcaseImages[1]?.attributes("src")).toContain("step-02-placera-eleverna");
    expect(showcaseImages[2]?.attributes("src")).toContain("step-03-exportera");

    // Trailing in-place login trigger is a button (not a public route link)
    const loginButton = wrapper.find('button[type="button"]');
    expect(loginButton.exists()).toBe(true);
    expect(loginButton.text()).toContain("Logga in");
  });
});
