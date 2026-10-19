/**
 * Exam workspace anchored floating position.
 *
 * Expected behavior:
 *   A floating panel (the gap popover) stays fully visible next to its
 *   anchor chip: below the chip while there is room, flipped above it when
 *   the space below is smaller than its height, clamped to the viewport
 *   edges, capped to the available viewport height, and repositioned on
 *   window resize and on scroll of any ancestor. When ancestor scrolling
 *   moves the anchor outside the viewport, the shown panel range stays
 *   inside the viewport edges and its cap never exceeds the viewport
 *   budget. All listeners are removed when the calling component unmounts.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";
import type { DeepReadonly, Ref } from "vue";

import { ANCHORED_EDGE_PX, useExamWorkspaceAnchoredPosition } from "./useExamWorkspaceAnchoredPosition";
import type { AnchoredPosition } from "./useExamWorkspaceAnchoredPosition";

const VIEWPORT = { width: 1024, height: 768 };
const VIEWPORT_BUDGET = VIEWPORT.height - 2 * ANCHORED_EDGE_PX;
const VIEWPORT_MAX = VIEWPORT.height - ANCHORED_EDGE_PX;

function stubViewport(): void {
  vi.stubGlobal("innerWidth", VIEWPORT.width);
  vi.stubGlobal("innerHeight", VIEWPORT.height);
}

/** Anchor rect; only the read fields are stubbed. */
function stubAnchorRect(element: HTMLElement, rect: { left: number; top: number; bottom: number }): void {
  vi.spyOn(element, "getBoundingClientRect").mockReturnValue({
    left: rect.left,
    top: rect.top,
    bottom: rect.bottom,
    right: rect.left,
    width: 0,
    height: 0,
    x: rect.left,
    y: rect.top,
    toJSON: () => ({}),
  });
}

/** jsdom has no layout, so the floating size is stubbed. */
function stubFloatingSize(element: HTMLElement, size: { height: number; width: number }): void {
  Object.defineProperty(element, "scrollHeight", { configurable: true, value: size.height });
  Object.defineProperty(element, "offsetWidth", { configurable: true, value: size.width });
}

interface HostState {
  anchor: Ref<HTMLElement | null>;
  floating: Ref<HTMLElement | null>;
  position: DeepReadonly<Ref<AnchoredPosition>>;
  place: () => void;
}

let hostState: HostState | undefined;

const Host = defineComponent({
  setup() {
    const anchor = ref<HTMLElement | null>(null);
    const floating = ref<HTMLElement | null>(null);
    const { position, place } = useExamWorkspaceAnchoredPosition(anchor, floating);
    hostState = { anchor, floating, position, place };
    return () =>
      h("div", [
        h("button", { ref: anchor }, "chip"),
        h("div", { ref: floating }, "popover"),
      ]);
  },
});

function requireHostState(): HostState {
  if (hostState === undefined) {
    throw new Error("Expected the host to be mounted.");
  }
  return hostState;
}

function requireElement(value: HTMLElement | null): HTMLElement {
  if (value === null) {
    throw new Error("Expected an element ref to be set.");
  }
  return value;
}

async function mountHost(
  anchorRect: { left: number; top: number; bottom: number },
  floatingSize: { height: number; width: number },
) {
  stubViewport();
  hostState = undefined;
  const wrapper = mount(Host, { attachTo: document.body });
  await nextTick();
  await nextTick();
  const state = requireHostState();
  stubAnchorRect(requireElement(state.anchor.value), anchorRect);
  stubFloatingSize(requireElement(state.floating.value), floatingSize);
  state.place();
  await nextTick();
  return { wrapper, state };
}

