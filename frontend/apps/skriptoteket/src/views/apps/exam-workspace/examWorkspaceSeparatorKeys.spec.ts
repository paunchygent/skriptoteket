/**
 * Exam workspace separator keyboard behavior.
 *
 * Expected behavior:
 *   Arrow keys move the panel 16 px (64 px with Shift), clamped to
 *   [min, max]; Home goes to the minimum, End to the maximum; Enter
 *   collapses and restores; Shift+Enter resets to the default. Any other key
 *   returns null.
 */

import { describe, expect, it } from "vitest";

import { examWorkspaceSeparatorKeyAction } from "./examWorkspaceSeparatorKeys";

const BOUNDS = { value: 320, min: 300, max: 600 };

describe("examWorkspaceSeparatorKeyAction", () => {
  it("moves 16 px per arrow press", () => {
    expect(examWorkspaceSeparatorKeyAction({ key: "ArrowRight", shiftKey: false }, BOUNDS)).toEqual({
      kind: "set",
      value: 336,
    });
    expect(examWorkspaceSeparatorKeyAction({ key: "ArrowLeft", shiftKey: false }, BOUNDS)).toEqual({
      kind: "set",
      value: 304,
    });
  });

  it("moves 64 px with Shift held", () => {
    expect(examWorkspaceSeparatorKeyAction({ key: "ArrowRight", shiftKey: true }, BOUNDS)).toEqual({
      kind: "set",
      value: 384,
    });
    expect(examWorkspaceSeparatorKeyAction({ key: "ArrowLeft", shiftKey: true }, BOUNDS)).toEqual({
      kind: "set",
      value: 300,
    });
  });

  it("clamps steps at both bounds", () => {
    expect(
      examWorkspaceSeparatorKeyAction({ key: "ArrowLeft", shiftKey: true }, BOUNDS),
    ).toEqual({ kind: "set", value: 300 });
    expect(
      examWorkspaceSeparatorKeyAction(
        { key: "ArrowRight", shiftKey: true },
        { value: 590, min: 300, max: 600 },
      ),
    ).toEqual({ kind: "set", value: 600 });
  });

  it("jumps to the minimum on Home and the maximum on End", () => {
    expect(examWorkspaceSeparatorKeyAction({ key: "Home", shiftKey: false }, BOUNDS)).toEqual({
      kind: "set",
      value: 300,
    });
    expect(examWorkspaceSeparatorKeyAction({ key: "End", shiftKey: false }, BOUNDS)).toEqual({
      kind: "set",
      value: 600,
    });
  });

  it("collapses and restores on Enter", () => {
    expect(examWorkspaceSeparatorKeyAction({ key: "Enter", shiftKey: false }, BOUNDS)).toEqual({
      kind: "toggle-collapse",
    });
  });

  it("resets to the default on Shift+Enter", () => {
    expect(examWorkspaceSeparatorKeyAction({ key: "Enter", shiftKey: true }, BOUNDS)).toEqual({
      kind: "reset",
    });
  });

  it("returns null for an unrelated key", () => {
    expect(examWorkspaceSeparatorKeyAction({ key: "a", shiftKey: false }, BOUNDS)).toBeNull();
    expect(examWorkspaceSeparatorKeyAction({ key: "Escape", shiftKey: false }, BOUNDS)).toBeNull();
  });
});
