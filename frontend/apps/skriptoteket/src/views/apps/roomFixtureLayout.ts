/**
 * Room fixture geometry and presentation helpers.
 *
 * This module keeps the classroom builder and the live seating canvas aligned
 * around one shared room model: room templates carry their own grid size,
 * wall-bound objects stay on the room boundary, floor objects occupy classroom
 * space, and labels only appear where they add clarity for teachers.
 */

import type { RoomFixture, RoomFixtureType } from "./classroomPlannerTypes";

export const DEFAULT_ROOM_GRID_COLS = 14;
export const DEFAULT_ROOM_GRID_ROWS = 9;
export const MIN_ROOM_GRID_COLS = 4;
export const MIN_ROOM_GRID_ROWS = 4;
export const ROOM_GRID_UNIT = 96;
const CORNER_WALL_SWITCH_EPSILON = ROOM_GRID_UNIT * 0.05;
const CORNER_LOCAL_SWITCH_EPSILON = 0.08;

export type RoomGridDimensions = {
  cols: number;
  rows: number;
};

export type FixturePlacementKind = "floor" | "wall";
export type WallSide = "top" | "right" | "bottom" | "left";

export type PointerAnchor = {
  x: number;
  y: number;
  relativeX?: number;
  relativeY?: number;
};

export type RoomFixturePaletteEntry = {
  type: RoomFixtureType;
  label: string;
  width: number;
  height: number;
  placementKind: FixturePlacementKind;
  defaultLabel: string | null;
};

export type FixtureRect = {
  row: number;
  col: number;
  width: number;
  height: number;
};

export type NormalizedFixturePlacement = FixtureRect & {
  wallSide: WallSide | null;
};

export const roomFixturePalette: RoomFixturePaletteEntry[] = [
  {
    type: "whiteboard",
    label: "Whiteboard",
    width: 3,
    height: 1,
    placementKind: "wall",
    defaultLabel: "Whiteboard",
  },
  {
    type: "window",
    label: "Fönster",
    width: 2,
    height: 1,
    placementKind: "wall",
    defaultLabel: null,
  },
  {
    type: "door",
    label: "Dörr",
    width: 1,
    height: 1,
    placementKind: "wall",
    defaultLabel: null,
  },
  {
    type: "teacher_desk",
    label: "Kateder",
    width: 2,
    height: 1,
    placementKind: "floor",
    defaultLabel: "Kateder",
  },
  {
    type: "round_table",
    label: "Runt bord",
    width: 2,
    height: 2,
    placementKind: "floor",
    defaultLabel: null,
  },
  {
    type: "square_table",
    label: "Fyrkantigt bord",
    width: 2,
    height: 2,
    placementKind: "floor",
    defaultLabel: null,
  },
  {
    type: "bench",
    label: "Bänk",
    width: 1,
    height: 1,
    placementKind: "floor",
    defaultLabel: null,
  },
];

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

export function normalizeRoomGrid(
  gridLike?: {
    cols?: number;
    rows?: number;
    grid_cols?: number;
    grid_rows?: number;
  } | null,
): RoomGridDimensions {
  const cols = Math.max(MIN_ROOM_GRID_COLS, Math.round(gridLike?.cols ?? gridLike?.grid_cols ?? DEFAULT_ROOM_GRID_COLS));
  const rows = Math.max(MIN_ROOM_GRID_ROWS, Math.round(gridLike?.rows ?? gridLike?.grid_rows ?? DEFAULT_ROOM_GRID_ROWS));
  return { cols, rows };
}

export function getRoomGridWidth(grid: RoomGridDimensions): number {
  return grid.cols * ROOM_GRID_UNIT;
}

export function getRoomGridHeight(grid: RoomGridDimensions): number {
  return grid.rows * ROOM_GRID_UNIT;
}

export function getRoomFixturePaletteEntry(type: RoomFixtureType): RoomFixturePaletteEntry | undefined {
  return roomFixturePalette.find((entry) => entry.type === type);
}

