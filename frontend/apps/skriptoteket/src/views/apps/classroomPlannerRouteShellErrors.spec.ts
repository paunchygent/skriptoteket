import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";

describe("normalizeClassroomPlannerUiError", () => {
  it("keeps backend-facing API messages", () => {
    expect(
      normalizeClassroomPlannerUiError(
        new ApiError({
          code: "TEST",
          message: "Servern sade nej.",
          status: 400,
        }),
        "Fallback",
      ),
    ).toBe("Servern sade nej.");
  });

  it("suppresses unexpected runtime exception text", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    expect(
      normalizeClassroomPlannerUiError(
        new TypeError("Cannot read properties of undefined (reading 'map')"),
        "Kunde inte öppna reglerna just nu.",
      ),
    ).toBe("Kunde inte öppna reglerna just nu.");
    expect(consoleError).toHaveBeenCalledOnce();
  });

  it("suppresses runtime-looking messages even when they are rethrown as generic errors", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    expect(
      normalizeClassroomPlannerUiError(
        new Error("Cannot read properties of undefined (reading 'map')"),
        "Kunde inte öppna reglerna just nu.",
      ),
    ).toBe("Kunde inte öppna reglerna just nu.");
    expect(consoleError).toHaveBeenCalledOnce();
  });

  it("preserves explicit non-runtime error messages", () => {
    expect(
      normalizeClassroomPlannerUiError(
        new Error("Exporten blev klar men kunde inte laddas ned automatiskt."),
        "Fallback",
      ),
    ).toBe("Exporten blev klar men kunde inte laddas ned automatiskt.");
  });
});
