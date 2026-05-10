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

import { nextTick, ref } from "vue";
import { describe, expect, it } from "vitest";

import {
  computeAnchoredRoomViewportScroll,
  useAnchoredRoomViewportZoom,
} from "./useAnchoredRoomViewportZoom";

describe("computeAnchoredRoomViewportScroll", () => {
  it("keeps the same content coordinate under the viewport anchor", () => {
    expect(
      computeAnchoredRoomViewportScroll({
        oldScale: 1,
        newScale: 2,
        scrollLeft: 100,
        scrollTop: 40,
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
  it("updates viewport scroll after applying a pinch scale", async () => {
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
    await nextTick();

    expect(zoom.scale.value).toBe(1.6);
    expect(viewport.scrollLeft).toBe(190);
    expect(viewport.scrollTop).toBe(94);
  });
});
