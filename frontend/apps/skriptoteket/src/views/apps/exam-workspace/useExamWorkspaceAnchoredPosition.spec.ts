/**
 * Exam workspace anchored floating position.
 *
 * Expected behavior:
 *   A floating panel (the gap popover) stays fully visible next to its
 *   anchor chip: below the chip while there is room, flipped above it when
 *   the space below is smaller than its height, clamped to the viewport
 *   edges, capped to the available viewport height, and repositioned on
 *   window resize and on scroll of any ancestor. All listeners are removed
 *   when the calling component unmounts.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import { useExamWorkspaceAnchoredPosition } from "./useExamWorkspaceAnchoredPosition";

const VIEWPORT = { width: 1024, height: 768 };

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

const Host = defineComponent({
  setup() {
    const anchor = ref<HTMLElement | null>(null);
    const floating = ref<HTMLElement | null>(null);
    const { position, place } = useExamWorkspaceAnchoredPosition(anchor, floating);
    function setAnchor(element: unknown): void {
      anchor.value = element as HTMLElement | null;
    }
    function setFloating(element: unknown): void {
      floating.value = element as HTMLElement | null;
    }
    return { anchor, floating, position, place, setAnchor, setFloating };
  },
  render() {
    const self = this as unknown as {
      setAnchor: (element: unknown) => void;
      setFloating: (element: unknown) => void;
    };
    return h("div", [
      h("button", { ref: self.setAnchor }, "chip"),
      h("div", { ref: self.setFloating }, "popover"),
    ]);
  },
});

type HostVm = {
  anchor: HTMLElement | null;
  floating: HTMLElement | null;
  position: { top: number; left: number; maxHeight: number; placement: "below" | "above" };
  place: () => void;
};

async function mountHost(anchorRect: { left: number; top: number; bottom: number }, floatingSize: { height: number; width: number }) {
  stubViewport();
  const wrapper = mount(Host, { attachTo: document.body });
  await nextTick();
  await nextTick();
  const vm = wrapper.vm as unknown as HostVm;
  stubAnchorRect(vm.anchor as HTMLElement, anchorRect);
  stubFloatingSize(vm.floating as HTMLElement, floatingSize);
  vm.place();
  await nextTick();
  return { wrapper, vm };
}

describe("useExamWorkspaceAnchoredPosition", () => {
  it("places the panel below the anchor while there is room", async () => {
    const { wrapper, vm } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 200, width: 300 });
    const position = vm.position;
    expect(position.placement).toBe("below");
    expect(position.top).toBe(264);
    expect(position.left).toBe(180);
    // 768 - 260 - 4 - 8 below; the 200 px panel fits, so no cap.
    expect(position.maxHeight).toBe(496);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("flips above the anchor when the space below is smaller than its height", async () => {
    const { wrapper, vm } = await mountHost({ left: 180, top: 680, bottom: 700 }, { height: 200, width: 300 });
    const position = vm.position;
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
    expect(wide.vm.position.left).toBe(716);
    wide.wrapper.unmount();

    const narrow = await mountHost({ left: 2, top: 240, bottom: 260 }, { height: 100, width: 300 });
    expect(narrow.vm.position.left).toBe(8);
    narrow.wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("caps the height so the panel never leaves the viewport", async () => {
    // A 700 px panel with 496 px below and 228 px above stays below, capped.
    const { wrapper, vm } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 700, width: 300 });
    expect(vm.position.placement).toBe("below");
    expect(vm.position.maxHeight).toBe(496);
    expect(vm.position.top).toBe(264);
    expect(vm.position.top + vm.position.maxHeight).toBeLessThanOrEqual(VIEWPORT.height - 8);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("recomputes when a nested scrolling ancestor scrolls", async () => {
    const { wrapper, vm } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 200, width: 300 });
    expect(vm.position.top).toBe(264);

    const scroller = document.createElement("div");
    (vm.floating as HTMLElement).appendChild(scroller);
    stubAnchorRect(vm.anchor as HTMLElement, { left: 180, top: 100, bottom: 120 });
    scroller.dispatchEvent(new Event("scroll", { bubbles: false }));
    await nextTick();

    expect(vm.position.top).toBe(124);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("recomputes on window resize", async () => {
    const { wrapper, vm } = await mountHost({ left: 900, top: 240, bottom: 260 }, { height: 100, width: 300 });
    expect(vm.position.left).toBe(716);

    vi.stubGlobal("innerWidth", 800);
    window.dispatchEvent(new Event("resize"));
    await nextTick();

    // 800 - 300 - 8 = 492.
    expect(vm.position.left).toBe(492);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("removes its listeners on unmount and stops recomputing", async () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { wrapper, vm } = await mountHost({ left: 180, top: 240, bottom: 260 }, { height: 200, width: 300 });
    expect(vm.position.top).toBe(264);
    const panel = vm.floating as HTMLElement;

    wrapper.unmount();
    expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function), true);
    removeSpy.mockRestore();

    // The listeners are gone, so viewport changes no longer move the panel.
    window.dispatchEvent(new Event("resize"));
    panel.dispatchEvent(new Event("scroll", { bubbles: false }));
    await nextTick();
    expect(vm.position.top).toBe(264);
    vi.unstubAllGlobals();
  });
});
