/**
 * Room-template editor domain helpers.
 *
 * This module keeps the builder's placement rules, editor-state hydration, and
 * payload serialization separate from the modal shell so the room editor can be
 * tested as a bounded frontend module instead of one large component.
 */

import type { RoomFixture, RoomFixtureType, RoomTemplate, Seat } from "./classroomPlannerTypes";
import {
  ROOM_GRID_UNIT,
  buildRoomFixtureLabel,
  fixtureContainsCell,
  isFloorFixtureType,
  isWallFixtureType,
  normalizeFixturePlacement,
  normalizeRoomGrid,
  rectanglesOverlap,
  type RoomGridDimensions,
  type WallSide,
} from "./roomFixtureLayout";

export type BuilderTool = "seat" | "erase" | RoomFixtureType;

export type FixturePlacement = {
  id: string;
  type: RoomFixtureType;
  col: number;
  row: number;
  width: number;
  height: number;
  label: string | null;
};

export type HoveredCell = {
  row: number;
  col: number;
};

export function seatKey(row: number, col: number): string {
  return `${row}:${col}`;
}

export function isSeatAt(seatCells: readonly string[], row: number, col: number): boolean {
  return seatCells.includes(seatKey(row, col));
}

export function findFloorFixtureAt(
  fixtures: readonly FixturePlacement[],
  row: number,
  col: number,
): FixturePlacement | null {
  return (
    fixtures.find((fixture) => {
      return isFloorFixtureType(fixture.type) && fixtureContainsCell(fixture, row, col);
    }) ?? null
  );
}

export function findWallFixtureAt(
  fixtures: readonly FixturePlacement[],
  row: number,
  col: number,
): FixturePlacement | null {
  return (
    fixtures.find((fixture) => {
      return isWallFixtureType(fixture.type) && fixtureContainsCell(fixture, row, col);
    }) ?? null
  );
}

export function fixtureFits(
  fixtures: readonly FixturePlacement[],
  seatCells: readonly string[],
  type: RoomFixtureType,
  row: number,
  col: number,
  roomGrid: RoomGridDimensions,
  wallSideOverride?: WallSide | null,
): boolean {
  const placement = normalizeFixturePlacement(type, row, col, roomGrid, wallSideOverride);
  if (!placement) {
    return false;
  }

  if (isWallFixtureType(type)) {
    return !fixtures.some((fixture) => {
      return isWallFixtureType(fixture.type) && rectanglesOverlap(placement, fixture);
    });
  }

  for (let currentRow = placement.row; currentRow < placement.row + placement.height; currentRow += 1) {
    for (let currentCol = placement.col; currentCol < placement.col + placement.width; currentCol += 1) {
      if (isSeatAt(seatCells, currentRow, currentCol) || findFloorFixtureAt(fixtures, currentRow, currentCol)) {
        return false;
      }
    }
  }

  return true;
}

export function templateFitsGrid(
  seatCells: readonly string[],
  fixtures: readonly FixturePlacement[],
  cols: number,
  rows: number,
): boolean {
  const allSeatsFit = seatCells.every((value) => {
    const [row, col] = value.split(":").map(Number);
    return row < rows && col < cols;
  });
  if (!allSeatsFit) {
    return false;
  }

  return fixtures.every((fixture) => {
    return fixture.row + fixture.height <= rows && fixture.col + fixture.width <= cols;
  });
}

export function hydrateRoomTemplateEditor(template?: RoomTemplate | null): {
  name: string;
  gridCols: number;
  gridRows: number;
  seatCells: string[];
  fixtures: FixturePlacement[];
} {
  const normalizedGrid = normalizeRoomGrid(template);
  return {
    name: template?.name ?? "",
    gridCols: normalizedGrid.cols,
    gridRows: normalizedGrid.rows,
    seatCells:
      template?.seats.map((seat) => {
        return seatKey(Math.round(seat.y / ROOM_GRID_UNIT), Math.round(seat.x / ROOM_GRID_UNIT));
      }) ?? [],
    fixtures:
      template?.fixtures.map((fixture) => ({
        id: fixture.id,
        type: fixture.type,
        row: Math.round(fixture.y / ROOM_GRID_UNIT),
        col: Math.round(fixture.x / ROOM_GRID_UNIT),
        width: Math.max(1, Math.round(fixture.width / ROOM_GRID_UNIT)),
        height: Math.max(1, Math.round(fixture.height / ROOM_GRID_UNIT)),
        label: fixture.label ?? buildRoomFixtureLabel(fixture.type),
      })) ?? [],
  };
}

export function buildParsedSeats(seatCells: readonly string[]): Seat[] {
  return seatCells
    .map((value) => {
      const [row, col] = value.split(":").map(Number);
      return { row, col };
    })
    .sort((left, right) => (left.row - right.row) || (left.col - right.col))
    .map((cell, index) => ({
      id: `seat-${index + 1}`,
      x: cell.col * ROOM_GRID_UNIT,
      y: cell.row * ROOM_GRID_UNIT,
      zone: null,
    }));
}

export function buildParsedFixtures(fixtures: readonly FixturePlacement[]): RoomFixture[] {
  return fixtures.map((fixture) => ({
    id: fixture.id,
    type: fixture.type,
    x: fixture.col * ROOM_GRID_UNIT,
    y: fixture.row * ROOM_GRID_UNIT,
    width: fixture.width * ROOM_GRID_UNIT,
    height: fixture.height * ROOM_GRID_UNIT,
    label: fixture.label,
  }));
}
