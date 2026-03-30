/**
 * Register view tests.
 *
 * These tests cover the early-release registration UX: inline preflight
 * feedback, password visibility toggles, and successful submit wiring.
 */

import { mount, flushPromises } from "@vue/test-utils";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import RegisterView from "./RegisterView.vue";

const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
  replace: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  isAuthenticated: false,
  bootstrap: vi.fn(),
  register: vi.fn(),
}));

const apiMocks = vi.hoisted(() => ({
  apiPost: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("vue-router", () => ({
  RouterLink: {
    props: ["to"],
    template: "<a :href=\"typeof to === 'string' ? to : '#'\"><slot /></a>",
  },
  useRouter: () => routerMocks,
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: () => authState,
}));

vi.mock("../api/client", () => ({
  apiPost: apiMocks.apiPost,
  isApiError: apiMocks.isApiError,
}));

describe("RegisterView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    routerMocks.push.mockReset();
    routerMocks.replace.mockReset();
    authState.isAuthenticated = false;
    authState.bootstrap.mockReset();
    authState.bootstrap.mockResolvedValue(undefined);
    authState.register.mockReset();
    authState.register.mockResolvedValue({
      message: "Konto skapat! Kontrollera din e-post för att verifiera kontot.",
    });
    apiMocks.apiPost.mockReset();
    apiMocks.isApiError.mockReset();
    apiMocks.isApiError.mockReturnValue(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows inline domain feedback while the user types", async () => {
    apiMocks.apiPost.mockResolvedValue({
      email: {
        status: "invalid",
        message:
          "Endast anställda hos kommuner och enskilda huvudmän kan registrera sig just nu. Använd din e-postadress från kommun eller enskild huvudman.",
      },
      password: {
        status: "incomplete",
        message: null,
      },
    });

    const wrapper = mount(RegisterView);
    await flushPromises();

    await wrapper.get("#register-email").setValue("teacher@gmail.com");
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();

    expect(wrapper.text()).toContain(
      "Endast anställda hos kommuner och enskilda huvudmän kan registrera sig just nu.",
    );
  });

  it("lets the user reveal the password they entered", async () => {
    const wrapper = mount(RegisterView);
    await flushPromises();

    const passwordInput = wrapper.get("#register-password");
    expect(passwordInput.attributes("type")).toBe("password");

    await wrapper.get('button[aria-label="Visa lösenord"]').trigger("click");

    expect(wrapper.get("#register-password").attributes("type")).toBe("text");
  });

  it("shows verification guidance after successful registration", async () => {
    apiMocks.apiPost.mockResolvedValue({
      email: {
        status: "valid",
        message: null,
      },
      password: {
        status: "valid",
        message: null,
      },
    });

    const wrapper = mount(RegisterView);
    await flushPromises();

    await wrapper.get("#first-name").setValue("Ada");
    await wrapper.get("#last-name").setValue("Lovelace");
    await wrapper.get("#register-email").setValue("teacher@harryda.se");
    await wrapper.get("#register-password").setValue("password123");
    await wrapper.get("#register-confirm").setValue("password123");
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();

    await wrapper.get("form").trigger("submit.prevent");

    expect(authState.register).toHaveBeenCalledWith({
      email: "teacher@harryda.se",
      password: "password123",
      firstName: "Ada",
      lastName: "Lovelace",
    });
    expect(routerMocks.push).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Kontrollera din e-post");
    expect(wrapper.text()).toContain(
      "Konto skapat! Kontrollera din e-post för att verifiera kontot.",
    );
    expect(wrapper.text()).toContain(
      "Om du inte ser något mejl från noreply@hule.education i din inkorg, kontrollera din skräppost.",
    );
  });
});
