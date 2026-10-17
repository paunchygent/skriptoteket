/**
 * Authenticated sidebar navigation tests.
 *
 * These tests keep the shell navigation in the order of the approved app-shell
 * prototype (TASK-SKRIPT-40-04-01): utility links first, proposals available
 * to all signed-in users, admin links under Administration, and routed app
 * lanes not duplicated in the sidebar, rail or drawer.
 */

import { RouterLinkStub, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AuthSidebar from "./AuthSidebar.vue";

type SidebarRoleVisibility = {
  canSeeContributor?: boolean;
  canSeeAdmin?: boolean;
  canSeeSuperuser?: boolean;
};

type SidebarNavLinkStub = {
  text: () => string;
  props: (name: string) => unknown;
};

function mountSidebar(visibility: SidebarRoleVisibility = {}, isOpen = true) {
  return mount(AuthSidebar, {
    props: {
      isOpen,
      isRail: false,
      isFocusMode: false,
      user: { email: "teacher@example.com" },
      canSeeContributor: visibility.canSeeContributor ?? false,
      canSeeAdmin: visibility.canSeeAdmin ?? false,
      canSeeSuperuser: visibility.canSeeSuperuser ?? false,
      logoutInProgress: false,
    },
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
      },
    },
  });
}

function getNavLinks(wrapper: ReturnType<typeof mountSidebar>) {
  return wrapper.find(".sidebar-nav").findAllComponents(RouterLinkStub);
}

function getNavItemTexts(wrapper: ReturnType<typeof mountSidebar>) {
  return wrapper
    .find(".sidebar-nav")
    .findAll(".sidebar-nav-item")
    .map((item) => item.text().trim());
}

describe("AuthSidebar", () => {
  it("shows normal signed-in users the approved utility link order without duplicating app cards or help", () => {
    const wrapper = mountSidebar();
    const navLinks = getNavLinks(wrapper);
    const navItemTexts = getNavItemTexts(wrapper);
    const linkTargets = navLinks.map((link: SidebarNavLinkStub) => link.props("to"));

    expect(navItemTexts).toEqual([
      "Hem",
      "Katalog",
      "Mina filer",
      "Föreslå verktyg",
      "Profil",
    ]);
    expect(linkTargets).toEqual([
      "/",
      "/browse",
      "/vault",
      "/suggestions/new",
      "/profile",
    ]);
    expect(navItemTexts).not.toContain("Kodredigerare");
    expect(navItemTexts).not.toContain("Klassrumskartan");
    expect(navItemTexts).not.toContain("Provhantering");
    expect(navItemTexts).not.toContain("Ljudtranskribering");
    expect(navItemTexts).not.toContain("Hjälp");
    expect(wrapper.text()).not.toContain("Appar");
    expect(wrapper.text()).not.toContain("Plattform");
    expect(wrapper.text()).not.toContain("Vad du gör");
    expect(wrapper.text()).not.toContain("Nytta");
    expect(wrapper.text()).not.toContain("Mina körningar");
    expect(linkTargets).not.toContain("/apps/classroom.group-seating-studio");
    expect(linkTargets).not.toContain("/apps/exam-converter");
    expect(linkTargets).not.toContain("/apps/audio-transcription");
    expect(linkTargets).not.toContain("/editor");
    expect(linkTargets).not.toContain("/my-runs");
  });

  it("keeps contributor-only shell tools without adding Kodredigerare to the sidebar", () => {
    const wrapper = mountSidebar({ canSeeContributor: true });
    const navItemTexts = getNavItemTexts(wrapper);
    const linkTargets = getNavLinks(wrapper).map((link: SidebarNavLinkStub) => link.props("to"));

    expect(navItemTexts).toEqual([
      "Hem",
      "Katalog",
      "Mina filer",
      "Mina verktyg",
      "Föreslå verktyg",
      "Profil",
    ]);
    expect(linkTargets).toContain("/my-tools");
    expect(navItemTexts).not.toContain("Kodredigerare");
    expect(navItemTexts).not.toContain("Hjälp");
    expect(linkTargets).not.toContain("/editor");
  });

  it("puts the admin links under Administration and keeps Användare for superusers", () => {
    const admin = mountSidebar({ canSeeContributor: true, canSeeAdmin: true });

    expect(admin.find(".sidebar-section").text()).toBe("Administration");
    expect(getNavItemTexts(admin).slice(-2)).toEqual(["Hantera verktyg", "Granska förslag"]);
    expect(getNavItemTexts(admin)).not.toContain("Användare");

    const superuser = mountSidebar({
      canSeeContributor: true,
      canSeeAdmin: true,
      canSeeSuperuser: true,
    });

    expect(getNavItemTexts(superuser).slice(-3)).toEqual([
      "Hantera verktyg",
      "Granska förslag",
      "Användare",
    ]);
  });

  it("shows no Administration heading to users without admin links", () => {
    const wrapper = mountSidebar({ canSeeContributor: true });

    expect(wrapper.find(".sidebar-section").exists()).toBe(false);
  });

  it("dismisses only an open drawer on Escape", async () => {
    const closed = mountSidebar({}, false);
    await closed.get("nav").trigger("keydown", { key: "Escape" });
    expect(closed.emitted("dismiss")).toBeUndefined();

    const open = mountSidebar({}, true);
    await open.get("nav").trigger("keydown", { key: "Escape" });
    expect(open.emitted("dismiss")).toHaveLength(1);
  });

  it("names every rail link through its tooltip so the glyph-only rail stays labelled", () => {
    const wrapper = mountSidebar({ canSeeContributor: true, canSeeAdmin: true, canSeeSuperuser: true });

    for (const item of wrapper.find(".sidebar-nav").findAll(".sidebar-nav-item")) {
      expect(item.attributes("title")).toBe(item.text().trim());
    }
  });
});
