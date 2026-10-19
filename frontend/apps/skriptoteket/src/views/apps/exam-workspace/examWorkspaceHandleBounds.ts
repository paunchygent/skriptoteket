/**
 * Exam workspace resize handle bounds.
 *
 * Domain purpose:
 *   The pure geometry behind one desktop column resize handle: turn the
 *   resolved computed gridTemplateColumns of the workspace body into pixel
 *   tracks, and derive the draggable bounds for one panel edge. The panel
 *   width is taken from the editor track only, down to its minimum, so a
 *   drag never squeezes a neighbour.
 *
 * Relationships:
 *   - Read by `ExamWorkspaceColumnHandle`, which measures the tracks
 *     transiently on focus and on pointerdown; no listener at rest.
 *   - Reuses `EXAM_WORKSPACE_EDITOR_MIN` from `useExamWorkspaceColumnSizes`;
 *     the per-column minimum comes from the caller.
 */

import { EXAM_WORKSPACE_EDITOR_MIN } from "./useExamWorkspaceColumnSizes";

export type ExamWorkspaceHandleEdge = "list" | "side";

export type ExamWorkspaceHandleBounds = {
  value: number;
  min: number;
  max: number;
};

/**
 * Parse a resolved computed gridTemplateColumns value such as
 * "260px 700px 320px" into numbers. Any track not in px (fr, %, clamp(),
 * minmax(), ...) gives null for the whole parse.
 */
export function parseGridTracks(gridTemplateColumns: string): number[] | null {
  const parts = gridTemplateColumns.trim().split(/\s+/).filter((part) => part.length > 0);
  if (parts.length === 0) {
    return null;
  }
  const tracks: number[] = [];
  for (const part of parts) {
    if (!part.endsWith("px")) {
      return null;
    }
    const value = Number(part.slice(0, -"px".length));
    if (!Number.isFinite(value)) {
      return null;
    }
    tracks.push(value);
  }
  return tracks;
}

/**
 * Derive the draggable bounds for one panel edge from pixel tracks
 * ([list, editor] or [list, editor, side]) and the panel's own minimum.
 * A max below min is floored at min. A missing needed track gives null.
 */
export function examWorkspaceHandleBounds(
  tracks: number[],
  edge: ExamWorkspaceHandleEdge,
  min: number,
): ExamWorkspaceHandleBounds | null {
  if (edge === "list") {
    if (tracks.length < 2) {
      return null;
    }
    const value = tracks[0];
    const max = Math.max(min, tracks[0] + tracks[1] - EXAM_WORKSPACE_EDITOR_MIN);
    return { value, min, max };
  }
  if (tracks.length < 3) {
    return null;
  }
  const value = tracks[2];
  const max = Math.max(min, tracks[2] + tracks[1] - EXAM_WORKSPACE_EDITOR_MIN);
  return { value, min, max };
}
