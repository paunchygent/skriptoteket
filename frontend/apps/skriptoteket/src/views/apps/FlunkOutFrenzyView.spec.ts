/**
 * Flunk-Out Frenzy shell view tests.
 *
 * These tests keep the bootstrap-powered game shell honest: it should render
 * immersive loading/error/ready states, expose game-shell controls, and keep
 * bootstrap metadata tucked behind the settings surface.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FlunkOutFrenzyView from "./FlunkOutFrenzyView.vue";

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiGet,
  isApiError: (error: unknown) => {
    return (
      typeof error === "object" &&
      error !== null &&
      "name" in error &&
      error.name === "ApiError"
    );
  },
  ApiError: class ApiError extends Error {
    public readonly code: string;
    public readonly status: number;

    public constructor(params: { code: string; message: string; status: number }) {
      super(params.message);
      this.name = "ApiError";
      this.code = params.code;
      this.status = params.status;
    }
  },
}));

async function flushBootstrap(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

async function waitForRuntimeMount(wrapper: ReturnType<typeof mount>): Promise<void> {
  await vi.waitFor(() => {
    expect(wrapper.get("[data-test='runtime-host-placeholder']").attributes("data-runtime-mounted")).toBe("true");
  });
}

describe("FlunkOutFrenzyView", () => {
  it("renders a loading state while bootstrap is pending", () => {
    apiGet.mockReturnValue(new Promise(() => undefined));

    const wrapper = mount(FlunkOutFrenzyView);

    expect(wrapper.find("[data-test='bootstrap-loading']").exists()).toBe(true);
    expect(wrapper.find("[data-test='runtime-host-placeholder']").exists()).toBe(false);
  });

  it("renders the ready state from the bootstrap payload", async () => {
    apiGet.mockResolvedValue({
      app_id: "games.flunk_out_frenzy",
      title: "Flunk-Out Frenzy",
      summary: "Local browser pinball with future official high scores.",
      app_version: "app:0.2.0",
      ruleset_id: "flunk_out_frenzy.prototype_alpha.v1",
      feature_flags: {
        audio_enabled: true,
        replay_capture_enabled: false,
        score_submission_enabled: false,
      },
    });

    const wrapper = mount(FlunkOutFrenzyView);
    await flushBootstrap();
    await waitForRuntimeMount(wrapper);

    expect(apiGet).toHaveBeenCalledWith("/api/v1/apps/games.flunk_out_frenzy/bootstrap");
    expect(wrapper.find("[data-test='bootstrap-ready']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Flunk-Out Frenzy");
    expect(wrapper.find("[data-test='runtime-host-placeholder']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Starta om");
    expect(wrapper.find("[data-test='settings-panel']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("flunk_out_frenzy.prototype_alpha.v1");
  });

  it("reveals bootstrap metadata inside the settings overlay", async () => {
    apiGet.mockResolvedValue({
      app_id: "games.flunk_out_frenzy",
      title: "Flunk-Out Frenzy",
      summary: "Local browser pinball with future official high scores.",
      app_version: "app:0.2.0",
      ruleset_id: "flunk_out_frenzy.prototype_alpha.v1",
      feature_flags: {
        audio_enabled: true,
        replay_capture_enabled: false,
        score_submission_enabled: false,
      },
    });

    const wrapper = mount(FlunkOutFrenzyView);
    await flushBootstrap();
    await waitForRuntimeMount(wrapper);

    await wrapper.get("[data-test='settings-toggle']").trigger("click");

    expect(wrapper.find("[data-test='settings-panel']").exists()).toBe(true);
    expect(wrapper.find("[data-test='ruleset-id']").text()).toContain("flunk_out_frenzy.prototype_alpha.v1");
  });

  it("renders HUD updates from the runtime host instead of owning the session state locally", async () => {
    apiGet.mockResolvedValue({
      app_id: "games.flunk_out_frenzy",
      title: "Flunk-Out Frenzy",
      summary: "Local browser pinball with future official high scores.",
      app_version: "app:0.2.0",
      ruleset_id: "flunk_out_frenzy.prototype_alpha.v1",
      feature_flags: {
        audio_enabled: true,
        replay_capture_enabled: false,
        score_submission_enabled: false,
      },
    });

    const wrapper = mount(FlunkOutFrenzyView);
    await flushBootstrap();
    await waitForRuntimeMount(wrapper);

    const startButton = wrapper.findAll("button").find((button) => button.text().trim() === "Start");
    if (!startButton) {
      throw new Error("Expected Start button to exist.");
    }

    await startButton.trigger("click");

    expect(wrapper.text()).toContain("Pågående runda");

    const muteButton = wrapper.findAll("button").find((button) => button.text().includes("Ljud"));
    if (!muteButton) {
      throw new Error("Expected mute button to exist.");
    }

    await muteButton.trigger("click");
    expect(wrapper.text()).toContain("Ljud av");
  });

  it("renders an error state when bootstrap fails", async () => {
    apiGet.mockRejectedValue(
      new Error("Bootstrap failed", {
        cause: {
          name: "ApiError",
        },
      }),
    );

    const wrapper = mount(FlunkOutFrenzyView);
    await flushBootstrap();

    expect(wrapper.find("[data-test='bootstrap-error']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Bootstrap failed");
    expect(wrapper.find("[data-test='runtime-host-placeholder']").exists()).toBe(false);
  });

  it("renders the API error message when the request raises an ApiError", async () => {
    const apiError = new (await import("../../api/client")).ApiError({
        code: "HTTP_ERROR",
        message: "Bootstrap failed",
        status: 503,
      });
    apiGet.mockRejectedValue(apiError);

    const wrapper = mount(FlunkOutFrenzyView);
    await flushBootstrap();

    expect(wrapper.find("[data-test='bootstrap-error']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Bootstrap failed");
    expect(wrapper.find("[data-test='runtime-host-placeholder']").exists()).toBe(false);
  });
});
