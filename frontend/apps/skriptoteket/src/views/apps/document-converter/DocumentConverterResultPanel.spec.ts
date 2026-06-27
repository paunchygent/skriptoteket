/**
 * Document Converter PDF preview panel specs.
 *
 * Domain purpose:
 *   Prove previewable PDF results expose real fit, zoom, and touch-pinch
 *   inspection controls in the right-side preview pane.
 *
 * Relationships:
 *   - Exercises `DocumentConverterResultPanel.vue` through user-visible
 *     controls.
 *   - Complements route-level tests for project and single-file result state.
 */

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DocumentConverterResultPanel from "./DocumentConverterResultPanel.vue";

class ResizeObserverMock {
  static instances: ResizeObserverMock[] = [];

  callback: ResizeObserverCallback;
  disconnect = vi.fn();
  observe = vi.fn();
  unobserve = vi.fn();

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    ResizeObserverMock.instances.push(this);
  }

  emit(width: number, height: number): void {
    this.callback(
      [
        {
          contentRect: { width, height } as DOMRectReadOnly,
        } as ResizeObserverEntry,
      ],
      this as unknown as ResizeObserver,
    );
  }
}

function touchEvent(
  type: string,
  touches: Array<{ clientX: number; clientY: number }>,
): TouchEvent {
  const event = new Event(type, { cancelable: true }) as TouchEvent;
  const touchList = {
    item: (index: number) => touches[index] ?? null,
    length: touches.length,
  };
  touches.forEach((touch, index) => {
    Object.assign(touchList, { [index]: touch });
  });
  Object.defineProperty(event, "touches", {
    configurable: true,
    value: touchList,
  });
  return event;
}

describe("DocumentConverterResultPanel", () => {
  beforeEach(() => {
    ResizeObserverMock.instances = [];
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fits a PDF preview until manual zoom changes the scale", async () => {
    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();
    ResizeObserverMock.instances[0]?.emit(397, 562);
    await wrapper.vm.$nextTick();

    const surface = wrapper.get('[data-testid="document-converter-pdf-surface"]');
    expect(surface.attributes("style")).toContain("--dc-preview-scale: 0.5");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("50%");

    await wrapper.get('[data-testid="document-converter-preview-zoom-in"]').trigger("click");
    expect(surface.attributes("style")).toContain("--dc-preview-scale: 0.6");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("60%");

    await wrapper.get('[data-testid="document-converter-preview-zoom-out"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-preview-zoom-out"]').trigger("click");
    expect(surface.attributes("style")).toContain("--dc-preview-scale: 0.4");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("40%");

    await wrapper.get('[data-testid="document-converter-preview-fit"]').trigger("click");
    expect(surface.attributes("style")).toContain("--dc-preview-scale: 0.5");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("50%");
  });

  it("returns to fit-to-pane when the selected PDF preview changes", async () => {
    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:first-document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();
    ResizeObserverMock.instances[0]?.emit(397, 562);
    await wrapper.vm.$nextTick();

    const surface = wrapper.get('[data-testid="document-converter-pdf-surface"]');
    await wrapper.get('[data-testid="document-converter-preview-zoom-in"]').trigger("click");
    expect(surface.attributes("style")).toContain("--dc-preview-scale: 0.6");

    await wrapper.setProps({ activePreviewUrl: "blob:second-document-converter-result" });
    await wrapper.vm.$nextTick();

    expect(surface.attributes("style")).toContain("--dc-preview-scale: 0.5");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("50%");
  });

  it("zooms a PDF preview with a two-finger pinch gesture", async () => {
    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();
    ResizeObserverMock.instances[0]?.emit(794, 1124);
    await wrapper.vm.$nextTick();

    const viewport = wrapper.get('[data-testid="document-converter-pdf-viewport"]');
    const surface = wrapper.get('[data-testid="document-converter-pdf-surface"]');

    viewport.element.dispatchEvent(touchEvent("touchstart", [
      { clientX: 10, clientY: 10 },
      { clientX: 110, clientY: 10 },
    ]));
    await wrapper.vm.$nextTick();
    viewport.element.dispatchEvent(touchEvent("touchmove", [
      { clientX: 10, clientY: 10 },
      { clientX: 160, clientY: 10 },
    ]));
    await wrapper.vm.$nextTick();

    expect(surface.attributes("style")).toContain("--dc-preview-scale: 1.5");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("150%");
  });

  it("keeps one-finger PDF panning available while pinch zoom owns two-finger gestures", async () => {
    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();
    ResizeObserverMock.instances[0]?.emit(397, 562);
    await wrapper.vm.$nextTick();

    const viewport = wrapper.get('[data-testid="document-converter-pdf-viewport"]');
    const oneFingerMove = touchEvent("touchmove", [{ clientX: 40, clientY: 120 }]);
    const oneFingerPreventDefault = vi.spyOn(oneFingerMove, "preventDefault");
    viewport.element.dispatchEvent(oneFingerMove);

    expect(oneFingerPreventDefault).not.toHaveBeenCalled();

    viewport.element.dispatchEvent(touchEvent("touchstart", [
      { clientX: 10, clientY: 10 },
      { clientX: 110, clientY: 10 },
    ]));
    const pinchMove = touchEvent("touchmove", [
      { clientX: 10, clientY: 10 },
      { clientX: 160, clientY: 10 },
    ]);
    const pinchPreventDefault = vi.spyOn(pinchMove, "preventDefault");
    viewport.element.dispatchEvent(pinchMove);

    expect(pinchPreventDefault).toHaveBeenCalledTimes(1);
  });
});
