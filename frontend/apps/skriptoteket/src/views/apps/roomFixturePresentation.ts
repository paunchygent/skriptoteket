/**
 * Shared room-fixture presentation helpers.
 *
 * This module is the canonical scene-presentation seam for classroom planner
 * surfaces. It keeps wall objects on dedicated wall bands, localizes visible
 * labels, coalesces presentation-only spans, and exposes grayscale-first
 * inputs so preview and export-adjacent surfaces render one consistent room.
 */

import type { RoomFixture, RoomFixtureType } from "./classroomPlannerTypes";
import {
  ROOM_GRID_UNIT,
  resolveWallSideFromFixture,
  type RoomGridDimensions,
  type WallSide,
} from "./roomFixtureLayout";

export const ROOM_WALL_BAND = 28;
export const ROOM_WALL_THICKNESS = 18;

export type GridFixturePlacement = {
  id: string;
  type: RoomFixtureType;
  row: number;
  col: number;
  width: number;
  height: number;
  label: string | null;
};

export type FixtureRenderSurface = "absolute" | "builder-grid" | "ghost";
export type FixtureLabelOrientation = "horizontal" | "vertical";
export type FixturePresentationTone = "outline" | "muted" | "strong";

export type PresentedRoomFixture = RoomFixture & {
  sourceIds?: readonly string[];
  displayLabel?: string | null;
  labelVisible?: boolean;
  labelOrientation?: FixtureLabelOrientation;
  wallSide?: WallSide | null;
  tone?: FixturePresentationTone;
};

const CANONICAL_FIXTURE_LABELS: Record<RoomFixtureType, string | null> = {
  whiteboard: "Whiteboard",
  teacher_desk: "Kateder",
  window: "Fönster",
  door: "Dörr",
  round_table: null,
  square_table: null,
  bench: "Bänk",
};

const FIXTURE_TONES: Record<RoomFixtureType, FixturePresentationTone> = {
  whiteboard: "outline",
  teacher_desk: "strong",
  window: "outline",
  door: "outline",
  round_table: "outline",
  square_table: "outline",
  bench: "muted",
};

function getFloorWidth(grid: RoomGridDimensions): number {
  return grid.cols * ROOM_GRID_UNIT;
}

function getFloorHeight(grid: RoomGridDimensions): number {
  return grid.rows * ROOM_GRID_UNIT;
}

export function getRoomSurfaceMetrics(grid: RoomGridDimensions): { width: number; height: number } {
  return {
    width: getFloorWidth(grid) + (ROOM_WALL_BAND * 2),
    height: getFloorHeight(grid) + (ROOM_WALL_BAND * 2),
  };
}

export function buildRoomFixtureFromGridPlacement(fixture: GridFixturePlacement): RoomFixture {
  return {
    id: fixture.id,
    type: fixture.type,
    x: fixture.col * ROOM_GRID_UNIT,
    y: fixture.row * ROOM_GRID_UNIT,
    width: fixture.width * ROOM_GRID_UNIT,
    height: fixture.height * ROOM_GRID_UNIT,
    label: fixture.label,
  };
}

export function getRoomSurfaceStyle(grid: RoomGridDimensions): Record<string, string> {
  const surface = getRoomSurfaceMetrics(grid);
  return {
    width: `${surface.width}px`,
    height: `${surface.height}px`,
  };
}

export function getRoomFloorLayerStyle(grid: RoomGridDimensions): Record<string, string> {
  return {
    left: `${ROOM_WALL_BAND}px`,
    top: `${ROOM_WALL_BAND}px`,
    width: `${getFloorWidth(grid)}px`,
    height: `${getFloorHeight(grid)}px`,
  };
}

export function getFloorPlacementStyle(fixture: GridFixturePlacement): Record<string, string> {
  return {
    left: `${fixture.col * ROOM_GRID_UNIT}px`,
    top: `${fixture.row * ROOM_GRID_UNIT}px`,
    width: `${fixture.width * ROOM_GRID_UNIT}px`,
    height: `${fixture.height * ROOM_GRID_UNIT}px`,
  };
}

export function getFloorFixtureFrameStyle(fixture: RoomFixture): Record<string, string> {
  return {
    left: `${fixture.x}px`,
    top: `${fixture.y}px`,
    width: `${fixture.width}px`,
    height: `${fixture.height}px`,
  };
}

export function getWallFixtureFrameStyle(
  fixture: RoomFixture,
  grid: RoomGridDimensions,
): Record<string, string> {
  const side = resolveWallSideFromFixture(fixture, grid);
  const floorWidth = getFloorWidth(grid);
  const floorHeight = getFloorHeight(grid);

  switch (side) {
    case "top":
      return {
        left: `${ROOM_WALL_BAND + fixture.x}px`,
        top: `${ROOM_WALL_BAND - ROOM_WALL_THICKNESS}px`,
        width: `${fixture.width}px`,
        height: `${ROOM_WALL_THICKNESS}px`,
      };
    case "bottom":
      return {
        left: `${ROOM_WALL_BAND + fixture.x}px`,
        top: `${ROOM_WALL_BAND + floorHeight}px`,
        width: `${fixture.width}px`,
        height: `${ROOM_WALL_THICKNESS}px`,
      };
    case "left":
      return {
        left: `${ROOM_WALL_BAND - ROOM_WALL_THICKNESS}px`,
        top: `${ROOM_WALL_BAND + fixture.y}px`,
        width: `${ROOM_WALL_THICKNESS}px`,
        height: `${fixture.height}px`,
      };
    case "right":
      return {
        left: `${ROOM_WALL_BAND + floorWidth}px`,
        top: `${ROOM_WALL_BAND + fixture.y}px`,
        width: `${ROOM_WALL_THICKNESS}px`,
        height: `${fixture.height}px`,
      };
    default:
      return getFloorFixtureFrameStyle(fixture);
  }
}

