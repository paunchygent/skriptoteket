/**
 * Authenticated layout tests.
 *
 * These tests verify that immersive game routes can suppress the generic
 * authenticated sidebar shell while preserving the shared top bar and body
 * mode hooks needed by the bespoke game experience.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthLayout from "./AuthLayout.vue";

const routeMocks = vi.hoisted(() => ({
  route: {
    name: "app-detail",
    params: {
      appId: "games.flunk_out_frenzy",
    },
  },
}));

vi.mock("vue-router", () => ({
  RouterLink: {
    template: "<a><slot /></a>",
  },
  useRoute: () => routeMocks.route,
}));

vi.mock("./AuthSidebar.vue", () => ({
  default: {
    props: ["preferXlDesktopBreakpoint"],
    template: "<aside data-test='auth-sidebar-stub' :data-prefer-xl='preferXlDesktopBreakpoint'>Sidebar</aside>",
  },
}));

vi.mock("./AuthTopBar.vue", () => ({
  default: {
    props: ["isImmersiveRoute", "preferXlDesktopBreakpoint"],
    template:
      "<header data-test='auth-topbar-stub' :data-immersive='isImmersiveRoute' :data-prefer-xl='preferXlDesktopBreakpoint'>TopBar</header>",
  },
}));

describe("AuthLayout", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    document.body.classList.remove("app-shell-game-mode");
    routeMocks.route.name = "app-detail";
    routeMocks.route.params.appId = "games.flunk_out_frenzy";
  });

  it("switches Flunk-Out Frenzy into immersive route mode", async () => {
    const wrapper = mount(AuthLayout, {
      props: {
        user: { id: "user-1", email: "teacher@example.com", role: "user" },
        profile: null,
        aiPolicy: null,
        canSeeContributor: false,
        canSeeAdmin: false,
        canSeeSuperuser: false,
        logoutError: null,
        logoutInProgress: false,
      },
      slots: {
        default: "<div>Route content</div>",
      },
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find("[data-test='auth-sidebar-stub']").exists()).toBe(false);
    expect(wrapper.find("[data-test='auth-topbar-stub']").attributes("data-immersive")).toBe("true");
    expect(wrapper.find(".auth-main-wrapper").classes()).toContain("is-immersive-route");
    expect(document.body.classList.contains("app-shell-game-mode")).toBe(true);
  });

  it("keeps the standard authenticated shell on non-immersive routes", async () => {
    routeMocks.route.params.appId = "chemistry.reagent_prep_chef";

    const wrapper = mount(AuthLayout, {
      props: {
        user: { id: "user-1", email: "teacher@example.com", role: "user" },
        profile: null,
        aiPolicy: null,
        canSeeContributor: false,
        canSeeAdmin: false,
        canSeeSuperuser: false,
        logoutError: null,
        logoutInProgress: false,
      },
      slots: {
        default: "<div>Route content</div>",
      },
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find("[data-test='auth-sidebar-stub']").exists()).toBe(true);
    expect(wrapper.find("[data-test='auth-topbar-stub']").attributes("data-immersive")).toBe("false");
    expect(document.body.classList.contains("app-shell-game-mode")).toBe(false);
  });

  it("keeps the planner route on the wider sidebar breakpoint contract", async () => {
    routeMocks.route.params.appId = "classroom.group-seating-studio";

    const wrapper = mount(AuthLayout, {
      props: {
        user: { id: "user-1", email: "teacher@example.com", role: "user" },
        profile: null,
        aiPolicy: null,
        canSeeContributor: false,
        canSeeAdmin: false,
        canSeeSuperuser: false,
        logoutError: null,
        logoutInProgress: false,
      },
      slots: {
        default: "<div>Route content</div>",
      },
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find(".auth-mobile-header").classes()).toContain(
      "auth-mobile-header--xl-sidebar-breakpoint",
    );
    expect(wrapper.find(".auth-main-wrapper").classes()).toContain(
      "auth-main-wrapper--xl-sidebar-breakpoint",
    );
    expect(wrapper.find("[data-test='auth-sidebar-stub']").attributes("data-prefer-xl")).toBe("true");
    expect(wrapper.find("[data-test='auth-topbar-stub']").attributes("data-prefer-xl")).toBe("true");
  });
});
