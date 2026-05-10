/**
 * Phone classroom seat-map layout helpers.
 *
 * Purpose:
 *   Translate classroom template geometry into CSS grid placement for the
 *   simplified phone classroom maps without mixing layout math into Vue views.
 *
 * Relationships:
 *   - consumed by `PlannerPhoneClassroomSeatMap.vue`
 *   - delegates canonical wall/floor fixture semantics to `roomFixtureLayout.ts`
 */

import type { RoomFixture } from "./classroomPlannerTypes";
import {
  isWallFixtureType,
  resolveWallSideFromFixture,
  type RoomGridDimensions,
  ROOM_GRID_UNIT,
} from "./roomFixtureLayout";

type GridPlacedSeat = {
  x: number;
  y: number;
};

function gridStartFromCoordinate(value: number): number {
  return Math.max(1, Math.round(value / ROOM_GRID_UNIT) + 1);
}

function gridSpanFromSize(value: number): number {
  return Math.max(1, Math.round(value / ROOM_GRID_UNIT));
}

export function buildPhoneSeatGridStyle(seat: GridPlacedSeat): Record<string, string> {
  return {
    gridColumn: `${gridStartFromCoordinate(seat.x)} / span 1`,
    gridRow: `${gridStartFromCoordinate(seat.y)} / span 1`,
  };
}

export function buildPhoneFixtureGridStyle(
  fixture: RoomFixture,
  roomGrid: RoomGridDimensions,
): Record<string, string> {
  const wallSide = isWallFixtureType(fixture.type)
    ? resolveWallSideFromFixture(fixture, roomGrid)
    : null;
  if (wallSide === "top" || wallSide === "bottom") {
    return {
      gridColumn: `${gridStartFromCoordinate(fixture.x)} / span ${gridSpanFromSize(fixture.width)}`,
      gridRow: `${wallSide === "top" ? 1 : roomGrid.rows} / span 1`,
    };
  }
  if (wallSide === "left" || wallSide === "right") {
    return {
      gridColumn: `${wallSide === "left" ? 1 : roomGrid.cols} / span 1`,
      gridRow: `${gridStartFromCoordinate(fixture.y)} / span ${gridSpanFromSize(fixture.height)}`,
    };
  }
  return {
    gridColumn: `${gridStartFromCoordinate(fixture.x)} / span ${gridSpanFromSize(fixture.width)}`,
    gridRow: `${gridStartFromCoordinate(fixture.y)} / span ${gridSpanFromSize(fixture.height)}`,
  };
}

export function buildPhoneFixtureLabel(fixture: RoomFixture): string {
  if (fixture.type === "teacher_desk") {
    return "Kateder";
  }
  if (fixture.type === "door") {
    return "Dörr";
  }
  if (fixture.type === "window") {
    return "Fönster";
  }
  return "Tavla";
}

export function buildPhoneFixtureVisibleLabel(fixture: RoomFixture): string {
  return isWallFixtureType(fixture.type) ? "" : buildPhoneFixtureLabel(fixture);
}

export function buildPhoneFixtureClass(fixture: RoomFixture, roomGrid: RoomGridDimensions): string[] {
  const wallSide = isWallFixtureType(fixture.type)
    ? resolveWallSideFromFixture(fixture, roomGrid)
    : null;
  return [
    `planner-phone-fixed-seat-map-fixture-${fixture.type}`,
    wallSide ? `planner-phone-fixed-seat-map-fixture-wall-${wallSide}` : "",
  ].filter(Boolean);
}