export function shouldRenderFixtureLabel(type: RoomFixtureType): boolean {
  return getCanonicalFixtureLabel(type) !== null;
}

export function getFixtureWallSide(
  fixture: RoomFixture,
  grid: RoomGridDimensions,
): WallSide | null {
  return resolveWallSideFromFixture(fixture, grid);
}

export function getCanonicalFixtureLabel(type: RoomFixtureType): string | null {
  return CANONICAL_FIXTURE_LABELS[type];
}

export function normalizePresentedFixtures(
  fixtures: readonly RoomFixture[],
  grid: RoomGridDimensions,
): PresentedRoomFixture[] {
  const normalized = fixtures.map((fixture) => normalizePresentedFixture(fixture, grid));
  const benches = mergePresentedFixtures(
    normalized.filter((fixture) => fixture.type === "bench"),
    canMergeBenches,
    mergePresentedFixtureSpan,
  );
  const whiteboards = mergePresentedFixtures(
    normalized.filter((fixture) => fixture.type === "whiteboard"),
    canMergeWhiteboards,
    mergePresentedFixtureSpan,
  );
  const passthrough = normalized.filter((fixture) => fixture.type !== "bench" && fixture.type !== "whiteboard");

  return [...passthrough, ...benches, ...whiteboards].sort((left, right) => {
    const leftWall = left.wallSide ?? "";
    const rightWall = right.wallSide ?? "";
    return (
      left.y - right.y
      || left.x - right.x
      || leftWall.localeCompare(rightWall)
      || left.type.localeCompare(right.type)
      || left.id.localeCompare(right.id)
    );
  });
}

function normalizePresentedFixture(
  fixture: RoomFixture,
  grid: RoomGridDimensions,
): PresentedRoomFixture {
  const wallSide = resolveWallSideFromFixture(fixture, grid);
  const displayLabel = getCanonicalFixtureLabel(fixture.type);
  return {
    ...fixture,
    sourceIds: [fixture.id],
    displayLabel,
    labelVisible: displayLabel !== null,
    labelOrientation: wallSide === "left" || wallSide === "right" ? "vertical" : "horizontal",
    wallSide,
    tone: FIXTURE_TONES[fixture.type],
  };
}

function mergePresentedFixtures(
  fixtures: PresentedRoomFixture[],
  canMerge: (left: PresentedRoomFixture, right: PresentedRoomFixture) => boolean,
  merge: (left: PresentedRoomFixture, right: PresentedRoomFixture) => PresentedRoomFixture,
): PresentedRoomFixture[] {
  if (fixtures.length === 0) {
    return [];
  }

  const ordered = [...fixtures].sort((left, right) => {
    const leftWall = left.wallSide ?? "";
    const rightWall = right.wallSide ?? "";
    return (
      leftWall.localeCompare(rightWall)
      || left.y - right.y
      || left.x - right.x
      || left.id.localeCompare(right.id)
    );
  });

  const merged: PresentedRoomFixture[] = [];
  let current = ordered[0];
  for (const candidate of ordered.slice(1)) {
    if (canMerge(current, candidate)) {
      current = merge(current, candidate);
      continue;
    }
    merged.push(current);
    current = candidate;
  }
  merged.push(current);
  return merged;
}

function mergePresentedFixtureSpan(
  left: PresentedRoomFixture,
  right: PresentedRoomFixture,
): PresentedRoomFixture {
  const sourceIds = [
    ...(left.sourceIds ?? [left.id]),
    ...(right.sourceIds ?? [right.id]),
  ];
  if (left.wallSide === "left" || left.wallSide === "right") {
    const y = Math.min(left.y, right.y);
    const height = Math.max(left.y + left.height, right.y + right.height) - y;
    return {
      ...left,
      id: sourceIds.join("__"),
      sourceIds,
      y,
      height,
    };
  }

  const x = Math.min(left.x, right.x);
  const width = Math.max(left.x + left.width, right.x + right.width) - x;
  return {
    ...left,
    id: sourceIds.join("__"),
    sourceIds,
    x,
    width,
  };
}

function canMergeBenches(left: PresentedRoomFixture, right: PresentedRoomFixture): boolean {
  return (
    left.type === "bench"
    && right.type === "bench"
    && left.y === right.y
    && left.height === right.height
    && left.x + left.width === right.x
  );
}

function canMergeWhiteboards(left: PresentedRoomFixture, right: PresentedRoomFixture): boolean {
  if (
    left.type !== "whiteboard"
    || right.type !== "whiteboard"
    || left.wallSide === null
    || left.wallSide !== right.wallSide
  ) {
    return false;
  }

  if (left.wallSide === "top" || left.wallSide === "bottom") {
    return left.y === right.y && left.height === right.height && left.x + left.width === right.x;
  }

  return left.x === right.x && left.width === right.width && left.y + left.height === right.y;
}

export function getBenchNeighbors(
  fixture: RoomFixture,
  fixtures: readonly RoomFixture[],
): { left: boolean; right: boolean } {
  if (fixture.type !== "bench") {
    return { left: false, right: false };
  }

  const left = fixtures.some((candidate) => {
    return (
      candidate.id !== fixture.id
      && candidate.type === "bench"
      && candidate.y === fixture.y
      && candidate.height === fixture.height
      && candidate.x + candidate.width === fixture.x
    );
  });
  const right = fixtures.some((candidate) => {
    return (
      candidate.id !== fixture.id
      && candidate.type === "bench"
      && candidate.y === fixture.y
      && candidate.height === fixture.height
      && fixture.x + fixture.width === candidate.x
    );
  });

  return { left, right };
}
