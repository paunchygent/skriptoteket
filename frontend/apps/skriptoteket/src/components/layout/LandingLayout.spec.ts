/**
 * Signed-out landing shell tests.
 *
 * These tests keep the shared signed-out header aligned with the public-entry
 * contract so unauthenticated routes expose Klassrumskartan quietly and open
 * login in place instead of navigating to an unmatched route.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LandingLayout from "./LandingLayout.vue";

const layoutMocks = vi.hoisted(() => ({
  loginOpen: vi.fn(),
  route: {
    name: "home",
    params: {},
  } as {
    name: string;
    params: Record<string, unknown>;
  },
}));

vi.mock("vue-router", () => ({
  useRoute: () => layoutMocks.route,
}));

vi.mock("../../composables/useLoginModal", () => ({
  useLoginModal: () => ({
    open: layoutMocks.loginOpen,
  }),
}));

vi.mock("../help/HelpButton.vue", () => ({
  default: {
    template: "<button type='button' data-test='help-button-stub'>Hjälp</button>",
  },
}));

describe("LandingLayout", () => {
  beforeEach(() => {
    layoutMocks.loginOpen.mockReset();
    layoutMocks.route.name = "home";
    layoutMocks.route.params = {};
  });

  it("shows the quiet public-app link and opens login in place", async () => {
    layoutMocks.route.name = "public-app-detail";
    layoutMocks.route.params = {
      appId: "classroom.group-seating-studio",
    };

    const wrapper = mount(LandingLayout, {
      slots: {
        default: "<div>Innehåll</div>",
      },
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    expect(wrapper.text()).toContain("Klassrumskartan");
    expect(wrapper.html()).toContain('href="/public/apps/classroom.group-seating-studio"');
    expect(wrapper.get("button.landing-header-link").text()).toBe("Logga in");

    await wrapper.get("button.landing-header-link").trigger("click");

    expect(layoutMocks.loginOpen).toHaveBeenCalledWith({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
    });
  });

  it("opens login with a home redirect on signed-out auth routes", async () => {
    layoutMocks.route.name = "register";

    const wrapper = mount(LandingLayout, {
      slots: {
        default: "<div>Innehåll</div>",
      },
      global: {
        stubs: {
          RouterLink: {
            props: ["to"],
            template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
          },
        },
      },
    });

    await wrapper.get("button.landing-header-link").trigger("click");

    expect(layoutMocks.loginOpen).toHaveBeenCalledWith({ name: "home" });
  });
});