export function isWallFixtureType(type: RoomFixtureType): boolean {
  return getRoomFixturePaletteEntry(type)?.placementKind === "wall";
}

export function isFloorFixtureType(type: RoomFixtureType): boolean {
  return getRoomFixturePaletteEntry(type)?.placementKind === "floor";
}

export function buildRoomFixtureLabel(type: RoomFixtureType): string | null {
  return getRoomFixturePaletteEntry(type)?.defaultLabel ?? null;
}

export function rectanglesOverlap(left: FixtureRect, right: FixtureRect): boolean {
  return (
    left.col < right.col + right.width
    && left.col + left.width > right.col
    && left.row < right.row + right.height
    && left.row + left.height > right.row
  );
}

export function fixtureContainsCell(fixture: FixtureRect, row: number, col: number): boolean {
  return (
    row >= fixture.row
    && row < fixture.row + fixture.height
    && col >= fixture.col
    && col < fixture.col + fixture.width
  );
}

export function resolveWallSideForCell(
  row: number,
  col: number,
  grid: RoomGridDimensions,
): WallSide | null {
  if (row === 0) {
    return "top";
  }
  if (row === grid.rows - 1) {
    return "bottom";
  }
  if (col === 0) {
    return "left";
  }
  if (col === grid.cols - 1) {
    return "right";
  }
  return null;
}

export function resolveNearestWallSide(pointer: PointerAnchor, grid: RoomGridDimensions): WallSide {
  const width = getRoomGridWidth(grid);
  const height = getRoomGridHeight(grid);
  const distances: Array<{ side: WallSide; distance: number }> = [
    { side: "top", distance: pointer.y },
    { side: "bottom", distance: height - pointer.y },
    { side: "left", distance: pointer.x },
    { side: "right", distance: width - pointer.x },
  ];

  return distances.reduce((closest, current) => {
    return current.distance < closest.distance ? current : closest;
  }).side;
}

function pickClosestWall(
  distances: Array<{ side: WallSide; distance: number }>,
): WallSide {
  return distances.reduce((closest, current) => {
    if (current.distance < closest.distance) {
      return current;
    }
    if (current.distance > closest.distance) {
      return closest;
    }

    const currentIsVertical = current.side === "left" || current.side === "right";
    const closestIsVertical = closest.side === "left" || closest.side === "right";
    if (currentIsVertical && !closestIsVertical) {
      return current;
    }
    return closest;
  }).side;
}

