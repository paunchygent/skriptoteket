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
    expect(wrapper.text()).toContain("Dela med kollegor");
    expect(wrapper.html()).toContain('href="/public/apps/classroom.group-seating-studio"');
    expect(wrapper.html()).toContain('href="/register"');
    expect(homeMocks.dashboard.loadDashboard).not.toHaveBeenCalled();
  });
});
