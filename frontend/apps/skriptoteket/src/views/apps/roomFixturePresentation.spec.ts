import { describe, expect, it } from "vitest";

import {
  ROOM_WALL_BAND,
  ROOM_WALL_THICKNESS,
  getFloorFixtureFrameStyle,
  getCanonicalFixtureLabel,
  getRoomFloorLayerStyle,
  getRoomSurfaceMetrics,
  getRoomSurfaceStyle,
  getWallFixtureFrameStyle,
  normalizePresentedFixtures,
} from "./roomFixturePresentation";

const grid = { cols: 14, rows: 9 };

describe("roomFixturePresentation", () => {
  it("adds dedicated wall bands around the classroom floor", () => {
    expect(getRoomSurfaceMetrics(grid)).toEqual({
      width: (14 * 96) + (ROOM_WALL_BAND * 2),
      height: (9 * 96) + (ROOM_WALL_BAND * 2),
    });
    expect(getRoomSurfaceStyle(grid)).toEqual({
      width: `${(14 * 96) + (ROOM_WALL_BAND * 2)}px`,
      height: `${(9 * 96) + (ROOM_WALL_BAND * 2)}px`,
    });
    expect(getRoomFloorLayerStyle(grid)).toEqual({
      left: `${ROOM_WALL_BAND}px`,
      top: `${ROOM_WALL_BAND}px`,
      width: `${14 * 96}px`,
      height: `${9 * 96}px`,
    });
  });

  it("keeps floor fixtures on the floor layer", () => {
    expect(getFloorFixtureFrameStyle({
      id: "desk-1",
      type: "teacher_desk",
      x: 96,
      y: 192,
      width: 192,
      height: 96,
      label: "Kateder",
    })).toEqual({
      left: "96px",
      top: "192px",
      width: "192px",
      height: "96px",
    });
  });

  it("renders wall fixtures on wall bands instead of floor tiles", () => {
    expect(getWallFixtureFrameStyle({
      id: "whiteboard-1",
      type: "whiteboard",
      x: 384,
      y: 0,
      width: 288,
      height: 96,
      label: "Whiteboard",
    }, grid)).toEqual({
      left: `${ROOM_WALL_BAND + 384}px`,
      top: `${ROOM_WALL_BAND - ROOM_WALL_THICKNESS}px`,
      width: "288px",
      height: `${ROOM_WALL_THICKNESS}px`,
    });

    expect(getWallFixtureFrameStyle({
      id: "window-1",
      type: "window",
      x: 1248,
      y: 96,
      width: 96,
      height: 192,
      label: null,
    }, grid)).toEqual({
      left: `${ROOM_WALL_BAND + (14 * 96)}px`,
      top: `${ROOM_WALL_BAND + 96}px`,
      width: `${ROOM_WALL_THICKNESS}px`,
      height: "192px",
    });
  });

  it("normalizes localized labels and coalesces benches and whiteboards for shared surfaces", () => {
    const fixtures = normalizePresentedFixtures([
      { id: "bench-1", type: "bench", x: 96, y: 384, width: 96, height: 96, label: null },
      { id: "bench-2", type: "bench", x: 192, y: 384, width: 96, height: 96, label: null },
      { id: "whiteboard-1", type: "whiteboard", x: 288, y: 0, width: 192, height: 96, label: "Old" },
      { id: "whiteboard-2", type: "whiteboard", x: 480, y: 0, width: 96, height: 96, label: null },
      { id: "door-1", type: "door", x: 0, y: 288, width: 96, height: 96, label: null },
    ], grid);

    expect(getCanonicalFixtureLabel("window")).toBe("Fönster");

    const bench = fixtures.find((fixture) => fixture.type === "bench");
    const whiteboard = fixtures.find((fixture) => fixture.type === "whiteboard");
    const door = fixtures.find((fixture) => fixture.type === "door");

    expect(bench).toMatchObject({
      sourceIds: ["bench-1", "bench-2"],
      displayLabel: "Bänk",
      width: 192,
      tone: "muted",
    });
    expect(whiteboard).toMatchObject({
      sourceIds: ["whiteboard-1", "whiteboard-2"],
      displayLabel: "Whiteboard",
      width: 288,
      wallSide: "top",
    });
    expect(door).toMatchObject({
      displayLabel: "Dörr",
      labelOrientation: "vertical",
      wallSide: "left",
    });
  });
});
