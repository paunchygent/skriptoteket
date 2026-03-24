/**
 * Flunk-Out Frenzy game host tests.
 *
 * These tests keep the shell-to-host seam honest using an explicit runtime
 * factory instead of module-level import interception. The host should surface
 * runtime boot failures and mirror HUD state without owning simulation logic.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import GameHost from "./GameHost.vue";
import type { GameHostApi, GameHudSnapshot } from "./gameHostTypes";

class FakeRuntime {
  private hostElement: HTMLElement | null = null;
  private hudListener: ((hud: GameHudSnapshot) => void) | null = null;
  private readonly canvas = document.createElement("canvas");
  private hud: GameHudSnapshot = {
    score: 0,
    ballsRemaining: 3,
    multiplier: 1,
    status: "ready",
    muted: false,
  };

  public readonly dispose = vi.fn(() => {
    this.canvas.remove();
  });

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

  subscribeHud(listener: (hud: GameHudSnapshot) => void): () => void {
    this.hudListener = listener;
    listener(this.hud);
    return () => {
      this.hudListener = null;
    };
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

function hudEvents(wrapper: ReturnType<typeof mount>): GameHudSnapshot[] {
  return wrapper.emitted("hudChange")?.map(([payload]) => payload as GameHudSnapshot) ?? [];
}

async function waitForRuntime(wrapper: ReturnType<typeof mount>): Promise<void> {
  await vi.waitFor(() => {
    expect(wrapper.get("[data-test='runtime-host-placeholder']").attributes("data-runtime-mounted")).toBe("true");
  });
}

describe("GameHost", () => {
  it("renders the dedicated playfield host surface before the runtime is loaded", async () => {
    const runtime = new FakeRuntime();
    const runtimeFactory = vi.fn((_options) => Promise.resolve(runtime));
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
        runtimeFactory,
      },
    });

    const host = wrapper.get("[data-test='runtime-host-placeholder']");
    expect(runtimeFactory).not.toHaveBeenCalled();
    expect(host.attributes("data-runtime-load-state")).toBe("idle");
    expect(host.attributes("aria-label")).toContain("Flunk-Out Frenzy");
    expect(wrapper.find("[data-test='runtime-renderer-canvas']").exists()).toBe(false);
  });

  it("loads the runtime on Start and mounts the runtime canvas", async () => {
    const runtime = new FakeRuntime();
    const runtimeFactory = vi.fn((_options) => Promise.resolve(runtime));
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
        runtimeFactory,
      },
    });

    const api = wrapper.vm as unknown as GameHostApi;
    await api.startGame();
    await waitForRuntime(wrapper);

    expect(runtimeFactory).toHaveBeenCalledWith({ audioEnabled: true });
    expect(wrapper.get("[data-test='runtime-renderer-canvas']").element.tagName).toBe("CANVAS");
  });

  it("threads audio-disabled bootstrap policy into the runtime factory", async () => {
    const runtime = new FakeRuntime();
    const runtimeFactory = vi.fn((_options) => Promise.resolve(runtime));

    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
        audioEnabled: false,
        runtimeFactory,
      },
    });

    expect(runtimeFactory).not.toHaveBeenCalled();

    const api = wrapper.vm as unknown as GameHostApi;
    await api.startGame();

    await vi.waitFor(() => {
      expect(runtimeFactory).toHaveBeenCalledWith({ audioEnabled: false });
    });
  });

  it("emits HUD snapshots and mirrors game state on the host during a live run", async () => {
    const runtime = new FakeRuntime();
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
        runtimeFactory: (_options) => Promise.resolve(runtime),
      },
    });

    const api = wrapper.vm as unknown as GameHostApi;
    const host = wrapper.get("[data-test='runtime-host-placeholder']");

    expect(host.attributes("data-runtime-load-state")).toBe("idle");
    expect(wrapper.emitted("loadStateChange")).toBeUndefined();
    expect(host.attributes("data-ball-present")).toBe("false");

    await api.startGame();
    await waitForRuntime(wrapper);
    await wrapper.vm.$nextTick();

    expect(hudEvents(wrapper).at(-1)?.status).toBe("running");
    expect(host.attributes("data-ball-present")).toBe("true");
  });

  it("keeps runtime host state mirrored through pause, resume, and mute", async () => {
    const runtime = new FakeRuntime();
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
        runtimeFactory: (_options) => Promise.resolve(runtime),
      },
    });

    const api = wrapper.vm as unknown as GameHostApi;
    const host = wrapper.get("[data-test='runtime-host-placeholder']");

    await api.startGame();
    await waitForRuntime(wrapper);
    api.pauseGame();
    await wrapper.vm.$nextTick();
    expect(hudEvents(wrapper).at(-1)?.status).toBe("paused");
    expect(host.attributes("data-runtime-status")).toBe("paused");

    api.resumeGame();
    await wrapper.vm.$nextTick();
    expect(hudEvents(wrapper).at(-1)?.status).toBe("running");

    api.setMuted(true);
    await wrapper.vm.$nextTick();
    expect(hudEvents(wrapper).at(-1)?.muted).toBe(true);
    expect(host.attributes("data-runtime-muted")).toBe("true");
  });

  it("surfaces runtime boot errors instead of leaving the cabinet inert", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
        runtimeFactory: (_options) => Promise.reject(new Error("WebGL init failed.")),
      },
    });

    const api = wrapper.vm as unknown as GameHostApi;
    await api.startGame();

    await vi.waitFor(() => {
      expect(wrapper.get("[data-test='runtime-error']").text()).toContain("WebGL init failed.");
    });

    expect(wrapper.emitted("bootError")?.at(-1)?.[0]).toBe("WebGL init failed.");
    expect(wrapper.find("[data-test='runtime-renderer-canvas']").exists()).toBe(false);
  });
});
