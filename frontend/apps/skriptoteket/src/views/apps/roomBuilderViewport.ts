/**
 * Room-builder viewport helpers.
 *
 * This module keeps the builder zoom model deterministic and local to the
 * modal session. It separates saved room geometry from view-only concerns such
 * as fit-to-view, zoom stepping, and scaled surface framing.
 */

export const MIN_ROOM_VIEWPORT_SCALE = 0.35;
export const MAX_ROOM_VIEWPORT_SCALE = 1.6;
export const ROOM_VIEWPORT_SCALE_STEP = 0.1;
const ROOM_VIEWPORT_PADDING = 24;

export type RoomViewportSize = {
  width: number;
  height: number;
};

export function clampRoomViewportScale(scale: number): number {
  return Math.min(Math.max(scale, MIN_ROOM_VIEWPORT_SCALE), MAX_ROOM_VIEWPORT_SCALE);
}

export function computeRoomViewportFitScale(
  viewport: RoomViewportSize,
  surface: RoomViewportSize,
): number {
  if (viewport.width <= 0 || viewport.height <= 0 || surface.width <= 0 || surface.height <= 0) {
    return 1;
  }

  const widthScale = (viewport.width - ROOM_VIEWPORT_PADDING) / surface.width;
  const heightScale = (viewport.height - ROOM_VIEWPORT_PADDING) / surface.height;

  return clampRoomViewportScale(Math.min(widthScale, heightScale, 1));
}

export function getScaledRoomSurfaceStyle(
  surface: RoomViewportSize,
  scale: number,
): Record<string, string> {
  return {
    width: `${surface.width * scale}px`,
    height: `${surface.height * scale}px`,
  };
}
