/**
 * Shared inloggning handoff panel tests.
 *
 * Purpose:
 *   Prove the login entry surface links to a browser ceremony, not an API
 *   login endpoint, and does not submit local Skriptoteket credentials.
 *
 * Relationships:
 *   - Covers the PR-0253 frontend ceremony replacement.
 */

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AuthLoginPanel from "./AuthLoginPanel.vue";

const route = vi.hoisted(() => ({
  query: { next: "/editor" },
}));

vi.mock("vue-router", () => ({
  useRoute: () => route,
}));

function mountAuthLoginPanel() {
  return mount(AuthLoginPanel, {
    global: {
      stubs: {
        RouterLink: {
          props: ["to"],
          template: "<a><slot /></a>",
        },
      },
    },
  });
}

describe("AuthLoginPanel", () => {
  beforeEach(() => {
    route.query = { next: "/editor" };
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("links to the shared inloggning ceremony with the preserved destination", () => {
    const wrapper = mountAuthLoginPanel();
    const link = wrapper.get("a.btn-primary");

    expect(link.text()).toContain("Öppna inloggningen");
    expect(link.attributes("href")).toBe(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Feditor",
    );
    expect(link.attributes("href")).not.toContain("/v1/auth/login");
    expect(wrapper.text()).toContain("Skapa ett Skriptoteket-konto");
    expect(wrapper.text()).toContain("Glömt lösenordet?");
    expect(wrapper.find("form").exists()).toBe(false);
  });

  it("uses the configured browser ceremony URL instead of the auth API base", () => {
    vi.stubEnv("VITE_HULEEDU_AUTH_BASE_URL", "https://api.example.test/");
    vi.stubEnv(
      "VITE_HULEEDU_AUTH_ENTRY_URL",
      "https://identity.example.test/login?app=skriptoteket",
    );

    const wrapper = mountAuthLoginPanel();
    const href = wrapper.get("a.btn-primary").attributes("href");

    expect(href).toBe(
      "https://identity.example.test/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Feditor",
    );
    expect(href).not.toContain("/v1/auth/login");
  });
});
