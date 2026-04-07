/**
 * Room viewport fit-scale tests.
 *
 * These tests freeze the shared framed-surface viewport contract used by the
 * builder, seating canvas, and rules seating map so downstream composables do
 * not quietly drift back to the older one-edge padding model.
 */

import { describe, expect, it } from "vitest";

import { computeRoomViewportFitScale } from "./roomBuilderViewport";

describe("computeRoomViewportFitScale", () => {
  it("uses the full framed surface when fitting a room into the viewport", () => {
    expect(
      computeRoomViewportFitScale(
        { width: 524, height: 374 },
        { width: 1000, height: 700 },
      ),
    ).toBeCloseTo(0.4657142857142857);
  });

  it("caps fit-to-view at 100 percent for smaller rooms", () => {
    expect(
      computeRoomViewportFitScale(
        { width: 1200, height: 800 },
        { width: 320, height: 240 },
      ),
    ).toBe(1);
  });
});
