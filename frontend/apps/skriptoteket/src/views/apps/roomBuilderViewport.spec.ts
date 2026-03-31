import { describe, expect, it } from "vitest";

import {
  MAX_ROOM_VIEWPORT_SCALE,
  MIN_ROOM_VIEWPORT_SCALE,
  clampRoomViewportScale,
  computeRoomViewportFitScale,
  getScaledRoomSurfaceStyle,
} from "./roomBuilderViewport";

describe("roomBuilderViewport", () => {
  it("clamps zoom scales inside the supported builder range", () => {
    expect(clampRoomViewportScale(0.1)).toBe(MIN_ROOM_VIEWPORT_SCALE);
    expect(clampRoomViewportScale(0.9)).toBe(0.9);
    expect(clampRoomViewportScale(3)).toBe(MAX_ROOM_VIEWPORT_SCALE);
  });

  it("computes a fit scale that prefers showing the full room surface", () => {
    expect(computeRoomViewportFitScale(
      { width: 900, height: 640 },
      { width: 1400, height: 920 },
    )).toBeLessThan(1);

    expect(computeRoomViewportFitScale(
      { width: 2000, height: 1400 },
      { width: 600, height: 400 },
    )).toBe(MAX_ROOM_VIEWPORT_SCALE);
  });

  it("returns scaled frame sizes for the zoomed room surface", () => {
    expect(getScaledRoomSurfaceStyle(
      { width: 1000, height: 800 },
      0.5,
    )).toEqual({
      width: "500px",
      height: "400px",
    });
  });
});
