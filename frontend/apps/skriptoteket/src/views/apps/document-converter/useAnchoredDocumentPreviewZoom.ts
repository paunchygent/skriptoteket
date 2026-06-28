/**
 * Anchored Document Converter preview zoom.
 *
 * Domain purpose:
 *   Preserve the teacher's pinch target inside the PDF preview viewport so
 *   zoom grows around the gesture midpoint instead of the document origin.
 *
 * Relationships:
 *   - Wraps `useDocumentPreviewZoom.ts` with scroll compensation.
 *   - Consumes anchors from `useDocumentPreviewTouchGestures.ts`.
 */

import { type Ref } from "vue";

import type { DocumentPreviewGestureAnchor } from "./useDocumentPreviewTouchGestures";
import {
  clampDocumentPreviewScale,
  type UseDocumentPreviewZoomOptions,
  useDocumentPreviewZoom,
} from "./useDocumentPreviewZoom";

type ViewportPoint = {
  x: number;
  y: number;
};

type GestureCamera = {
  contentX: number;
  contentY: number;
};

export type AnchoredDocumentPreviewScrollInput = {
  anchorX: number;
  anchorY: number;
  contentX: number;
  contentY: number;
  newScale: number;
};

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

export function computeAnchoredDocumentPreviewScroll(
  input: AnchoredDocumentPreviewScrollInput,
): { left: number; top: number } {
  if (input.newScale <= 0) {
    return { left: 0, top: 0 };
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
  anchor: DocumentPreviewGestureAnchor | null,
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

export function useAnchoredDocumentPreviewZoom(
  viewport: Ref<HTMLElement | null>,
  options: UseDocumentPreviewZoomOptions = {},
) {
  const zoom = useDocumentPreviewZoom(options);
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
    const nextScroll = computeAnchoredDocumentPreviewScroll({
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

  function beginGestureCamera(anchor: DocumentPreviewGestureAnchor | null): void {
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
    anchor: DocumentPreviewGestureAnchor | null = null,
  ): void {
    if (!Number.isFinite(factor) || factor <= 0) {
      return;
    }
    const element = viewport.value;
    const oldScale = zoom.scale.value;
    const newScale = clampDocumentPreviewScale(oldScale * factor);
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
    const nextScroll = computeAnchoredDocumentPreviewScroll({
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
