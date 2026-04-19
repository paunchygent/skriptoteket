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
    query: {},
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

    expect(wrapper.text()).toContain("Lektionsplanera direkt i webbläsaren.");
    expect(wrapper.text()).toContain("Klassrumskartan är en av Skriptotekets appar.");
    expect(wrapper.text()).toContain("Öppna Klassrumskartan");
    expect(wrapper.text()).toContain("skapa ett konto");
    expect(wrapper.html()).toContain('href="/public/apps/classroom.group-seating-studio"');
    expect(wrapper.html()).toContain("https://api.hule.education/auth/register");
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
    expect(wrapper.text()).toContain(
      "Skapa salen, placera eleverna, spara som PDF eller för Excel.",
    );
    expect(wrapper.text()).toContain(
      "Som inloggad är alla dina klasser, grupperingar och klassrumsplaceringar sparade.",
    );
    expect(wrapper.text()).toContain("Öppna appen");
    expect(wrapper.text()).toContain("Skapa salen");
    expect(wrapper.text()).toContain("Placera eleverna");
    expect(wrapper.text()).toContain("Exportera");

    // Roman-numeral step markers (I, II, III) replace the former 01/02/03.
    const showcaseIndices = wrapper.findAll(
      'section[class*="border-b"] p.font-mono',
    );
    const showcaseIndexLabels = showcaseIndices
      .slice(0, 3)
      .map((node) => node.text());
    expect(showcaseIndexLabels).toEqual(["I", "II", "III"]);
    expect(wrapper.text()).not.toContain("01");
    expect(wrapper.text()).not.toContain("02");
    expect(wrapper.text()).not.toContain("03");

    // Authenticated-only preview — Alternative B: leads with access to more
    // apps and work tools, surfaces that teacher suggestions can become new
    // apps, and keeps saved work as the persistence guarantee. The code
    // editor is no longer a ledger row on the landing page.
    expect(wrapper.text()).toContain("Mer när du loggar in");
    expect(wrapper.text()).toContain(
      "Få tillgång till fler appar och arbetsverktyg.",
    );
    expect(wrapper.text()).toContain("Fler färdiga lärarverktyg");
    expect(wrapper.text()).toContain(
      "Använd alla Skriptotekets appar och verktyg som finns tillgängliga.",
    );
    expect(wrapper.text()).toContain("Dina förslag kan bli nya appar");
    expect(wrapper.text()).toContain(
      "Berätta vilka arbetsmoment du vill slippa göra för hand.",
    );
    expect(wrapper.text()).toContain("Spara arbetet över tid");
    expect(wrapper.text()).toContain(
      "Kom tillbaka till dina klasser, filer, inställningar och placeringar.",
    );
    expect(wrapper.text()).toContain("Kräver konto");
    expect(wrapper.text()).not.toContain("Kräver ansökan");
    expect(wrapper.text()).not.toContain("kodredigeraren");
    expect(wrapper.text()).toContain("Skapa konto");

    const heroPreview = wrapper.get('img[alt="Klassrum med tavla, dörr och placerade elever"]');
    expect(heroPreview.attributes("src")).toContain("hero-preview");

    const showcaseImages = wrapper.findAll('img[alt=""]');
    expect(showcaseImages).toHaveLength(3);
    expect(showcaseImages[0]?.attributes("src")).toContain("step-01-skapa-salen");
    expect(showcaseImages[1]?.attributes("src")).toContain("step-02-placera-eleverna");
    expect(showcaseImages[2]?.attributes("src")).toContain("step-03-exportera");

    const loginLink = wrapper.find(
      'a[href^="https://api.hule.education/auth/login?app=skriptoteket"]',
    );
    expect(loginLink.exists()).toBe(true);
    expect(loginLink.text()).toContain("Logga in");

    const registerLinks = wrapper.findAll(
      'a[href^="https://api.hule.education/auth/register?app=skriptoteket"]',
    );
    expect(registerLinks.length).toBeGreaterThan(0);
    expect(registerLinks.some((link) => link.text().toLowerCase().includes("skapa"))).toBe(true);
  });
});
