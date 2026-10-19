/**
 * Exam workspace resize handle bounds.
 *
 * Expected behavior:
 *   parseGridTracks turns a resolved computed gridTemplateColumns value such
 *   as "260px 700px 320px" into numbers; any track not in px gives null for
 *   the whole parse. examWorkspaceHandleBounds takes the panel width from
 *   the editor track only, down to its minimum: for edge "list" value is
 *   tracks[0] and max is tracks[0] + tracks[1] - EXAM_WORKSPACE_EDITOR_MIN;
 *   for edge "side" value is tracks[2] and max is tracks[2] + tracks[1] -
 *   EXAM_WORKSPACE_EDITOR_MIN. A max below min is floored at min. A missing
 *   needed track gives null.
 */

import { describe, expect, it } from "vitest";

import {
  examWorkspaceHandleBounds,
  parseGridTracks,
} from "./examWorkspaceHandleBounds";
import { EXAM_WORKSPACE_EDITOR_MIN } from "./useExamWorkspaceColumnSizes";

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

describe("examWorkspaceHandleBounds", () => {
  it("bounds the list edge against the editor track", () => {
    expect(examWorkspaceHandleBounds([260, 700, 320], "list", 260)).toEqual({
      value: 260,
      min: 260,
      max: 260 + 700 - EXAM_WORKSPACE_EDITOR_MIN,
    });
  });

  it("bounds the side edge against the editor track", () => {
    expect(examWorkspaceHandleBounds([260, 700, 320], "side", 300)).toEqual({
      value: 320,
      min: 300,
      max: 320 + 700 - EXAM_WORKSPACE_EDITOR_MIN,
    });
  });

  it("floors max at min when the editor is at its minimum", () => {
    expect(examWorkspaceHandleBounds([260, 400, 300], "list", 260)).toEqual({
      value: 260,
      min: 260,
      max: 260,
    });
  });

  it("returns null for a missing side track", () => {
    expect(examWorkspaceHandleBounds([260, 700], "side", 300)).toBeNull();
  });

  it("returns null for a missing list track", () => {
    expect(examWorkspaceHandleBounds([260], "list", 260)).toBeNull();
  });
});
