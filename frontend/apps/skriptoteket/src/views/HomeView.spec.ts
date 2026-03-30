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
  loginOpen: vi.fn(),
  loadDashboard: vi.fn(),
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

vi.mock("../composables/useLoginModal", () => ({
  useLoginModal: () => ({
    open: homeMocks.loginOpen,
  }),
}));

vi.mock("../composables/home/useHomeDashboard", () => ({
  useHomeDashboard: () => homeMocks.dashboard,
}));

describe("HomeView", () => {
  beforeEach(() => {
    homeMocks.auth.isAuthenticated = false;
    homeMocks.auth.hasAtLeastRole.mockReset();
    homeMocks.auth.hasAtLeastRole.mockReturnValue(false);
    homeMocks.loginOpen.mockReset();
    homeMocks.dashboard.loadDashboard.mockReset();
  });

  it("shows the curated teacher-library positioning for signed-out users", async () => {
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

    expect(wrapper.text()).toContain("Professionellt appbibliotek för lärare");
    expect(wrapper.text()).toContain(
      "Logga in och använd appar och verktyg för undervisning, planering och dokumentation.",
    );
    expect(wrapper.text()).toContain("Dela med kollegor");
    expect(wrapper.text()).not.toContain("Ta koden i egna händer");
    expect(wrapper.html()).toContain('href="/register"');

    await wrapper.get("button").trigger("click");

    expect(homeMocks.loginOpen).toHaveBeenCalledTimes(1);
    expect(homeMocks.dashboard.loadDashboard).not.toHaveBeenCalled();
  });
});
