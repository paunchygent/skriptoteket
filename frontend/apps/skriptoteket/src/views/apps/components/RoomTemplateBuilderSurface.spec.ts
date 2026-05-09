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

function setHoverCapableViewport(): void {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn().mockReturnValue({
      matches: false,
      media: "(hover: none), (pointer: coarse)",
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

describe("RoomTemplateBuilderSurface", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    setViewportSize(800, 600);
    setHoverCapableViewport();
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

  it("suppresses ghost previews after touch input while keeping pointer hover available", async () => {
    const wrapper = mount(RoomTemplateBuilderSurface, {
      props: {
        roomGrid: { cols: 14, rows: 9 },
        seats: [],
        fixtures: [],
        ghostPlacement: {
          row: 0,
          col: 2,
          width: 3,
          height: 1,
          wallSide: "top",
          type: "whiteboard",
          canPlace: true,
        },
        ghostRenderableFixture: {
          id: "ghost-whiteboard",
          type: "whiteboard",
          x: 192,
          y: 0,
          width: 288,
          height: 96,
          label: "Whiteboard",
        },
        builderScale: 0.8,
        builderScaledSurfaceStyle: { width: "1120px", height: "768px" },
        builderScalePercent: 80,
      },
    });

    expect(wrapper.find('[data-test="room-builder-ghost-overlay"]').exists()).toBe(true);

    const firstCell = wrapper.find(".planner-grid-node-button");
    await firstCell.trigger("pointerdown", { pointerType: "touch" });
    expect(wrapper.emitted("clear-hover")).toHaveLength(1);
    expect(wrapper.find('[data-test="room-builder-ghost-overlay"]').exists()).toBe(false);

    await firstCell.trigger("mousemove", { clientX: 8, clientY: 8 });
    expect(wrapper.find('[data-test="room-builder-ghost-overlay"]').exists()).toBe(true);
  });
});
