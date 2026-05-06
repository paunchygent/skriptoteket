/**
 * Dense-tool primitive contract tests.
 *
 * Relationships:
 * - locks shared menu shell styling for planner and editor popovers
 * - keeps floating dense controls aligned with the modal-surface token contract
 */

import { describe, expect, it } from "vitest";

import { DENSE_MENU_PANEL_CLASS } from "./denseToolPrimitives";

describe("dense tool primitives", () => {
  it("uses the opaque modal surface for shared menu popovers", () => {
    expect(DENSE_MENU_PANEL_CLASS.split(" ")).toContain("bg-modal");
    expect(DENSE_MENU_PANEL_CLASS.split(" ")).not.toContain("bg-panel");
  });
});
