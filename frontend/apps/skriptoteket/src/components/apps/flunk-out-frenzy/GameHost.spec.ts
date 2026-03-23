/**
 * Flunk-Out Frenzy game host tests.
 *
 * These tests keep the shell-to-host seam honest now that the host delegates
 * actual playfield rendering to a runtime-owned Pixi canvas.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

vi.mock("./game/render/PixiRenderer", () => {
  class MockPixiRenderer {
    private readonly canvas = document.createElement("canvas");

    static async create(): Promise<MockPixiRenderer> {
      return new MockPixiRenderer();
    }

    attach(hostElement: HTMLElement): void {
      this.canvas.dataset.test = "runtime-renderer-canvas";
      hostElement.appendChild(this.canvas);
    }

    render(): void {}

    dispose(): void {
      this.canvas.remove();
    }
  }

  return { PixiRenderer: MockPixiRenderer };
});

vi.mock("./game/audio/AudioDirector", () => {
  class MockAudioDirector {
    static async create(): Promise<MockAudioDirector> {
      return new MockAudioDirector();
    }

    setMuted(): void {}

    consumeEffects(): void {}

    dispose(): void {}
  }

  return { AudioDirector: MockAudioDirector };
});

import GameHost from "./GameHost.vue";
import type { GameHostApi, GameHudSnapshot } from "./gameHostTypes";

function hudEvents(wrapper: ReturnType<typeof mount>): GameHudSnapshot[] {
  return wrapper.emitted("hudChange")?.map(([payload]) => payload as GameHudSnapshot) ?? [];
}

async function waitForRuntime(wrapper: ReturnType<typeof mount>): Promise<void> {
  await vi.waitFor(() => {
    expect(wrapper.get("[data-test='runtime-host-placeholder']").attributes("data-runtime-mounted")).toBe("true");
  });
}

describe("GameHost", () => {
  it("renders the dedicated playfield host surface and mounts the runtime canvas", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
      },
    });

    await waitForRuntime(wrapper);

    const host = wrapper.get("[data-test='runtime-host-placeholder']");
    expect(host.attributes("aria-label")).toContain("Flunk-Out Frenzy");
    expect(wrapper.get("[data-test='runtime-renderer-canvas']").element.tagName).toBe("CANVAS");
  });

  it("emits HUD snapshots and mirrors game state on the host during a live run", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
      },
    });

    await waitForRuntime(wrapper);

    const api = wrapper.vm as unknown as GameHostApi;
    const host = wrapper.get("[data-test='runtime-host-placeholder']");

    expect(hudEvents(wrapper).at(-1)?.status).toBe("ready");
    expect(host.attributes("data-ball-present")).toBe("false");

    api.startGame();
    await wrapper.vm.$nextTick();

    expect(hudEvents(wrapper).at(-1)?.status).toBe("running");
    expect(host.attributes("data-ball-present")).toBe("true");
  });

  it("keeps runtime host state mirrored through pause, resume, and mute", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
      },
    });

    await waitForRuntime(wrapper);

    const api = wrapper.vm as unknown as GameHostApi;
    const host = wrapper.get("[data-test='runtime-host-placeholder']");

    api.startGame();
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
});
