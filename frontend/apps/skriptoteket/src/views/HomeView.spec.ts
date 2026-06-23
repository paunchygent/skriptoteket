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

function normalizedText(wrapper: ReturnType<typeof mountPublicHomeView>) {
  return wrapper.text().replace(/\s+/g, " ").trim();
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
    const text = normalizedText(wrapper);

    expect(text).toContain("Lektionsplanera direkt i webbläsaren.");
    expect(text).toContain(
      "Klassrumskartan är en av Skriptotekets appar. Den är öppen för alla.",
    );
    expect(text).toContain("Du behöver inget konto för att komma igång.");
    expect(text).toContain("Öppna Klassrumskartan");
    expect(text).toContain("eller skapa ett konto för att spara ditt arbete.");
    expect(wrapper.html()).toContain('href="/public/apps/classroom.group-seating-studio"');
    expect(wrapper.html()).toContain("https://api.hule.education/auth/register");
  });

  it("renders the approved signed-out authenticated app preview and removes the retired landing sections", () => {
    const wrapper = mountPublicHomeView();
    const text = normalizedText(wrapper);

    expect(text).toContain("När du loggar in");
    expect(text).toContain("Transkribera tal till text");
    expect(text).toContain("Skapa PDF:er med hjälp av HTML och CSS");
    expect(text).toContain("Skapa, redigera och konvertera prov");
    expect(text).toContain("Logga in");
    expect(text).toContain("Skapa konto");

    [
      "Skapa salen, placera eleverna, spara som PDF eller för Excel.",
      "Som inloggad är alla dina klasser, grupperingar och klassrumsplaceringar sparade.",
      "Öppna appen",
      "Skapa salen",
      "Placera eleverna",
      "Exportera",
      "Mer när du loggar in",
      "Få tillgång till fler appar och arbetsverktyg.",
      "Fler färdiga lärarverktyg",
      "Använd alla Skriptotekets appar och verktyg som finns tillgängliga.",
      "Dina förslag kan bli nya appar",
      "Berätta vilka arbetsmoment du vill slippa göra för hand.",
      "Spara arbetet över tid",
      "Kom tillbaka till dina klasser, filer, inställningar och placeringar.",
      "Kräver konto",
      "Direkt i appen",
      "01",
      "02",
      "03",
    ].forEach((copy) => {
      expect(text).not.toContain(copy);
    });
    expect(text).not.toMatch(/\bI\b/);
    expect(text).not.toMatch(/\bII\b/);
    expect(text).not.toMatch(/\bIII\b/);

    const heroPreview = wrapper.get('img[alt="Klassrum med tavla, dörr och placerade elever"]');
    expect(heroPreview.attributes("src")).toContain("hero-preview");

    const showcaseImages = wrapper.findAll('img[alt=""]');
    expect(showcaseImages).toHaveLength(3);
    expect(showcaseImages[0]?.attributes("src")).toContain("ljudtranskribering");
    expect(showcaseImages[1]?.attributes("src")).toContain("dokumentkonverteraren");
    expect(showcaseImages[2]?.attributes("src")).toContain("provkonverteraren");
    expect(showcaseImages.map((image) => image.attributes("loading"))).toEqual([
      "eager",
      "eager",
      "eager",
    ]);
    expect(showcaseImages.map((image) => image.attributes("decoding"))).toEqual([
      "sync",
      "sync",
      "sync",
    ]);
    expect(showcaseImages.map((image) => image.attributes("fetchpriority"))).toEqual([
      "high",
      "high",
      "high",
    ]);
    expect(
      wrapper.find('section[aria-labelledby="landing-authenticated-preview-heading"] svg').exists(),
    ).toBe(false);

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

  it("renders work app cards first for authenticated users and removes the retired dashboard grid", async () => {
    const wrapper = await mountAuthenticatedHomeView();

    const workAppsSection = wrapper.get('[data-testid="home-work-apps"]');
    const secondaryLedgers = wrapper.get('[data-testid="home-secondary-ledgers"]');

    expect(workAppsSection.text()).not.toContain("Arbetsappar");
    expect(wrapper.text().indexOf("Klassrumskartan")).toBeLessThan(
      wrapper.text().indexOf("Mina filer"),
    );
    expect(wrapper.text().indexOf("Klassrumskartan")).toBeLessThan(
      wrapper.text().indexOf("Katalog"),
    );
    expect(workAppsSection.text()).toContain("Klassrumskartan");
    expect(workAppsSection.text()).toContain("Provhantering");
    expect(workAppsSection.text()).toContain("Ljudtranskribering");
    expect(workAppsSection.text()).toContain("Dokumentkonvertering");
    expect(workAppsSection.text()).not.toContain("Kodredigerare");
    expect(wrapper.text()).toContain("Vad vill du göra?");
    expect(workAppsSection.text()).toContain(
      "Skapa klassrum, placera elever och exportera till PDF eller Excel.",
    );
    expect(workAppsSection.text()).toContain("Skapa, redigera och konvertera prov.");
    expect(workAppsSection.text()).toContain(
      "Transkribera tal till text och spara resultatet bland dina filer.",
    );
    expect(workAppsSection.text()).toContain(
      "Skapa PDF:er med hjälp av HTML och CSS.",
    );
    expect(workAppsSection.text()).toContain("Kommer senare");
    expect(
      workAppsSection.findAll('[data-testid^="home-work-app-"]').map((app) => {
        const heading = app.find("h3");
        return heading.text();
      }),
    ).toEqual([
      "Klassrumskartan",
      "Provhantering",
      "Ljudtranskribering",
      "Dokumentkonvertering",
    ]);
    expect(workAppsSection.findAll('[data-testid^="home-work-app-"] img')).toHaveLength(4);
    expect(workAppsSection.text()).not.toContain("Exam Converter");
    expect(workAppsSection.text()).not.toContain("Audio Transcription");
    expect(workAppsSection.text()).not.toContain("Document Converter");
    expect(workAppsSection.text()).not.toContain("Provkonverteraren");
    expect(workAppsSection.text()).not.toContain("Dokumentkonverteraren");
    expect(workAppsSection.text()).not.toContain("Öppna");
    expect(workAppsSection.text()).not.toContain("Direkt i appen");
    [
      "nästa arbetsmoment",
      "nästa steg i ditt arbete",
      "filspår",
      "transkriptarbetsyta",
      "publiceringsflödet",
      "app-första startsidan",
      "nästa arbetsflöde",
      "Visas här när arbetsytan är redo",
    ].forEach((copy) => {
      expect(wrapper.text()).not.toContain(copy);
    });
    expect(wrapper.text()).not.toContain("Mina körningar");
    expect(wrapper.text()).not.toContain("Dina favoriter");
    expect(wrapper.text()).not.toContain("Senast använda");
    expect(secondaryLedgers.text()).toContain("Filer och katalog");
    expect(secondaryLedgers.text()).toContain("Mina filer");
    expect(secondaryLedgers.text()).toContain("Öppna sparade filer och exporter.");
    expect(secondaryLedgers.text()).toContain("Katalog");
    expect(secondaryLedgers.text()).toContain(
      "Sök och filtrera bland tillgängliga verktyg.",
    );
    expect(secondaryLedgers.text()).not.toContain("Fortsätt");
    expect(secondaryLedgers.text()).not.toContain("Mina verktyg");
    expect(secondaryLedgers.text()).not.toContain("Föreslå verktyg");
    expect(secondaryLedgers.text()).not.toContain("Att granska");
  });

  it("uses truthful authenticated route targets and keeps Dokumentkonvertering non-clickable", async () => {
    const wrapper = await mountAuthenticatedHomeView();

    expect(findRouterLinkByText(wrapper, "Klassrumskartan")?.props("to")).toBe(
      "/apps/classroom.group-seating-studio",
    );
    expect(findRouterLinkByText(wrapper, "Provhantering")?.props("to")).toBe(
      "/apps/exam-converter",
    );
    expect(findRouterLinkByText(wrapper, "Ljudtranskribering")?.props("to")).toBe(
      "/apps/audio-transcription",
    );
    expect(findRouterLinkByText(wrapper, "Kodredigerare")).toBeUndefined();
    expect(findRouterLinkByText(wrapper, "Dokumentkonvertering")).toBeUndefined();
    expect(
      wrapper
        .get('[data-testid="home-work-app-document-converter"]')
        .attributes("data-app-linkable"),
    ).toBe("false");
  });

  it("keeps Kodredigerare and secondary affordances role-gated for contributors", async () => {
    const contributorWrapper = await mountAuthenticatedHomeView("contributor");
    const contributorWorkApps = contributorWrapper.get('[data-testid="home-work-apps"]');
    const contributorLedgers = contributorWrapper.get('[data-testid="home-secondary-ledgers"]');

    expect(contributorWorkApps.text()).toContain("Kodredigerare");
    expect(contributorWorkApps.text()).toContain("Fortsätt där du slutade.");
    expect(findRouterLinkByText(contributorWrapper, "Kodredigerare")?.props("to")).toBe(
      "/editor",
    );
    expect(contributorLedgers.text()).toContain("Mina verktyg");
    expect(contributorLedgers.text()).toContain("Hantera verktyg du ansvarar för.");
    expect(contributorLedgers.text()).toContain("Föreslå verktyg");
    expect(contributorLedgers.text()).toContain("Har du en idé? Skicka in ett förslag.");
    expect(contributorLedgers.text()).not.toContain("Att granska");

    const adminWrapper = await mountAuthenticatedHomeView("admin");
    const adminWorkApps = adminWrapper.get('[data-testid="home-work-apps"]');
    const adminLedgers = adminWrapper.get('[data-testid="home-secondary-ledgers"]');

    expect(adminWorkApps.text()).toContain("Kodredigerare");
    expect(adminLedgers.text()).toContain("Mina verktyg");
    expect(adminLedgers.text()).toContain("Föreslå verktyg");
    expect(adminLedgers.text()).toContain("Att granska");
    expect(adminLedgers.text()).toContain("Granska och publicera verktyg.");
  });
});
