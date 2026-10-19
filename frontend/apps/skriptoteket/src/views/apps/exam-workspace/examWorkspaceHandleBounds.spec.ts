/**
 * Exam workspace resize handle bounds.
 *
 * Expected behavior:
 *   parseGridTracks turns a resolved computed gridTemplateColumns value such
 *   as "260px 700px 320px" into numbers; any track not in px gives null for
 *   the whole parse. parsePx turns a trimmed "<number>px" custom property
 *   value into a number and gives null for anything else. The bounds take the
 *   panel width from the editor track only, down to its minimum: for edge
 *   "list" value is tracks[0] and max is tracks[0] + tracks[1] - editorMin;
 *   for edge "side" value is the LAST track and max is last + previous -
 *   editorMin, so [editor, side] (empty body with a drawer) and
 *   [list, editor, side] both work. A max below min is floored at min. Fewer
 *   than two tracks gives null for either edge.
 */

import { describe, expect, it } from "vitest";

import {
  examWorkspaceHandleBounds,
  parseGridTracks,
  parsePx,
} from "./examWorkspaceHandleBounds";

describe("parseGridTracks", () => {
  it("parses a px track list into numbers", () => {
    expect(parseGridTracks("260px 700px 320px")).toEqual([260, 700, 320]);
  });

  it("parses a two-track list", () => {
    expect(parseGridTracks("260px 700px")).toEqual([260, 700]);
  });

  it("returns null when any track is not in px", () => {
    expect(parseGridTracks("260px 1fr 320px")).toBeNull();
  });

  it("returns null for clamp() and minmax() tracks", () => {
    expect(parseGridTracks("clamp(260px, 18%, 340px) 700px")).toBeNull();
    expect(parseGridTracks("260px minmax(0, 1fr)")).toBeNull();
  });

  it("returns null for an empty value", () => {
    expect(parseGridTracks("")).toBeNull();
  });
});

describe("parsePx", () => {
  it("parses a px custom property value", () => {
    expect(parsePx("260px")).toBe(260);
  });

  it("trims surrounding whitespace", () => {
    expect(parsePx("  280px  ")).toBe(280);
  });

  it("parses a fractional px value", () => {
    expect(parsePx("44.5px")).toBe(44.5);
  });

  it("returns null for a missing or empty value", () => {
    expect(parsePx("")).toBeNull();
  });

  it("returns null for a unitless number", () => {
    expect(parsePx("260")).toBeNull();
  });

  it("returns null for another unit", () => {
    expect(parsePx("260em")).toBeNull();
    expect(parsePx("50%")).toBeNull();
  });

  it("returns null for a non-numeric value", () => {
    expect(parsePx("auto")).toBeNull();
    expect(parsePx("clamp(260px, 18%, 340px)")).toBeNull();
  });
});

describe("examWorkspaceHandleBounds", () => {
  it("bounds the list edge against the editor track", () => {
    expect(examWorkspaceHandleBounds([260, 700, 320], "list", { own: 260, editor: 400 })).toEqual({
      value: 260,
      min: 260,
      max: 260 + 700 - 400,
    });
  });

  it("bounds the side edge against the editor track", () => {
    expect(examWorkspaceHandleBounds([260, 700, 320], "side", { own: 300, editor: 400 })).toEqual({
      value: 320,
      min: 300,
      max: 320 + 700 - 400,
    });
  });

  it("bounds the side edge on a two-track editor/side grid", () => {
    expect(examWorkspaceHandleBounds([700, 320], "side", { own: 300, editor: 400 })).toEqual({
      value: 320,
      min: 300,
      max: 320 + 700 - 400,
    });
  });

  it("bounds the list edge on a two-track list/editor grid", () => {
    expect(examWorkspaceHandleBounds([260, 700], "list", { own: 260, editor: 400 })).toEqual({
      value: 260,
      min: 260,
      max: 260 + 700 - 400,
    });
  });

  it("floors max at min when the editor is at its minimum", () => {
    expect(examWorkspaceHandleBounds([260, 400, 300], "list", { own: 260, editor: 400 })).toEqual({
      value: 260,
      min: 260,
      max: 260,
    });
  });

  it("returns null for a single track on the side edge", () => {
    expect(examWorkspaceHandleBounds([700], "side", { own: 300, editor: 400 })).toBeNull();
  });

  it("returns null for a single track on the list edge", () => {
    expect(examWorkspaceHandleBounds([260], "list", { own: 260, editor: 400 })).toBeNull();
  });
});
