/**
 * Flunk-Out Frenzy game host tests.
 *
 * These tests keep the shell-to-host seam honest now that the host renders a
 * live prototype-alpha view surface instead of a placeholder mount badge.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

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
  it("renders the dedicated playfield host surface", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
      },
    });

    await waitForRuntime(wrapper);

    const host = wrapper.get("[data-test='runtime-host-placeholder']");
    expect(host.attributes("aria-label")).toContain("Flunk-Out Frenzy");
    expect(wrapper.find("[data-test='runtime-flipper-left']").exists()).toBe(true);
    expect(wrapper.find("[data-test='runtime-flipper-right']").exists()).toBe(true);
  });

  it("emits HUD snapshots and renders a live ball when the game starts", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
      },
    });

    await waitForRuntime(wrapper);

    const api = wrapper.vm as unknown as GameHostApi;
    expect(hudEvents(wrapper).at(-1)?.status).toBe("ready");
    expect(wrapper.find("[data-test='runtime-ball']").exists()).toBe(false);

    api.startGame();
    await wrapper.vm.$nextTick();

    expect(hudEvents(wrapper).at(-1)?.status).toBe("running");
    expect(wrapper.find("[data-test='runtime-ball']").exists()).toBe(true);
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

  it("renders the right flipper with the mirrored display angle when pressed", async () => {
    const wrapper = mount(GameHost, {
      props: {
        title: "Flunk-Out Frenzy",
      },
      attachTo: document.body,
    });

    await waitForRuntime(wrapper);

    const api = wrapper.vm as unknown as GameHostApi;
    api.startGame();
    await wrapper.vm.$nextTick();

    const rightFlipper = wrapper.get("[data-test='runtime-flipper-right']");
    expect(rightFlipper.attributes("style")).toContain("rotate(-18deg)");

    window.dispatchEvent(new KeyboardEvent("keydown", { code: "ShiftRight" }));

    await vi.waitFor(() => {
      expect(rightFlipper.attributes("style")).toContain("rotate(24deg)");
    });

    window.dispatchEvent(new KeyboardEvent("keyup", { code: "ShiftRight" }));
    await wrapper.unmount();
  });
});
