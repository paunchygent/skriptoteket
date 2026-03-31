import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RoomTemplateBuilderSurface from "./RoomTemplateBuilderSurface.vue";

class ResizeObserverMock {
  observe(): void {}
  disconnect(): void {}
}

function setViewportSize(width: number, height: number): void {
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get: () => width,
  });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get: () => height,
  });
}

describe("RoomTemplateBuilderSurface", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    setViewportSize(800, 600);
  });

  it("anchors the zoomed builder surface to the left edge when it overflows horizontally", async () => {
    const wrapper = mount(RoomTemplateBuilderSurface, {
      props: {
        roomGrid: { cols: 14, rows: 9 },
        seats: [],
        fixtures: [],
        ghostPlacement: null,
        ghostRenderableFixture: null,
        builderScale: 0.8,
        builderScaledSurfaceStyle: { width: "1120px", height: "768px" },
        builderScalePercent: 80,
      },
      global: {
        stubs: {
          RoomSceneSurface: { template: "<div />" },
          RoomSeatToken: { template: "<div />" },
          RoomFixtureArtwork: { template: "<div />" },
        },
      },
    });

    await nextTick();

    expect(wrapper.get('[data-test="room-builder-scroll-frame"]').attributes("data-overflow-anchor")).toBe("start");
    expect(wrapper.get('[data-test="room-builder-scroll-frame"]').attributes("style")).toBeUndefined();
    expect(wrapper.get('[data-test="room-builder-surface-shell"]').classes()).toContain("px-6");
    expect(wrapper.get('[data-test="room-builder-surface-shell"]').classes()).toContain("py-6");
  });

  it("keeps the builder heading but removes the incorrect geometry helper copy", () => {
    const wrapper = mount(RoomTemplateBuilderSurface, {
      props: {
        roomGrid: { cols: 14, rows: 9 },
        seats: [],
        fixtures: [],
        ghostPlacement: null,
        ghostRenderableFixture: null,
        builderScale: 0.8,
        builderScaledSurfaceStyle: { width: "1120px", height: "768px" },
        builderScalePercent: 80,
      },
      global: {
        stubs: {
          RoomSceneSurface: { template: "<div />" },
          RoomSeatToken: { template: "<div />" },
          RoomFixtureArtwork: { template: "<div />" },
        },
      },
    });

    expect(wrapper.text()).toContain("Klassrumsyta");
    expect(wrapper.text()).not.toContain(
      "Anpassa vyn utan att ändra klassrummets sparade geometri.",
    );
  });
});
