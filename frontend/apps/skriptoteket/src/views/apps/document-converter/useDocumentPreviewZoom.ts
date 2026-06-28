/**
 * Document Converter PDF preview zoom state.
 *
 * Domain purpose:
 *   Keep previewable document outputs fit-to-pane by default while letting the
 *   teacher inspect details with explicit zoom and touch pinch gestures.
 *
 * Relationships:
 *   - Used by `DocumentConverterResultPanel.vue`.
 *   - Adapts the app's viewport zoom model without importing room-builder
 *     domain semantics.
 */

import { computed, ref, watch, type WatchSource } from "vue";

type DocumentPreviewSize = {
  width: number;
  height: number;
};

type TouchPoint = {
  clientX: number;
  clientY: number;
};

export type UseDocumentPreviewZoomOptions = {
  resetSource?: WatchSource<unknown> | WatchSource<unknown>[];
};

export const DOCUMENT_PREVIEW_WIDTH = 794;
export const DOCUMENT_PREVIEW_HEIGHT = 1124;
const DOCUMENT_PREVIEW_MIN_SCALE = 0.35;
const DOCUMENT_PREVIEW_MAX_SCALE = 2.5;
const DOCUMENT_PREVIEW_SCALE_STEP = 0.1;

export function clampDocumentPreviewScale(scale: number): number {
  return Math.min(
    Math.max(scale, DOCUMENT_PREVIEW_MIN_SCALE),
    DOCUMENT_PREVIEW_MAX_SCALE,
  );
}

function roundScale(scale: number): number {
  return Math.round(scale * 100) / 100;
}

function computeFitScale(viewport: DocumentPreviewSize): number {
  if (viewport.width <= 0 || viewport.height <= 0) {
    return 1;
  }
  return clampDocumentPreviewScale(
    Math.min(
      viewport.width / DOCUMENT_PREVIEW_WIDTH,
      viewport.height / DOCUMENT_PREVIEW_HEIGHT,
    ),
  );
}

function firstTwoTouches(event: TouchEvent): [TouchPoint, TouchPoint] | null {
  const first = event.touches.item(0);
  const second = event.touches.item(1);
  return first && second ? [first, second] : null;
}

function touchDistance(first: TouchPoint, second: TouchPoint): number {
  return Math.hypot(first.clientX - second.clientX, first.clientY - second.clientY);
}

function preventBrowserDefault(event: Event): void {
  if (event.cancelable) {
    event.preventDefault();
  }
}

export function useDocumentPreviewZoom(options: UseDocumentPreviewZoomOptions = {}) {
  const viewportSize = ref<DocumentPreviewSize>({ width: 0, height: 0 });
  const manualZoomScale = ref<number | null>(null);
  let lastPinchDistance: number | null = null;

  const fitScale = computed(() => roundScale(computeFitScale(viewportSize.value)));
  const scale = computed(() => roundScale(manualZoomScale.value ?? fitScale.value));
  const fitsViewport = computed(() => scale.value <= fitScale.value);
  const scalePercent = computed(() => Math.round(scale.value * 100));
  const scaledSurfaceStyle = computed(() => ({
    "--dc-preview-scale": String(scale.value),
  }));

  function setViewportSize(nextSize: DocumentPreviewSize): void {
    viewportSize.value = nextSize;
  }

  function setManualZoomScale(nextScale: number): void {
    if (!Number.isFinite(nextScale)) {
      return;
    }
    manualZoomScale.value = roundScale(clampDocumentPreviewScale(nextScale));
  }

  function zoomOut(): void {
    setManualZoomScale((manualZoomScale.value ?? fitScale.value) - DOCUMENT_PREVIEW_SCALE_STEP);
  }

  function zoomIn(): void {
    setManualZoomScale((manualZoomScale.value ?? fitScale.value) + DOCUMENT_PREVIEW_SCALE_STEP);
  }

  function zoomByFactor(factor: number): void {
    if (!Number.isFinite(factor) || factor <= 0) {
      return;
    }
    setManualZoomScale((manualZoomScale.value ?? fitScale.value) * factor);
  }

  function fitToView(): void {
    manualZoomScale.value = null;
  }

  function handleTouchStart(event: TouchEvent): void {
    const touches = firstTwoTouches(event);
    if (!touches) {
      return;
    }
    lastPinchDistance = touchDistance(touches[0], touches[1]);
    preventBrowserDefault(event);
  }

  function handleTouchMove(event: TouchEvent): void {
    const touches = firstTwoTouches(event);
    if (!touches || lastPinchDistance === null) {
      return;
    }
    const nextDistance = touchDistance(touches[0], touches[1]);
    if (lastPinchDistance > 0 && nextDistance > 0) {
      zoomByFactor(nextDistance / lastPinchDistance);
    }
    lastPinchDistance = nextDistance;
    preventBrowserDefault(event);
  }

  function endTouchGesture(): void {
    lastPinchDistance = null;
  }

  if (options.resetSource) {
    watch(options.resetSource, () => {
      fitToView();
    });
  }

  return {
    fitScale,
    fitsViewport,
    scale,
    scalePercent,
    scaledSurfaceStyle,
    setViewportSize,
    setManualZoomScale,
    zoomOut,
    zoomIn,
    zoomByFactor,
    fitToView,
    handleTouchStart,
    handleTouchMove,
    endTouchGesture,
  };
}
