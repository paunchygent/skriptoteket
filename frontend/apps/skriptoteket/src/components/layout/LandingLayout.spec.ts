/**
 * Signed-out landing shell tests.
 *
 * These tests keep the shared signed-out header aligned with the public-entry
 * contract so the hero owns the Klassrumskartan CTA while the header keeps a
 * simple shared-auth login action plus help entry.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LandingLayout from "./LandingLayout.vue";

const layoutMocks = vi.hoisted(() => ({
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

vi.mock("../help/HelpButton.vue", () => ({
  default: {
    template: "<button type='button' data-test='help-button-stub'>Hjälp</button>",
  },
}));

describe("LandingLayout", () => {
  beforeEach(() => {
    layoutMocks.route.name = "home";
    layoutMocks.route.params = {};
  });

  it("keeps only login and help as header actions and opens login through the HuleEdu ceremony", () => {
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

    expect(wrapper.text()).not.toContain("Klassrumskartan");
    expect(wrapper.find('nav[aria-label="Publika genvägar"]').exists()).toBe(false);

    const headerActions = wrapper.get(".landing-header-actions");
    const loginLink = wrapper.get("a.landing-header-link");

    expect(headerActions.text()).toContain("Logga in");
    expect(headerActions.text()).toContain("Hjälp");
    expect(loginLink.text()).toBe("Logga in");
    expect(loginLink.attributes("href")).toBe(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Fapps%2Fclassroom.group-seating-studio",
    );
  });

  it("opens login with a home redirect on signed-out auth routes", () => {
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

    expect(wrapper.get("a.landing-header-link").attributes("href")).toBe(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2F",
    );
  });
});
