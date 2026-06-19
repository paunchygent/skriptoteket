/**
 * Home view tests.
 *
 * These tests keep the public landing page aligned with the current product
 * reality instead of the older open script-creation pitch.
 */

import { RouterLinkStub, flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomeView from "./HomeView.vue";

const homeMocks = vi.hoisted(() => ({
  auth: {
    isAuthenticated: false,
    hasAtLeastRole: vi.fn<(requiredRole: string) => boolean>(() => false),
    displayName: null as string | null,
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

type AuthRole = "teacher" | "contributor" | "admin";

function mountPublicHomeView() {
  return mount(HomeView, {
    global: {
      stubs: {
        RouterLink: {
          props: ["to"],
          template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
        },
      },
    },
  });
}

async function mountAuthenticatedHomeView(role: AuthRole = "teacher") {
  homeMocks.auth.isAuthenticated = true;
  homeMocks.auth.displayName = "Ada";
  homeMocks.auth.hasAtLeastRole.mockImplementation((requiredRole: string) => {
    if (role === "admin") {
      return requiredRole === "contributor" || requiredRole === "admin";
    }
    if (role === "contributor") {
      return requiredRole === "contributor";
    }
    return false;
  });

  const wrapper = mount(HomeView, {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
      },
    },
  });

  await flushPromises();
  return wrapper;
}

function findRouterLinkByText(
  wrapper: Awaited<ReturnType<typeof mountAuthenticatedHomeView>>,
  text: string,
) {
  return wrapper
    .findAllComponents(RouterLinkStub)
    .find((link) => link.text().includes(text));
}

describe("HomeView", () => {
  beforeEach(() => {
    homeMocks.auth.isAuthenticated = false;
    homeMocks.auth.displayName = null;
    homeMocks.auth.hasAtLeastRole.mockReset();
    homeMocks.auth.hasAtLeastRole.mockReturnValue(false);
    homeMocks.dashboard.loadDashboard.mockReset();
  });

  it("shows the public-entry hero hierarchy for signed-out users", () => {
    const wrapper = mountPublicHomeView();

    expect(wrapper.text()).toContain("Lektionsplanera direkt i webbläsaren.");
    expect(wrapper.text()).toContain("Klassrumskartan är en av Skriptotekets appar.");
    expect(wrapper.text()).toContain("Öppna Klassrumskartan");
    expect(wrapper.text()).toContain("skapa ett konto");
    expect(wrapper.html()).toContain('href="/public/apps/classroom.group-seating-studio"');
    expect(wrapper.html()).toContain("https://api.hule.education/auth/register");
  });

  it("renders the featured Klassrumskartan showcase and authenticated preview ledger", () => {
    const wrapper = mountPublicHomeView();

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

  it("renders arbetsappar first for authenticated users and removes the retired dashboard grid", async () => {
    const wrapper = await mountAuthenticatedHomeView();

    const workAppsSection = wrapper.get('[data-testid="home-work-apps"]');
    const secondaryLedgers = wrapper.get('[data-testid="home-secondary-ledgers"]');

    expect(workAppsSection.text()).toContain("Arbetsappar");
    expect(wrapper.text().indexOf("Arbetsappar")).toBeLessThan(
      wrapper.text().indexOf("Mina filer"),
    );
    expect(wrapper.text().indexOf("Arbetsappar")).toBeLessThan(
      wrapper.text().indexOf("Katalog"),
    );
    expect(workAppsSection.text()).toContain("Klassrumskartan");
    expect(workAppsSection.text()).toContain("Provkonverteraren");
    expect(workAppsSection.text()).toContain("Ljudtranskribering");
    expect(workAppsSection.text()).toContain("Dokumentkonverteraren");
    expect(workAppsSection.text()).toContain("Kodredigerare");
    expect(
      workAppsSection.findAll('[data-testid^="home-work-app-"]').map((app) => {
        const heading = app.find("h3");
        return heading.text();
      }),
    ).toEqual([
      "Klassrumskartan",
      "Provkonverteraren",
      "Ljudtranskribering",
      "Dokumentkonverteraren",
      "Kodredigerare",
    ]);
    expect(workAppsSection.findAll('[data-testid^="home-work-app-"] img')).toHaveLength(5);
    expect(workAppsSection.text()).not.toContain("Exam Converter");
    expect(workAppsSection.text()).not.toContain("Audio Transcription");
    expect(workAppsSection.text()).not.toContain("Document Converter");
    expect(workAppsSection.text()).not.toContain("Öppna");
    expect(wrapper.text()).not.toContain("Mina körningar");
    expect(wrapper.text()).not.toContain("Dina favoriter");
    expect(wrapper.text()).not.toContain("Senast använda");
    expect(secondaryLedgers.text()).toContain("Mina filer");
    expect(secondaryLedgers.text()).toContain("Katalog");
    expect(secondaryLedgers.text()).not.toContain("Mina verktyg");
    expect(secondaryLedgers.text()).not.toContain("Föreslå verktyg");
    expect(secondaryLedgers.text()).not.toContain("Att granska");
  });

  it("uses truthful authenticated route targets and keeps Dokumentkonverteraren non-clickable", async () => {
    const wrapper = await mountAuthenticatedHomeView();

    expect(findRouterLinkByText(wrapper, "Klassrumskartan")?.props("to")).toBe(
      "/apps/classroom.group-seating-studio",
    );
    expect(findRouterLinkByText(wrapper, "Provkonverteraren")?.props("to")).toBe(
      "/apps/documents.conversion_hub?mode=exam",
    );
    expect(findRouterLinkByText(wrapper, "Ljudtranskribering")?.props("to")).toBe(
      "/apps/documents.conversion_hub?mode=transcript",
    );
    expect(findRouterLinkByText(wrapper, "Kodredigerare")?.props("to")).toBe("/editor");
    expect(findRouterLinkByText(wrapper, "Dokumentkonverteraren")).toBeUndefined();
    expect(
      wrapper
        .get('[data-testid="home-work-app-document-converter"]')
        .attributes("data-app-linkable"),
    ).toBe("false");
  });

  it("keeps contributor and admin secondary affordances role-gated below the app shelf", async () => {
    const contributorWrapper = await mountAuthenticatedHomeView("contributor");
    const contributorLedgers = contributorWrapper.get('[data-testid="home-secondary-ledgers"]');

    expect(contributorLedgers.text()).toContain("Mina verktyg");
    expect(contributorLedgers.text()).toContain("Föreslå verktyg");
    expect(contributorLedgers.text()).not.toContain("Att granska");

    const adminWrapper = await mountAuthenticatedHomeView("admin");
    const adminLedgers = adminWrapper.get('[data-testid="home-secondary-ledgers"]');

    expect(adminLedgers.text()).toContain("Mina verktyg");
    expect(adminLedgers.text()).toContain("Föreslå verktyg");
    expect(adminLedgers.text()).toContain("Att granska");
  });
});
