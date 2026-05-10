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

import { type Ref } from "vue";

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

type GestureCamera = {
  contentX: number;
  contentY: number;
};

export type AnchoredScrollInput = {
  newScale: number;
  contentX: number;
  contentY: number;
  anchorX: number;
  anchorY: number;
};

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

export function computeAnchoredRoomViewportScroll(
  input: AnchoredScrollInput,
): { left: number; top: number } {
  if (input.newScale <= 0) {
    return {
      left: 0,
      top: 0,
    };
  }
  return {
    left: (input.contentX * input.newScale) - input.anchorX,
    top: (input.contentY * input.newScale) - input.anchorY,
  };
}

function captureGestureCamera(
  viewport: HTMLElement,
  scale: number,
  point: ViewportPoint,
): GestureCamera {
  return {
    contentX: (viewport.scrollLeft + point.x) / scale,
    contentY: (viewport.scrollTop + point.y) / scale,
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
  let gestureCamera: GestureCamera | null = null;
  let pendingAnimationFrame: number | null = null;
  let pendingPoint: ViewportPoint | null = null;
  let pendingScale: number | null = null;

  function applyPendingGestureCamera(): void {
    pendingAnimationFrame = null;
    const element = viewport.value;
    if (!element || !gestureCamera || !pendingPoint || pendingScale === null) {
      return;
    }
    const nextScroll = computeAnchoredRoomViewportScroll({
      newScale: pendingScale,
      contentX: gestureCamera.contentX,
      contentY: gestureCamera.contentY,
      anchorX: pendingPoint.x,
      anchorY: pendingPoint.y,
    });
    element.scrollLeft = Math.max(0, nextScroll.left);
    element.scrollTop = Math.max(0, nextScroll.top);
  }

  function scheduleGestureCameraScroll(scale: number, point: ViewportPoint): void {
    pendingScale = scale;
    pendingPoint = point;
    if (pendingAnimationFrame !== null) {
      return;
    }
    pendingAnimationFrame = window.requestAnimationFrame(applyPendingGestureCamera);
  }

  function beginGestureCamera(anchor: RoomTouchViewportGestureAnchor | null): void {
    const element = viewport.value;
    if (!element || zoom.scale.value <= 0) {
      gestureCamera = null;
      return;
    }
    const point = resolveViewportPoint(element, anchor);
    gestureCamera = captureGestureCamera(element, zoom.scale.value, point);
    pendingPoint = point;
    pendingScale = zoom.scale.value;
  }

  function endGestureCamera(): void {
    if (pendingAnimationFrame !== null) {
      window.cancelAnimationFrame(pendingAnimationFrame);
      pendingAnimationFrame = null;
      applyPendingGestureCamera();
    }
    gestureCamera = null;
    pendingPoint = null;
    pendingScale = null;
  }

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
    if (gestureCamera) {
      zoom.setManualZoomScale(newScale);
      scheduleGestureCameraScroll(newScale, point);
      return;
    }
    const nextScroll = computeAnchoredRoomViewportScroll({
      newScale,
      ...captureGestureCamera(element, oldScale, point),
      anchorX: point.x,
      anchorY: point.y,
    });
    zoom.setManualZoomScale(newScale);
    window.requestAnimationFrame(() => {
      element.scrollLeft = Math.max(0, nextScroll.left);
      element.scrollTop = Math.max(0, nextScroll.top);
    });
  }

  return {
    ...zoom,
    beginGestureCamera,
    endGestureCamera,
    zoomByFactor,
  };
}
