/**
 * Shared room viewport zoom composable.
 *
 * This composable owns session-local viewport zoom state for room-based
 * planner surfaces. It keeps fit-to-view, manual zoom stepping, and viewport
 * measurement consistent between the room builder and the live seating canvas
 * without leaking view-only state into saved planner data.
 */

import { computed, ref, watch, type Ref, type WatchSource } from "vue";

import {
  ROOM_VIEWPORT_SCALE_STEP,
  clampRoomViewportScale,
  computeRoomViewportFitScale,
  getScaledRoomSurfaceStyle,
  type RoomViewportSize,
} from "./roomBuilderViewport";

export type UseRoomViewportZoomOptions = {
  resetSource?: WatchSource<unknown> | WatchSource<unknown>[];
};

export function useRoomViewportZoom(
  surfaceMetrics: Ref<RoomViewportSize>,
  options: UseRoomViewportZoomOptions = {},
) {
  const viewportSize = ref<RoomViewportSize>({ width: 0, height: 0 });
  const manualZoomScale = ref<number | null>(null);

  const fitScale = computed(() => computeRoomViewportFitScale(viewportSize.value, surfaceMetrics.value));
  const scale = computed(() => manualZoomScale.value ?? fitScale.value);
  const scaledSurfaceStyle = computed(() => getScaledRoomSurfaceStyle(surfaceMetrics.value, scale.value));
  const scalePercent = computed(() => Math.round(scale.value * 100));

  function setViewportSize(nextSize: RoomViewportSize): void {
    viewportSize.value = nextSize;
  }

  function zoomOut(): void {
    const currentScale = manualZoomScale.value ?? fitScale.value;
    manualZoomScale.value = clampRoomViewportScale(currentScale - ROOM_VIEWPORT_SCALE_STEP);
  }

  function zoomIn(): void {
    const currentScale = manualZoomScale.value ?? fitScale.value;
    manualZoomScale.value = clampRoomViewportScale(currentScale + ROOM_VIEWPORT_SCALE_STEP);
  }

  function setManualZoomScale(nextScale: number): void {
    manualZoomScale.value = clampRoomViewportScale(nextScale);
  }

  function zoomByFactor(factor: number): void {
    if (!Number.isFinite(factor) || factor <= 0) {
      return;
    }
    const currentScale = manualZoomScale.value ?? fitScale.value;
    setManualZoomScale(currentScale * factor);
  }

  function resetZoom(): void {
    manualZoomScale.value = null;
  }

  if (options.resetSource) {
    watch(options.resetSource, () => {
      resetZoom();
    });
  }

  return {
    viewportSize,
    fitScale,
    scale,
    scaledSurfaceStyle,
    scalePercent,
    setViewportSize,
    zoomOut,
    zoomIn,
    setManualZoomScale,
    zoomByFactor,
    resetZoom,
  };
}