describe("useExamWorkspaceAnchoredPosition", () => {
  it("places the panel below the anchor while there is room", async () => {
    const { wrapper, state } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 200, width: 300 });
    const position = state.position.value;
    expect(position.placement).toBe("below");
    expect(position.top).toBe(264);
    expect(position.left).toBe(180);
    // 768 - 260 - 4 - 8 below; the 200 px panel fits, so no cap.
    expect(position.maxHeight).toBe(496);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("flips above the anchor when the space below is smaller than its height", async () => {
    const { wrapper, state } = await mountHost({ left: 180, top: 680, bottom: 700 }, { height: 200, width: 300 });
    const position = state.position.value;
    expect(position.placement).toBe("above");
    // Shown fully: 680 - 4 - 200.
    expect(position.top).toBe(476);
    expect(position.left).toBe(180);
    expect(position.top + Math.min(200, position.maxHeight)).toBeLessThanOrEqual(
      VIEWPORT.height - 8,
    );
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("clamps the left edge at the right viewport edge and at the viewport edge", async () => {
    const wide = await mountHost({ left: 900, top: 240, bottom: 260 }, { height: 100, width: 300 });
    // 1024 - 300 - 8 = 716.
    expect(wide.state.position.value.left).toBe(716);
    wide.wrapper.unmount();

    const narrow = await mountHost({ left: 2, top: 240, bottom: 260 }, { height: 100, width: 300 });
    expect(narrow.state.position.value.left).toBe(8);
    narrow.wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("caps the height so the panel never leaves the viewport", async () => {
    // A 700 px panel with 496 px below and 228 px above stays below, capped.
    const { wrapper, state } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 700, width: 300 });
    expect(state.position.value.placement).toBe("below");
    expect(state.position.value.maxHeight).toBe(496);
    expect(state.position.value.top).toBe(264);
    expect(state.position.value.top + state.position.value.maxHeight).toBeLessThanOrEqual(VIEWPORT.height - 8);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("keeps the panel inside the viewport when the anchor scrolled above it", async () => {
    const { wrapper, state } = await mountHost({ left: 100, top: -500, bottom: -480 }, { height: 200, width: 300 });
    const position = state.position.value;
    expect(position.placement).toBe("below");
    expect(position.maxHeight).toBe(VIEWPORT_BUDGET);
    expect(position.top).toBe(ANCHORED_EDGE_PX);
    expect(position.top).toBeGreaterThanOrEqual(ANCHORED_EDGE_PX);
    expect(position.top + Math.min(200, position.maxHeight)).toBeLessThanOrEqual(VIEWPORT_MAX);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("keeps the panel inside the viewport when the anchor scrolled below it", async () => {
    const { wrapper, state } = await mountHost({ left: 100, top: 800, bottom: 820 }, { height: 200, width: 300 });
    const position = state.position.value;
    expect(position.placement).toBe("above");
    expect(position.maxHeight).toBe(VIEWPORT_BUDGET);
    // 768 - 8 - 200: the 200 px panel sits flush at the bottom edge.
    expect(position.top).toBe(560);
    expect(position.top).toBeGreaterThanOrEqual(ANCHORED_EDGE_PX);
    expect(position.top + Math.min(200, position.maxHeight)).toBeLessThanOrEqual(VIEWPORT_MAX);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("caps a panel taller than the viewport to the viewport budget", async () => {
    const { wrapper, state } = await mountHost({ left: 100, top: -500, bottom: -480 }, { height: 1000, width: 300 });
    const position = state.position.value;
    expect(position.maxHeight).toBe(VIEWPORT_BUDGET);
    expect(position.top).toBe(ANCHORED_EDGE_PX);
    expect(position.top + position.maxHeight).toBe(VIEWPORT_MAX);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("recomputes when a nested scrolling ancestor scrolls", async () => {
    const { wrapper, state } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 200, width: 300 });
    expect(state.position.value.top).toBe(264);

    const panel = requireElement(state.floating.value);
    const scroller = document.createElement("div");
    panel.appendChild(scroller);
    stubAnchorRect(requireElement(state.anchor.value), { left: 180, top: 100, bottom: 120 });
    scroller.dispatchEvent(new Event("scroll", { bubbles: false }));
    await nextTick();

    expect(state.position.value.top).toBe(124);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("recomputes on window resize", async () => {
    const { wrapper, state } = await mountHost({ left: 900, top: 240, bottom: 260 }, { height: 100, width: 300 });
    expect(state.position.value.left).toBe(716);

    vi.stubGlobal("innerWidth", 800);
    window.dispatchEvent(new Event("resize"));
    await nextTick();

    // 800 - 300 - 8 = 492.
    expect(state.position.value.left).toBe(492);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("removes its listeners on unmount and stops recomputing", async () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { wrapper, state } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 200, width: 300 });
    expect(state.position.value.top).toBe(264);
    const panel = requireElement(state.floating.value);

    wrapper.unmount();
    expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function), true);
    removeSpy.mockRestore();

    // The listeners are gone, so viewport changes no longer move the panel.
    window.dispatchEvent(new Event("resize"));
    panel.dispatchEvent(new Event("scroll", { bubbles: false }));
    await nextTick();
    expect(state.position.value.top).toBe(264);
    vi.unstubAllGlobals();
  });
});
