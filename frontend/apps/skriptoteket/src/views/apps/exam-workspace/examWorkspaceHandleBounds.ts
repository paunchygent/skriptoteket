/**
 * Exam workspace resize handle bounds.
 *
 * Domain purpose:
 *   The pure geometry behind one desktop column resize handle: turn the
 *   resolved computed gridTemplateColumns of the workspace body into pixel
 *   tracks, and derive the draggable bounds for one panel edge. The panel
 *   width is taken from the editor track only, down to its minimum, so a
 *   drag never squeezes a neighbour. Minimums come from the `.xw-root`
 *   custom properties (`--xw-<column>-min`, `--xw-editor-min`), which the
 *   handle parses with `parsePx`; this module owns no minimum catalogue.
 *
 * Relationships:
 *   - Read by `ExamWorkspaceColumnHandle`, which measures the tracks
 *     transiently on focus and on pointerdown and the minimums from the
 *     closest `.xw-root` ancestor; no listener at rest.
 */

export type ExamWorkspaceHandleEdge = "list" | "side";

export type ExamWorkspaceHandleBounds = {
  value: number;
  min: number;
  max: number;
};

export type ExamWorkspaceHandleMinimums = {
  own: number;
  editor: number;
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
 * Parse a trimmed "<number>px" custom property value into a number. Anything
 * else (empty, unitless, another unit, auto, clamp(), ...) gives null.
 */
export function parsePx(value: string): number | null {
  const match = /^(\d+(?:\.\d+)?)px$/.exec(value.trim());
  if (match === null) {
    return null;
  }
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Derive the draggable bounds for one panel edge from pixel tracks and the
 * CSS-owned minimums. The list edge reads tracks[0] (list) and tracks[1]
 * (editor); the side edge reads the LAST track as the side panel and the
 * track before it as the editor, so [editor, side] (empty body with a drawer)
 * and [list, editor, side] both work. Both edges need at least two tracks,
 * else null. A max below min is floored at min.
 */
export function examWorkspaceHandleBounds(
  tracks: number[],
  edge: ExamWorkspaceHandleEdge,
  mins: ExamWorkspaceHandleMinimums,
): ExamWorkspaceHandleBounds | null {
  if (tracks.length < 2) {
    return null;
  }
  if (edge === "list") {
    const value = tracks[0];
    const editor = tracks[1];
    const max = Math.max(mins.own, value + editor - mins.editor);
    return { value, min: mins.own, max };
  }
  const value = tracks[tracks.length - 1];
  const editor = tracks[tracks.length - 2];
  const max = Math.max(mins.own, value + editor - mins.editor);
  return { value, min: mins.own, max };
}
