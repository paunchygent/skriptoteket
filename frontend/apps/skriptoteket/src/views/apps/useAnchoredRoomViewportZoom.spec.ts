/**
 * Anchored room viewport zoom tests.
 *
 * Purpose:
 *   Prove scrollable phone map zoom preserves the gesture target instead of
 *   drifting toward the classroom canvas origin.
 *
 * Relationships:
 *   - covers `useAnchoredRoomViewportZoom.ts`
 *   - complements phone map component gesture tests
 */

import { ref } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  computeAnchoredRoomViewportScroll,
  useAnchoredRoomViewportZoom,
} from "./useAnchoredRoomViewportZoom";

describe("computeAnchoredRoomViewportScroll", () => {
  it("keeps the same content coordinate under the viewport anchor", () => {
    expect(
      computeAnchoredRoomViewportScroll({
        newScale: 2,
        contentX: 150,
        contentY: 70,
        anchorX: 50,
        anchorY: 30,
      }),
    ).toEqual({
      left: 250,
      top: 110,
    });
  });
});

describe("useAnchoredRoomViewportZoom", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("updates viewport scroll after applying a pinch scale", () => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      callback(0);
      return 1;
    });
    const viewport = document.createElement("div");
    Object.defineProperties(viewport, {
      clientWidth: { value: 300 },
      clientHeight: { value: 180 },
    });
    viewport.getBoundingClientRect = () => ({
      x: 10,
      y: 20,
      left: 10,
      top: 20,
      right: 310,
      bottom: 200,
      width: 300,
      height: 180,
      toJSON: () => ({}),
    });
    viewport.scrollLeft = 100;
    viewport.scrollTop = 40;

    const zoom = useAnchoredRoomViewportZoom(
      ref({ width: 600, height: 400 }),
      ref(viewport),
    );

    zoom.zoomByFactor(2, { clientX: 60, clientY: 70 });

    expect(zoom.scale.value).toBe(1.6);
    expect(viewport.scrollLeft).toBe(190);
    expect(viewport.scrollTop).toBe(94);
  });

  it("keeps the captured content point stable across coalesced gesture updates", () => {
    let queuedCallback: FrameRequestCallback = () => {};
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      queuedCallback = callback;
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
    const viewport = document.createElement("div");
    Object.defineProperties(viewport, {
      clientWidth: { value: 300 },
      clientHeight: { value: 180 },
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

    const zoom = useAnchoredRoomViewportZoom(
      ref({ width: 600, height: 400 }),
      ref(viewport),
    );

    zoom.beginGestureCamera({ clientX: 80, clientY: 60 });
    zoom.zoomByFactor(1.2, { clientX: 82, clientY: 61 });
    zoom.zoomByFactor(1.2, { clientX: 84, clientY: 62 });
    queuedCallback(0);

    expect(zoom.scale.value).toBeCloseTo(1.44);
    expect(viewport.scrollLeft).toBeCloseTo(175.2);
    expect(viewport.scrollTop).toBeCloseTo(82);
  });

  it("flushes the final queued gesture-camera scroll before ending a pinch", () => {
    vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 4);
    const cancelAnimationFrame = vi
      .spyOn(window, "cancelAnimationFrame")
      .mockImplementation(() => {});
    const viewport = document.createElement("div");
    Object.defineProperties(viewport, {
      clientWidth: { value: 300 },
      clientHeight: { value: 180 },
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

    const zoom = useAnchoredRoomViewportZoom(
      ref({ width: 600, height: 400 }),
      ref(viewport),
    );

    zoom.beginGestureCamera({ clientX: 80, clientY: 60 });
    zoom.zoomByFactor(1.2, { clientX: 82, clientY: 61 });
    zoom.endGestureCamera();

    expect(cancelAnimationFrame).toHaveBeenCalledWith(4);
    expect(zoom.scale.value).toBeCloseTo(1.2);
    expect(viewport.scrollLeft).toBeCloseTo(134);
    expect(viewport.scrollTop).toBeCloseTo(59);
  });
});
