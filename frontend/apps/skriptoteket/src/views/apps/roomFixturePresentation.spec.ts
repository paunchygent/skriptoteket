import { describe, expect, it } from "vitest";

import {
  ROOM_WALL_BAND,
  ROOM_WALL_THICKNESS,
  getFloorFixtureFrameStyle,
  getRoomFloorLayerStyle,
  getRoomSurfaceMetrics,
  getRoomSurfaceStyle,
  getWallFixtureFrameStyle,
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
});
