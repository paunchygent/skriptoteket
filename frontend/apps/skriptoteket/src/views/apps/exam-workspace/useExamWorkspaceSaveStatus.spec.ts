/**
 * Exam workspace save status copy (TASK-SKRIPT-40-04-14, C1 and C2).
 *
 * Expected behavior:
 *   The generic save failure reads `Ändringarna kunde inte sparas. Vi
 *   försöker igen automatiskt.` A step refused because questions are still
 *   being converted reports its specific message for the dedicated
 *   `CONVERSION_IN_PROGRESS` code (and for a 422 carrying `item_ids`),
 *   never the generic copy; any other failure falls back to it.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import { AUTOSAVE_FAILURE_COPY, refusalReason } from "./useExamWorkspaceSaveStatus";
import { exam } from "./useExamWorkspaceEditing.history.specSupport";

const GENERIC_COPY = "Ändringarna kunde inte sparas. Vi försöker igen automatiskt.";
const GUARD_COPY =
  "Provet kunde inte sparas. Vänta tills frågorna har konverterats " +
  "innan du ändrar, flyttar eller tar bort dem.";

describe("save status failure copy", () => {
  it("states the generic failure with its automatic retry", () => {
    expect(AUTOSAVE_FAILURE_COPY).toBe(GENERIC_COPY);
  });

  it("reports the conversion refusal for its dedicated code, never the generic copy", () => {
    const error = new ApiError({
      code: "CONVERSION_IN_PROGRESS",
      message: GUARD_COPY,
      details: {},
      status: 422,
    });

    expect(refusalReason(exam(), error)).toBe(GUARD_COPY);
  });

  it("reports the guard message for a 422 carrying converted item ids", () => {
    const error = new ApiError({
      code: "VALIDATION_ERROR",
      message: GUARD_COPY,
      details: { item_ids: ["item_001"] },
      status: 422,
    });

    expect(refusalReason(exam(), error)).toBe(GUARD_COPY);
  });

  it("falls back to the generic copy for any other failure", () => {
    const error = new ApiError({
      code: "VALIDATION_ERROR",
      message: "Validation error",
      details: [],
      status: 422,
    });

    expect(refusalReason(exam(), error)).toBe(GENERIC_COPY);
  });
});
