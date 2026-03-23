import { describe, expect, it } from "vitest";

import {
  DEFAULT_ROOM_GRID_COLS,
  DEFAULT_ROOM_GRID_ROWS,
  normalizeFixturePlacement,
  normalizeRoomGrid,
  resolveNearestWallSide,
  resolveWallSideFromFixture,
  resolveWallSideForPointer,
} from "./roomFixtureLayout";

describe("roomFixtureLayout", () => {
  it("normalizes missing room dimensions to the default grid", () => {
    expect(normalizeRoomGrid(null)).toEqual({
      cols: DEFAULT_ROOM_GRID_COLS,
      rows: DEFAULT_ROOM_GRID_ROWS,
    });
  });

  it("anchors a wall object to the nearest wall from the pointer", () => {
    const grid = normalizeRoomGrid({ cols: 14, rows: 9 });
    const leftPlacement = normalizeFixturePlacement("window", 3, 5, grid, resolveNearestWallSide({ x: 10, y: 300 }, grid));
    const topPlacement = normalizeFixturePlacement("window", 3, 5, grid, resolveNearestWallSide({ x: 400, y: 8 }, grid));

    expect(leftPlacement?.col).toBe(0);
    expect(leftPlacement?.height).toBe(2);
    expect(topPlacement?.row).toBe(0);
    expect(topPlacement?.width).toBe(2);
  });

  it("prefers the right wall over the top wall when the pointer is tied in the top-right corner", () => {
    const grid = normalizeRoomGrid({ cols: 6, rows: 6 });
    const wallSide = resolveWallSideForPointer(
      { x: (grid.cols * 96) - 12, y: 12 },
      0,
      grid.cols - 1,
      grid,
    );

    const placement = normalizeFixturePlacement("window", 0, grid.cols - 1, grid, wallSide);

    expect(wallSide).toBe("right");
    expect(placement?.col).toBe(grid.cols - 1);
    expect(placement?.width).toBe(1);
    expect(placement?.height).toBe(2);
  });

  it("treats a vertical top-right wall fixture as right-bound during rendering", () => {
    const grid = normalizeRoomGrid({ cols: 14, rows: 9 });
    expect(
      resolveWallSideFromFixture(
        {
          id: "window-1",
          type: "window",
          x: (grid.cols - 1) * 96,
          y: 0,
          width: 96,
          height: 192,
          label: null,
        },
        grid,
      ),
    ).toBe("right");
  });
});