export function resolveWallSideForPointer(
  pointer: PointerAnchor,
  row: number,
  col: number,
  grid: RoomGridDimensions,
): WallSide {
  const onTop = row === 0;
  const onBottom = row === grid.rows - 1;
  const onLeft = col === 0;
  const onRight = col === grid.cols - 1;

  if (onRight && (onTop || onBottom)) {
    return "right";
  }
  if (onLeft && (onTop || onBottom)) {
    return "left";
  }

  const boundaryDistances: Array<{ side: WallSide; distance: number }> = [];
  if (onTop) {
    boundaryDistances.push({ side: "top", distance: pointer.y });
  }
  if (onBottom) {
    boundaryDistances.push({ side: "bottom", distance: getRoomGridHeight(grid) - pointer.y });
  }
  if (onLeft) {
    boundaryDistances.push({ side: "left", distance: pointer.x });
  }
  if (onRight) {
    boundaryDistances.push({ side: "right", distance: getRoomGridWidth(grid) - pointer.x });
  }

  if (boundaryDistances.length === 1) {
    return boundaryDistances[0].side;
  }
  if (boundaryDistances.length > 1) {
    if (pointer.relativeX !== undefined && pointer.relativeY !== undefined) {
      if (onTop && onRight) {
        return (1 - pointer.relativeX) <= pointer.relativeY + CORNER_LOCAL_SWITCH_EPSILON
          ? "right"
          : "top";
      }
      if (onBottom && onRight) {
        return (1 - pointer.relativeX) <= (1 - pointer.relativeY) + CORNER_LOCAL_SWITCH_EPSILON
          ? "right"
          : "bottom";
      }
      if (onTop && onLeft) {
        return pointer.relativeX <= pointer.relativeY + CORNER_LOCAL_SWITCH_EPSILON
          ? "left"
          : "top";
      }
      if (onBottom && onLeft) {
        return pointer.relativeX <= (1 - pointer.relativeY) + CORNER_LOCAL_SWITCH_EPSILON
          ? "left"
          : "bottom";
      }
    }

    const verticalWall = boundaryDistances.find((distance) => {
      return distance.side === "left" || distance.side === "right";
    });
    const horizontalWall = boundaryDistances.find((distance) => {
      return distance.side === "top" || distance.side === "bottom";
    });

    if (
      verticalWall
      && horizontalWall
      && Math.abs(verticalWall.distance - horizontalWall.distance) <= CORNER_WALL_SWITCH_EPSILON
    ) {
      return verticalWall.side;
    }
    return pickClosestWall(boundaryDistances);
  }

  return pickClosestWall([
    { side: "top", distance: pointer.y },
    { side: "bottom", distance: getRoomGridHeight(grid) - pointer.y },
    { side: "left", distance: pointer.x },
    { side: "right", distance: getRoomGridWidth(grid) - pointer.x },
  ]);
}

export function normalizeFixturePlacement(
  type: RoomFixtureType,
  row: number,
  col: number,
  grid: RoomGridDimensions,
  wallSideOverride?: WallSide | null,
): NormalizedFixturePlacement | null {
  const paletteEntry = getRoomFixturePaletteEntry(type);
  if (!paletteEntry) {
    return null;
  }

  if (paletteEntry.placementKind === "floor") {
    if (col + paletteEntry.width > grid.cols || row + paletteEntry.height > grid.rows) {
      return null;
    }
    return {
      row,
      col,
      width: paletteEntry.width,
      height: paletteEntry.height,
      wallSide: null,
    };
  }

  const wallSide = wallSideOverride ?? resolveWallSideForCell(row, col, grid);
  if (!wallSide) {
    return null;
  }

  const isHorizontal = wallSide === "top" || wallSide === "bottom";
  const width = isHorizontal ? paletteEntry.width : paletteEntry.height;
  const height = isHorizontal ? paletteEntry.height : paletteEntry.width;

  if (wallSide === "top" || wallSide === "bottom") {
    return {
      row: wallSide === "top" ? 0 : grid.rows - height,
      col: clamp(col - Math.floor(width / 2), 0, grid.cols - width),
      width,
      height,
      wallSide,
    };
  }

  return {
    row: clamp(row - Math.floor(height / 2), 0, grid.rows - height),
    col: wallSide === "left" ? 0 : grid.cols - width,
    width,
    height,
    wallSide,
  };
}

export function resolveWallSideFromFixture(
  fixture: RoomFixture,
  grid: RoomGridDimensions,
): WallSide | null {
  if (!isWallFixtureType(fixture.type)) {
    return null;
  }

  const gridWidth = getRoomGridWidth(grid);
  const gridHeight = getRoomGridHeight(grid);
  const prefersVerticalWall = fixture.height >= fixture.width;

  if (prefersVerticalWall) {
    if (fixture.x === 0) {
      return "left";
    }
    if (fixture.x + fixture.width === gridWidth) {
      return "right";
    }
  }

  if (fixture.y === 0) {
    return "top";
  }
  if (fixture.y + fixture.height === gridHeight) {
    return "bottom";
  }

  if (!prefersVerticalWall) {
    if (fixture.x === 0) {
      return "left";
    }
    if (fixture.x + fixture.width === gridWidth) {
      return "right";
    }
  }
  return null;
}
