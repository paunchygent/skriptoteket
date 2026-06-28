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

function gestureEvent(
  type: string,
  {
    scale,
    clientX = 90,
    clientY = 140,
  }: { scale: number; clientX?: number; clientY?: number },
): Event {
  const event = new Event(type, { cancelable: true });
  Object.defineProperty(event, "scale", {
    configurable: true,
    value: scale,
  });
  Object.defineProperty(event, "clientX", {
    configurable: true,
    value: clientX,
  });
  Object.defineProperty(event, "clientY", {
    configurable: true,
    value: clientY,
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

  it("keeps fit-to-view previews centered when the document underfills a wider pane", async () => {
    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();
    ResizeObserverMock.instances[0]?.emit(640, 562);
    await wrapper.vm.$nextTick();

    const stage = wrapper.get('[data-testid="document-converter-pdf-stage"]');
    expect(stage.classes()).toContain("dc-pdf-stage--contained");

    await wrapper.get('[data-testid="document-converter-preview-zoom-in"]').trigger("click");
    expect(stage.classes()).not.toContain("dc-pdf-stage--contained");

    await wrapper.get('[data-testid="document-converter-preview-fit"]').trigger("click");
    expect(stage.classes()).toContain("dc-pdf-stage--contained");
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

  it("binds native non-passive touch and platform gesture listeners on the preview viewport", async () => {
    const originalAddEventListener = HTMLElement.prototype.addEventListener;
    const bindings: Array<{
      listener: EventListenerOrEventListenerObject;
      options: AddEventListenerOptions | boolean | undefined;
      target: EventTarget;
      type: string;
    }> = [];
    const addEventListenerSpy = vi
      .spyOn(HTMLElement.prototype, "addEventListener")
      .mockImplementation(function (
        this: HTMLElement,
        type: string,
        listener: EventListenerOrEventListenerObject,
        options?: AddEventListenerOptions | boolean,
      ): void {
        bindings.push({ type, listener, options, target: this });
        originalAddEventListener.call(this, type, listener, options);
      });

    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();

    const viewport = wrapper.get('[data-testid="document-converter-pdf-viewport"]').element;
    const viewportBindings = bindings.filter((binding) => binding.target === viewport);
    const passiveFalseTypes = viewportBindings
      .filter((binding) => binding.options && typeof binding.options === "object" && binding.options.passive === false)
      .map((binding) => binding.type)
      .sort();

    expect(passiveFalseTypes).toEqual([
      "gesturechange",
      "gestureend",
      "gesturestart",
      "touchcancel",
      "touchend",
      "touchmove",
      "touchstart",
    ]);

    addEventListenerSpy.mockRestore();
  });

  it("uses platform gesture events to zoom a PDF preview on Safari-style pinch input", async () => {
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
    const start = gestureEvent("gesturestart", { scale: 1, clientX: 110, clientY: 150 });
    const change = gestureEvent("gesturechange", { scale: 1.4, clientX: 110, clientY: 150 });
    const startPreventDefault = vi.spyOn(start, "preventDefault");
    const changePreventDefault = vi.spyOn(change, "preventDefault");

    viewport.element.dispatchEvent(start);
    viewport.element.dispatchEvent(change);
    await wrapper.vm.$nextTick();

    expect(startPreventDefault).toHaveBeenCalledTimes(1);
    expect(changePreventDefault).toHaveBeenCalledTimes(1);
    expect(surface.attributes("style")).toContain("--dc-preview-scale: 1.4");
    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("140%");
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

  it("keeps the pinch midpoint anchored by compensating viewport scroll", async () => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      callback(0);
      return 1;
    });

    const wrapper = mount(DocumentConverterResultPanel, {
      props: {
        activePreviewUrl: "blob:document-converter-result",
        resultStateLabel: "PDF klart för granskning.",
        resultTitle: "lektion.pdf",
      },
    });

    await wrapper.vm.$nextTick();

    const viewport = wrapper.get('[data-testid="document-converter-pdf-viewport"]').element as HTMLElement;
    Object.defineProperties(viewport, {
      clientHeight: { configurable: true, value: 180 },
      clientWidth: { configurable: true, value: 300 },
    });
    viewport.getBoundingClientRect = () => ({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 300,
      bottom: 180,
      width: 300,
      height: 180,
      toJSON: () => ({}),
    });
    viewport.scrollLeft = 100;
    viewport.scrollTop = 40;

    ResizeObserverMock.instances[0]?.emit(794, 1124);
    await wrapper.vm.$nextTick();

    viewport.dispatchEvent(touchEvent("touchstart", [
      { clientX: 50, clientY: 50 },
      { clientX: 150, clientY: 50 },
    ]));
    viewport.dispatchEvent(touchEvent("touchmove", [
      { clientX: 0, clientY: 50 },
      { clientX: 200, clientY: 50 },
    ]));
    await wrapper.vm.$nextTick();

    expect(wrapper.get('[data-testid="document-converter-preview-zoom-label"]').text()).toBe("200%");
    expect(viewport.scrollLeft).toBe(300);
    expect(viewport.scrollTop).toBe(130);
  });
});
