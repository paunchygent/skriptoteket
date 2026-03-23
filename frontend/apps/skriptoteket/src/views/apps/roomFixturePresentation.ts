/**
 * Shared room-fixture presentation helpers.
 *
 * This module keeps wall objects on dedicated wall bands around the classroom
 * floor so the builder, preview surface, and live seating canvas can render
 * one consistent room model without letting wall-bound objects consume floor
 * tiles.
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
  return type === "whiteboard" || type === "teacher_desk";
}

export function getFixtureWallSide(
  fixture: RoomFixture,
  grid: RoomGridDimensions,
): WallSide | null {
  return resolveWallSideFromFixture(fixture, grid);
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
