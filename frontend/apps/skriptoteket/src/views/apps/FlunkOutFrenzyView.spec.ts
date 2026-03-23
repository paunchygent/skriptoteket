/**
 * Flunk-Out Frenzy shell view tests.
 *
 * These tests keep the bootstrap-powered game shell honest: it should render
 * immersive loading/error/ready states, expose game-shell controls, and keep
 * runtime boot failures visible at the route layer via an explicit runtime
 * factory seam.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FlunkOutFrenzyView from "./FlunkOutFrenzyView.vue";
import type {
  GameHudSnapshot,
  GameRuntimeFactoryOptions,
} from "../../components/apps/flunk-out-frenzy/gameHostTypes";

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

class FakeRuntime {
  private hostElement: HTMLElement | null = null;
  private hudListener: ((payload: GameHudSnapshot) => void) | null = null;
  private readonly canvas = document.createElement("canvas");
  private hud: GameHudSnapshot = {
    score: 0,
    ballsRemaining: 3,
    multiplier: 1,
    status: "ready",
    muted: false,
  };

  mount(hostElement: HTMLElement): void {
    this.hostElement = hostElement;
    this.canvas.dataset.test = "runtime-renderer-canvas";
    hostElement.appendChild(this.canvas);
    this.syncHost();
  }

  start(): void {
    this.hud = {
      ...this.hud,
      status: "running",
    };
    this.syncHost({ ballPresent: "true" });
    this.publishHud();
  }

  pause(): void {
    this.hud = {
      ...this.hud,
      status: "paused",
    };
    this.syncHost();
    this.publishHud();
  }

  resume(): void {
    this.hud = {
      ...this.hud,
      status: "running",
    };
    this.syncHost();
    this.publishHud();
  }

  restart(): void {
    this.hud = {
      score: 0,
      ballsRemaining: 3,
      multiplier: 1,
      status: "running",
      muted: this.hud.muted,
    };
    this.syncHost({ ballPresent: "true" });
    this.publishHud();
  }

  setMuted(muted: boolean): void {
    this.hud = {
      ...this.hud,
      muted,
    };
    this.syncHost();
    this.publishHud();
  }

  subscribeHud(listener: (payload: GameHudSnapshot) => void): () => void {
    this.hudListener = listener;
    listener(this.hud);
    return () => {
      this.hudListener = null;
    };
  }

  dispose(): void {
    this.canvas.remove();
  }

  injectMachineEventsForDebug(): void {}

  enqueueCommand(): void {}

  private publishHud(): void {
    this.hudListener?.(this.hud);
  }

  private syncHost(overrides: { ballPresent?: string } = {}): void {
    if (!this.hostElement) {
      return;
    }

    this.hostElement.dataset.runtimeMounted = "true";
    this.hostElement.dataset.runtimeStatus = this.hud.status;
    this.hostElement.dataset.runtimeMuted = String(this.hud.muted);
    this.hostElement.dataset.ballPresent = overrides.ballPresent ?? "false";
  }
}

async function flushBootstrap(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

async function waitForRuntimeMount(wrapper: ReturnType<typeof mount>): Promise<void> {
  await vi.waitFor(() => {
    expect(wrapper.get("[data-test='runtime-host-placeholder']").attributes("data-runtime-mounted")).toBe("true");
  });
}

function bootstrapPayload() {
  return {
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
  };
}

describe("FlunkOutFrenzyView", () => {
  it("renders a loading state while bootstrap is pending", () => {
    apiGet.mockReturnValue(new Promise(() => undefined));

    const wrapper = mount(FlunkOutFrenzyView);

    expect(wrapper.find("[data-test='bootstrap-loading']").exists()).toBe(true);
    expect(wrapper.find("[data-test='runtime-host-placeholder']").exists()).toBe(false);
  });

  it("renders the ready state from the bootstrap payload", async () => {
    apiGet.mockResolvedValue(bootstrapPayload());

    const wrapper = mount(FlunkOutFrenzyView, {
      props: {
        runtimeFactory: (_options) => Promise.resolve(new FakeRuntime()),
      },
    });
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
    apiGet.mockResolvedValue(bootstrapPayload());

    const wrapper = mount(FlunkOutFrenzyView, {
      props: {
        runtimeFactory: (_options) => Promise.resolve(new FakeRuntime()),
      },
    });
    await flushBootstrap();
    await waitForRuntimeMount(wrapper);

    await wrapper.get("[data-test='settings-toggle']").trigger("click");

    expect(wrapper.find("[data-test='settings-panel']").exists()).toBe(true);
    expect(wrapper.find("[data-test='ruleset-id']").text()).toContain("flunk_out_frenzy.prototype_alpha.v1");
  });

  it("renders HUD updates from the runtime host instead of owning the session state locally", async () => {
    apiGet.mockResolvedValue(bootstrapPayload());

    const wrapper = mount(FlunkOutFrenzyView, {
      props: {
        runtimeFactory: (_options) => Promise.resolve(new FakeRuntime()),
      },
    });
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

  it("renders a route-visible runtime error when the playfield runtime fails to boot", async () => {
    apiGet.mockResolvedValue(bootstrapPayload());

    const wrapper = mount(FlunkOutFrenzyView, {
      props: {
        runtimeFactory: (_options) => Promise.reject(new Error("Pixi failed to initialize.")),
      },
    });
    await flushBootstrap();

    await vi.waitFor(() => {
      expect(wrapper.get("[data-test='runtime-route-error']").text()).toContain("Pixi failed to initialize.");
    });

    const startButton = wrapper.findAll("button").find((button) => button.text().trim() === "Start");
    if (!startButton) {
      throw new Error("Expected Start button to exist.");
    }

    expect(startButton.attributes("disabled")).toBeDefined();
  });

  it("disables runtime audio controls and passes audio policy into the host when bootstrap disables audio", async () => {
    apiGet.mockResolvedValue({
      ...bootstrapPayload(),
      feature_flags: {
        audio_enabled: false,
        replay_capture_enabled: false,
        score_submission_enabled: false,
      },
    });

    const runtimeFactory = vi.fn((_options: GameRuntimeFactoryOptions) => {
      return Promise.resolve(new FakeRuntime());
    });

    const wrapper = mount(FlunkOutFrenzyView, {
      props: {
        runtimeFactory,
      },
    });
    await flushBootstrap();
    await waitForRuntimeMount(wrapper);

    expect(runtimeFactory).toHaveBeenCalledWith({ audioEnabled: false });

    const muteButton = wrapper.findAll("button").find((button) => button.text().includes("Ljud"));
    if (!muteButton) {
      throw new Error("Expected mute button to exist.");
    }

    expect(muteButton.text()).toContain("Ljud avstängt");
    expect(muteButton.attributes("disabled")).toBeDefined();
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
