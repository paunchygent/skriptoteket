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
  return mount(AuthLoginPanel);
}

function getLinkByText(wrapper: ReturnType<typeof mountAuthLoginPanel>, text: string) {
  const link = wrapper.findAll("a").find((item) => item.text().includes(text));
  if (!link) {
    throw new Error(`Expected link containing ${text}.`);
  }
  return link;
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
    expect(getLinkByText(wrapper, "Skapa ett Skriptoteket-konto").attributes("href")).toBe(
      "https://api.hule.education/auth/register?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Feditor",
    );
    expect(getLinkByText(wrapper, "Glömt lösenordet?").attributes("href")).toBe(
      "https://api.hule.education/auth/password-reset?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Feditor",
    );
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
    expect(getLinkByText(wrapper, "Skapa ett Skriptoteket-konto").attributes("href")).toBe(
      "https://identity.example.test/auth/register?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Feditor",
    );
    expect(getLinkByText(wrapper, "Glömt lösenordet?").attributes("href")).toBe(
      "https://identity.example.test/auth/password-reset?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Feditor",
    );
  });

  it("can render a callback recovery panel with one primary login action", () => {
    const wrapper = mount(AuthLoginPanel, {
      props: {
        introCopy: "Inloggningen blev inte klar. Logga in igen för att fortsätta.",
        primaryLabel: "Logga in igen",
        showAccountLinks: false,
      },
    });

    expect(wrapper.text()).toContain("Inloggningen blev inte klar");
    expect(wrapper.get("a.btn-primary").text()).toContain("Logga in igen");
    expect(wrapper.text()).not.toContain("Skapa ett Skriptoteket-konto");
    expect(wrapper.text()).not.toContain("Glömt lösenordet?");
  });
});
