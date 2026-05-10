/**
 * Anchored room viewport zoom.
 *
 * Purpose:
 *   Preserve the visible map target while a scrollable room viewport changes
 *   scale, so phone pinch zoom grows around the gesture midpoint instead of
 *   drifting toward the canvas origin.
 *
 * Relationships:
 *   - wraps `useRoomViewportZoom.ts`
 *   - consumed by simplified phone classroom-map surfaces
 *   - receives gesture anchors from `useRoomTouchViewportGestures.ts`
 */

import { nextTick, type Ref } from "vue";

import {
  clampRoomViewportScale,
  type RoomViewportSize,
} from "./roomBuilderViewport";
import type { RoomTouchViewportGestureAnchor } from "./useRoomTouchViewportGestures";
import {
  useRoomViewportZoom,
  type UseRoomViewportZoomOptions,
} from "./useRoomViewportZoom";

type ViewportPoint = {
  x: number;
  y: number;
};

export type AnchoredScrollInput = {
  oldScale: number;
  newScale: number;
  scrollLeft: number;
  scrollTop: number;
  anchorX: number;
  anchorY: number;
};

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

export function computeAnchoredRoomViewportScroll(
  input: AnchoredScrollInput,
): { left: number; top: number } {
  if (input.oldScale <= 0 || input.newScale <= 0) {
    return {
      left: input.scrollLeft,
      top: input.scrollTop,
    };
  }
  const contentX = (input.scrollLeft + input.anchorX) / input.oldScale;
  const contentY = (input.scrollTop + input.anchorY) / input.oldScale;
  return {
    left: (contentX * input.newScale) - input.anchorX,
    top: (contentY * input.newScale) - input.anchorY,
  };
}

function resolveViewportPoint(
  viewport: HTMLElement,
  anchor: RoomTouchViewportGestureAnchor | null,
): ViewportPoint {
  if (!anchor) {
    return {
      x: viewport.clientWidth / 2,
      y: viewport.clientHeight / 2,
    };
  }
  const rect = viewport.getBoundingClientRect();
  return {
    x: clamp(anchor.clientX - rect.left, 0, viewport.clientWidth),
    y: clamp(anchor.clientY - rect.top, 0, viewport.clientHeight),
  };
}

export function useAnchoredRoomViewportZoom(
  surfaceMetrics: Ref<RoomViewportSize>,
  viewport: Ref<HTMLElement | null>,
  options: UseRoomViewportZoomOptions = {},
) {
  const zoom = useRoomViewportZoom(surfaceMetrics, options);

  function zoomByFactor(
    factor: number,
    anchor: RoomTouchViewportGestureAnchor | null = null,
  ): void {
    if (!Number.isFinite(factor) || factor <= 0) {
      return;
    }
    const element = viewport.value;
    const oldScale = zoom.scale.value;
    const newScale = clampRoomViewportScale(oldScale * factor);
    if (!element) {
      zoom.setManualZoomScale(newScale);
      return;
    }
    const point = resolveViewportPoint(element, anchor);
    const nextScroll = computeAnchoredRoomViewportScroll({
      oldScale,
      newScale,
      scrollLeft: element.scrollLeft,
      scrollTop: element.scrollTop,
      anchorX: point.x,
      anchorY: point.y,
    });
    zoom.setManualZoomScale(newScale);
    void nextTick(() => {
      element.scrollLeft = Math.max(0, nextScroll.left);
      element.scrollTop = Math.max(0, nextScroll.top);
    });
  }

  return {
    ...zoom,
    zoomByFactor,
  };
}
