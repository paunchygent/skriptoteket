/**
 * Room viewport zoom composable tests.
 *
 * These tests keep the stateful zoom behavior aligned with the shared framed
 * fit-scale helper without duplicating the pure layout-contract assertions.
 */

import { computed, nextTick, ref } from "vue";
import { describe, expect, it } from "vitest";

import { computeRoomViewportFitScale } from "./roomBuilderViewport";
import { useRoomViewportZoom } from "./useRoomViewportZoom";

describe("useRoomViewportZoom", () => {
  it("uses fit-to-view until the teacher zooms manually", () => {
    const surfaceMetrics = computed(() => ({ width: 1000, height: 700 }));
    const zoom = useRoomViewportZoom(surfaceMetrics);
    const expectedFitScale = computeRoomViewportFitScale(
      { width: 524, height: 374 },
      surfaceMetrics.value,
    );

    zoom.setViewportSize({ width: 524, height: 374 });

    expect(zoom.fitScale.value).toBeCloseTo(expectedFitScale);
    expect(zoom.scale.value).toBeCloseTo(expectedFitScale);
    expect(zoom.scalePercent.value).toBe(Math.round(expectedFitScale * 100));

    zoom.zoomIn();

    expect(zoom.scale.value).toBeCloseTo(expectedFitScale + 0.1);
    expect(zoom.scalePercent.value).toBe(Math.round((expectedFitScale + 0.1) * 100));
  });

  it("resets manual zoom when the configured reset source changes", async () => {
    const surfaceMetrics = computed(() => ({ width: 1000, height: 700 }));
    const templateId = ref("template-1");
    const zoom = useRoomViewportZoom(surfaceMetrics, { resetSource: templateId });
    const expectedFitScale = computeRoomViewportFitScale(
      { width: 524, height: 374 },
      surfaceMetrics.value,
    );

    zoom.setViewportSize({ width: 524, height: 374 });
    zoom.zoomIn();
    expect(zoom.scale.value).toBeCloseTo(expectedFitScale + 0.1);

    templateId.value = "template-2";
    await nextTick();

    expect(zoom.scale.value).toBeCloseTo(expectedFitScale);
    expect(zoom.scalePercent.value).toBe(Math.round(expectedFitScale * 100));
  });

  it("does not auto-upscale smaller rooms beyond 100 percent", () => {
    const surfaceMetrics = computed(() => ({ width: 320, height: 240 }));
    const zoom = useRoomViewportZoom(surfaceMetrics);

    zoom.setViewportSize({ width: 1200, height: 800 });

    expect(zoom.fitScale.value).toBe(1);
    expect(zoom.scale.value).toBe(1);
    expect(zoom.scalePercent.value).toBe(100);
  });

  it("supports direct gesture zoom while preserving clamp boundaries", () => {
    const surfaceMetrics = computed(() => ({ width: 1000, height: 700 }));
    const zoom = useRoomViewportZoom(surfaceMetrics);

    zoom.setViewportSize({ width: 524, height: 374 });
    zoom.setManualZoomScale(1.2);
    expect(zoom.scale.value).toBeCloseTo(1.2);

    zoom.zoomByFactor(1.25);
    expect(zoom.scale.value).toBeCloseTo(1.5);

    zoom.zoomByFactor(10);
    expect(zoom.scale.value).toBe(1.6);

    zoom.zoomByFactor(0);
    expect(zoom.scale.value).toBe(1.6);

    zoom.setManualZoomScale(0.1);
    expect(zoom.scale.value).toBe(0.35);
  });
});
