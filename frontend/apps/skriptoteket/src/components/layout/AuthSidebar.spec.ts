/**
 * Authenticated sidebar navigation tests.
 *
 * These tests keep the persistent shell navigation aligned with the current
 * authenticated-home/app-card contract, where the persistent rail stays
 * utility-first, proposals stay available to all signed-in users, and routed
 * app lanes are not duplicated in the sidebar or drawer.
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

function mountSidebar(visibility: SidebarRoleVisibility = {}) {
  return mount(AuthSidebar, {
    props: {
      isOpen: true,
      isFocusMode: false,
      preferXlDesktopBreakpoint: false,
      user: { email: "teacher@example.com" },
      canSeeContributor: visibility.canSeeContributor ?? false,
      canSeeAdmin: visibility.canSeeAdmin ?? false,
      canSeeSuperuser: visibility.canSeeSuperuser ?? false,
      logoutInProgress: false,
    },
    global: {
      stubs: {
        BrandLogo: true,
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
      "Mina filer",
      "Föreslå verktyg",
      "Katalog",
      "Profil",
    ]);
    expect(linkTargets.slice(0, 5)).toEqual([
      "/",
      "/vault",
      "/suggestions/new",
      "/browse",
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
    expect(linkTargets).not.toContain("/apps/documents.conversion_hub?mode=exam");
    expect(linkTargets).not.toContain("/apps/documents.conversion_hub?mode=transcript");
    expect(linkTargets).not.toContain("/editor");
    expect(linkTargets).not.toContain("/my-runs");
  });

  it("keeps contributor-only shell tools without adding Kodredigerare to the sidebar", () => {
    const wrapper = mountSidebar({ canSeeContributor: true });
    const navItemTexts = getNavItemTexts(wrapper);
    const linkTargets = getNavLinks(wrapper).map((link: SidebarNavLinkStub) => link.props("to"));

    expect(navItemTexts).toEqual([
      "Hem",
      "Mina filer",
      "Föreslå verktyg",
      "Katalog",
      "Profil",
      "Mina verktyg",
    ]);
    expect(linkTargets).toContain("/my-tools");
    expect(navItemTexts).not.toContain("Kodredigerare");
    expect(navItemTexts).not.toContain("Hjälp");
    expect(linkTargets).not.toContain("/editor");
  });
});
