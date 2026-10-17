/**
 * Authenticated layout tests.
 *
 * These tests verify that immersive game routes suppress the sidebar while
 * keeping the top bar and the body mode hook the bespoke game needs, and that
 * the per-user shell modes follow the signed-in user.
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
    props: ["isRail"],
    template: "<aside data-test='auth-sidebar-stub' :data-rail='isRail'>Sidebar</aside>",
  },
}));

vi.mock("./AuthTopBar.vue", () => ({
  default: {
    props: ["isImmersiveRoute", "isFocusMode", "isSidebarCollapsed"],
    template:
      "<header data-test='auth-topbar-stub' :data-immersive='isImmersiveRoute' :data-focus='isFocusMode' :data-rail='isSidebarCollapsed'>TopBar</header>",
  },
}));

describe("AuthLayout", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    document.body.classList.remove("app-shell-game-mode");
    localStorage.clear();
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
        logoutInProgress: false,
      },
      slots: {
        default: "<div>Route content</div>",
      },
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find("[data-test='auth-sidebar-stub']").exists()).toBe(false);
    expect(wrapper.find("[data-test='auth-topbar-stub']").attributes("data-immersive")).toBe("true");
    expect(wrapper.find(".auth-shell").classes()).toContain("is-immersive-route");
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

  it("rehydrates focus mode and the rail when the signed-in user changes", async () => {
    routeMocks.route.params.appId = "chemistry.reagent_prep_chef";
    localStorage.setItem("skriptoteket:layout:focus_mode:user-1", "1");
    localStorage.setItem("skriptoteket:layout:sidebar_collapsed:user-2", "1");

    const wrapper = mount(AuthLayout, {
      props: {
        user: { id: "user-1", email: "teacher@example.com", role: "user" },
        profile: null,
        aiPolicy: null,
        canSeeContributor: false,
        canSeeAdmin: false,
        canSeeSuperuser: false,
        logoutInProgress: false,
      },
      slots: {
        default: "<div>Route content</div>",
      },
    });
    const topBar = () => wrapper.get("[data-test='auth-topbar-stub']");
    const sidebar = () => wrapper.get("[data-test='auth-sidebar-stub']");

    expect(topBar().attributes("data-focus")).toBe("true");
    expect(sidebar().attributes("data-rail")).toBe("false");

    await wrapper.setProps({ user: { id: "user-2", email: "other@example.com", role: "user" } });

    expect(topBar().attributes("data-focus")).toBe("false");
    expect(topBar().attributes("data-rail")).toBe("true");
    expect(sidebar().attributes("data-rail")).toBe("true");

    await wrapper.setProps({ user: null });

    expect(topBar().attributes("data-focus")).toBe("false");
    expect(sidebar().attributes("data-rail")).toBe("false");
  });
});
