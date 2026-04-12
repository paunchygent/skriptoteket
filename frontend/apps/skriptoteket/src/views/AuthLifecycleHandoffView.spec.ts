/**
 * Lifecycle handoff view tests.
 *
 * Purpose:
 *   Prove legacy Skriptoteket account lifecycle routes hand off to HuleEdu
 *   Gateway browser ceremonies without rendering local forms or API actions.
 *
 * Relationships:
 *   - Covers `PR-0257` consumer-side route compatibility.
 *   - Complements `sharedAuth.spec.ts` helper-level ceremony URL coverage.
 */

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AuthLifecycleHandoffView from "./AuthLifecycleHandoffView.vue";

const route = vi.hoisted(() => ({
  name: "register" as string,
  query: {} as Record<string, unknown>,
}));

vi.mock("vue-router", () => ({
  useRoute: () => route,
}));

function mountLifecycleHandoffView() {
  return mount(AuthLifecycleHandoffView, {
    global: {
      stubs: {
        RouterLink: {
          props: ["to"],
          template: "<a data-test='router-link'><slot /></a>",
        },
      },
    },
  });
}

describe("AuthLifecycleHandoffView", () => {
  beforeEach(() => {
    route.name = "register";
    route.query = {};
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("hands registration to the HuleEdu standalone registration ceremony", () => {
    route.query = { next: "/apps/classroom.group-seating-studio" };

    const wrapper = mountLifecycleHandoffView();
    const link = wrapper.get("a.btn-primary");

    expect(wrapper.text()).toContain("Skapa konto");
    expect(link.text()).toContain("Fortsätt till registrering");
    expect(link.attributes("href")).toBe(
      "https://api.hule.education/auth/register?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Fapps%2Fclassroom.group-seating-studio",
    );
    expect(wrapper.find("form").exists()).toBe(false);
  });

  it("hands forgot-password to password reset without a token", () => {
    route.name = "forgot-password";

    const wrapper = mountLifecycleHandoffView();
    const href = wrapper.get("a.btn-primary").attributes("href");

    expect(wrapper.text()).toContain("Återställ lösenord");
    expect(href).toContain("https://api.hule.education/auth/password-reset?");
    expect(href).not.toContain("token=");
    expect(href).not.toContain("/v1/auth/request-password-reset");
  });

  it("preserves reset tokens through the HuleEdu password reset ceremony", () => {
    route.name = "reset-password";
    route.query = {
      token: "reset-token",
      next: "/editor?draft=head#debug",
    };

    const wrapper = mountLifecycleHandoffView();
    const url = new URL(wrapper.get("a.btn-primary").attributes("href") ?? "");

    expect(`${url.origin}${url.pathname}`).toBe("https://api.hule.education/auth/password-reset");
    expect(url.searchParams.get("token")).toBe("reset-token");
    expect(url.searchParams.get("next")).toBe("/editor?draft=head#debug");
  });

  it("preserves verification tokens and drops hostile next values", () => {
    route.name = "verify-email";
    route.query = {
      token: "verification-token",
      next: "https://evil.example/phish",
    };

    const wrapper = mountLifecycleHandoffView();
    const url = new URL(wrapper.get("a.btn-primary").attributes("href") ?? "");

    expect(`${url.origin}${url.pathname}`).toBe(
      "https://api.hule.education/auth/email-verification",
    );
    expect(url.searchParams.get("token")).toBe("verification-token");
    expect(url.searchParams.has("next")).toBe(false);
    expect(wrapper.find("form").exists()).toBe(false);
  });
});
