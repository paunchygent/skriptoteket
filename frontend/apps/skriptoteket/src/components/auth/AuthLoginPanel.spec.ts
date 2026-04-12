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

describe("AuthLoginPanel", () => {
  beforeEach(() => {
    route.query = { next: "/editor" };
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("links to the shared inloggning ceremony with the preserved destination", () => {
    const wrapper = mount(AuthLoginPanel);
    const link = wrapper.get("a");

    expect(link.text()).toContain("Fortsätt till inloggning");
    expect(link.attributes("href")).toBe(
      "https://api.hule.education/auth/login?app=skriptoteket&next=http%3A%2F%2Flocalhost%3A3000%2Feditor",
    );
    expect(link.attributes("href")).not.toContain("/v1/auth/login");
    expect(wrapper.find("form").exists()).toBe(false);
  });

  it("uses the configured browser ceremony URL instead of the auth API base", () => {
    vi.stubEnv("VITE_HULEEDU_AUTH_BASE_URL", "https://api.example.test/");
    vi.stubEnv(
      "VITE_HULEEDU_AUTH_ENTRY_URL",
      "https://identity.example.test/login?app=skriptoteket",
    );

    const wrapper = mount(AuthLoginPanel);
    const href = wrapper.get("a").attributes("href");

    expect(href).toBe(
      "https://identity.example.test/login?app=skriptoteket&next=http%3A%2F%2Flocalhost%3A3000%2Feditor",
    );
    expect(href).not.toContain("/v1/auth/login");
  });
});
