import { computed, nextTick, ref } from "vue";
import { describe, expect, it } from "vitest";

import { useRoomViewportZoom } from "./useRoomViewportZoom";

describe("useRoomViewportZoom", () => {
  it("uses fit-to-view until the teacher zooms manually", () => {
    const surfaceMetrics = computed(() => ({ width: 1000, height: 700 }));
    const zoom = useRoomViewportZoom(surfaceMetrics);

    zoom.setViewportSize({ width: 524, height: 374 });

    expect(zoom.fitScale.value).toBeCloseTo(0.5);
    expect(zoom.scale.value).toBeCloseTo(0.5);
    expect(zoom.scalePercent.value).toBe(50);

    zoom.zoomIn();

    expect(zoom.scale.value).toBeCloseTo(0.6);
    expect(zoom.scalePercent.value).toBe(60);
  });

  it("resets manual zoom when the configured reset source changes", async () => {
    const surfaceMetrics = computed(() => ({ width: 1000, height: 700 }));
    const templateId = ref("template-1");
    const zoom = useRoomViewportZoom(surfaceMetrics, { resetSource: templateId });

    zoom.setViewportSize({ width: 524, height: 374 });
    zoom.zoomIn();
    expect(zoom.scale.value).toBeCloseTo(0.6);

    templateId.value = "template-2";
    await nextTick();

    expect(zoom.scale.value).toBeCloseTo(0.5);
    expect(zoom.scalePercent.value).toBe(50);
  });
});
