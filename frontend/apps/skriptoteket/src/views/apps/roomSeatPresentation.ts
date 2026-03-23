/**
 * Room-seat presentation helpers.
 *
 * This module keeps seat geometry and visual framing shared between the room
 * builder, preview, and live seating canvas so seats read as circular places
 * rather than as square room tiles.
 */

import type { Seat } from "./classroomPlannerTypes";

import { ROOM_GRID_UNIT } from "./roomFixtureLayout";

export const ROOM_SEAT_SIZE = 72;
export const ROOM_SEAT_OFFSET = (ROOM_GRID_UNIT - ROOM_SEAT_SIZE) / 2;

export function getSeatFrameStyle(
  seat: Pick<Seat, "x" | "y">,
): Record<string, string> {
  return {
    left: `${seat.x + ROOM_SEAT_OFFSET}px`,
    top: `${seat.y + ROOM_SEAT_OFFSET}px`,
    width: `${ROOM_SEAT_SIZE}px`,
    height: `${ROOM_SEAT_SIZE}px`,
  };
}

export function getSeatGhostFrameStyle(
  row: number,
  col: number,
): Record<string, string> {
  return {
    left: `${(col * ROOM_GRID_UNIT) + ROOM_SEAT_OFFSET}px`,
    top: `${(row * ROOM_GRID_UNIT) + ROOM_SEAT_OFFSET}px`,
    width: `${ROOM_SEAT_SIZE}px`,
    height: `${ROOM_SEAT_SIZE}px`,
  };
}
