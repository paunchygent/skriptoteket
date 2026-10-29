/**
 * Room-template builder pinch anchoring tests.
 *
 * Purpose:
 *   Prove the builder canvas keeps the content point under the pinch midpoint
 *   fixed while the scale changes, for the touch-event path (iOS Chrome) and
 *   the platform gesture path (iOS Safari), including the coordinate-less
 *   gesture fallback to the viewport centre.
 *
 * Relationships:
 *   - covers the `RoomTemplateBuilderSurface` -> `CreateRoomTemplateModal` ->
 *     `useRoomTemplateEditorState` -> `useAnchoredRoomViewportZoom` wiring
 *   - mirrors `PlannerPhoneClassroomSeatMap.spec.ts`, the accepted seat-map
 *     reference for anchored pinch zoom
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CreateRoomTemplateModal from "./CreateRoomTemplateModal.vue";

class ResizeObserverMock {
  observe(): void {}
  disconnect(): void {}
}

const clientMocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

vi.mock("../../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../../api/client")>("../../../api/client");
  return {
    ...actual,
    apiDelete: clientMocks.apiDelete,
    apiPost: clientMocks.apiPost,
    apiPut: clientMocks.apiPut,
  };
});

const VIEWPORT_SIZE = 2000;

async function dispatchTouchEvent(
  element: Element,
  type: string,
  distance: number,
  touches = 2,
): Promise<void> {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.defineProperty(event, "touches", {
    value: {
      length: touches,
      item: (index: number) => {
        if (index >= touches) {
          return null;
        }
        return {
          clientX: index === 0 ? 0 : distance,
          clientY: 0,
        };
      },
    },
  });
  element.dispatchEvent(event);
  await nextTick();
}

async function dispatchPlatformGesture(
  element: Element,
  type: string,
  init: { scale: number; clientX?: number; clientY?: number },
): Promise<void> {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.defineProperty(event, "scale", { value: init.scale });
  if (init.clientX !== undefined) {
    Object.defineProperty(event, "clientX", { value: init.clientX });
  }
  if (init.clientY !== undefined) {
    Object.defineProperty(event, "clientY", { value: init.clientY });
  }
  element.dispatchEvent(event);
  await nextTick();
}

function mountBuilder(): VueWrapper {
  return mount(CreateRoomTemplateModal);
}

function builderViewport(wrapper: VueWrapper): HTMLElement {
  const viewport = wrapper.get('[data-test="room-builder-viewport"]');
  const element = viewport.element as HTMLElement;
  element.getBoundingClientRect = () => ({
    x: 0,
    y: 0,
    left: 0,
    top: 0,
    right: VIEWPORT_SIZE,
    bottom: VIEWPORT_SIZE,
    width: VIEWPORT_SIZE,
    height: VIEWPORT_SIZE,
    toJSON: () => ({}),
  });
  return element;
}

function zoomPercent(wrapper: VueWrapper): string {
  return wrapper.get('[data-test="builder-zoom-percent"]').text();
}

describe("CreateRoomTemplateModal builder pinch anchoring", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      callback(0);
      return 1;
    });
    HTMLElement.prototype.scrollIntoView = vi.fn();
    // A viewport larger than the 14x9 room surface keeps the fit scale at 1, so
    // a 100 -> 125 touch distance maps to an exact 1.25 scale factor.
    Object.defineProperty(HTMLElement.prototype, "clientWidth", {
      configurable: true,
      get: () => VIEWPORT_SIZE,
    });
    Object.defineProperty(HTMLElement.prototype, "clientHeight", {
      configurable: true,
      get: () => VIEWPORT_SIZE,
    });
    clientMocks.apiDelete.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiPut.mockReset();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("keeps the content point under the touch midpoint while zooming", async () => {
    const wrapper = mountBuilder();
    const viewport = builderViewport(wrapper);
    viewport.scrollLeft = 100;
    viewport.scrollTop = 40;

    // Pinch from 100px to 125px apart: the midpoint moves 50 -> 62.5, the
    // factor is 1.25, and the content point captured at (150, 40) must stay
    // under the moving midpoint.
    await dispatchTouchEvent(viewport, "touchstart", 100);
    await dispatchTouchEvent(viewport, "touchmove", 125);
    await nextTick();

    expect(zoomPercent(wrapper)).toBe("125%");
    expect(viewport.scrollLeft).toBe(125);
    expect(viewport.scrollTop).toBe(50);
  });

  it("keeps the content point under the platform gesture point while zooming", async () => {
    const wrapper = mountBuilder();
    const viewport = builderViewport(wrapper);
    viewport.scrollLeft = 100;
    viewport.scrollTop = 40;

    await dispatchPlatformGesture(viewport, "gesturestart", {
      scale: 1,
      clientX: 50,
      clientY: 0,
    });
    await dispatchPlatformGesture(viewport, "gesturechange", {
      scale: 1.25,
      clientX: 62.5,
      clientY: 0,
    });
    await nextTick();

    expect(zoomPercent(wrapper)).toBe("125%");
    expect(viewport.scrollLeft).toBe(125);
    expect(viewport.scrollTop).toBe(50);
  });

  it("falls back to the viewport centre when a platform gesture has no coordinates", async () => {
    const wrapper = mountBuilder();
    const viewport = builderViewport(wrapper);
    viewport.scrollLeft = 100;
    viewport.scrollTop = 40;

    await dispatchPlatformGesture(viewport, "gesturestart", { scale: 1 });
    await dispatchPlatformGesture(viewport, "gesturechange", { scale: 1.25 });
    await nextTick();

    // Centre anchor (1000, 1000): content (1100, 1040) stays under it.
    expect(zoomPercent(wrapper)).toBe("125%");
    expect(viewport.scrollLeft).toBe(375);
    expect(viewport.scrollTop).toBe(300);
  });
});
