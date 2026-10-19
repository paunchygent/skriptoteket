/**
 * Guest draft handoff failure classification (TASK-SKRIPT-41-02-05, U1).
 *
 * Expected behavior:
 *   A 422 carrying the server's vault_full marker reports vault_full; every
 *   other 4xx reports permanent; 401 and a superseded session report
 *   deferred; 5xx, 408, 429, sub-400 statuses, and anything that is not an
 *   API error report transient. Classification is by status only, never by
 *   code or message text, and lookalike details never escape their status.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import { SupersededAuthSessionError } from "../../../stores/auth";
import { classifyGuestHandoffFailure } from "./examWorkspaceGuestHandoffFailure";

function apiError(status: number, code = "ERROR", details: unknown = null): ApiError {
  return new ApiError({ code, message: code, status, details });
}

describe("classifyGuestHandoffFailure", () => {
  it("reports permanent rejections the server will never accept", () => {
    expect(classifyGuestHandoffFailure(apiError(422, "DOCUMENT_SCHEMA_OUTDATED"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(422, "VALIDATION_ERROR"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(413, "PAYLOAD_TOO_LARGE"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(403, "FORBIDDEN"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(404, "NOT_FOUND"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(409, "CONFLICT"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(400, "BAD_REQUEST"))).toBe("permanent");
  });

  it("reports transient failures a later try can survive", () => {
    expect(classifyGuestHandoffFailure(apiError(500, "INTERNAL_ERROR"))).toBe("transient");
    expect(classifyGuestHandoffFailure(apiError(502, "BAD_GATEWAY"))).toBe("transient");
    expect(classifyGuestHandoffFailure(apiError(503, "SERVICE_UNAVAILABLE"))).toBe("transient");
    expect(classifyGuestHandoffFailure(apiError(429, "RATE_LIMITED"))).toBe("transient");
    expect(classifyGuestHandoffFailure(apiError(408, "TIMEOUT"))).toBe("transient");
    expect(classifyGuestHandoffFailure(apiError(0, "HTTP_ERROR"))).toBe("transient");
  });

  it("reports transient for anything that is not an API error", () => {
    expect(classifyGuestHandoffFailure(new TypeError("Failed to fetch"))).toBe("transient");
    expect(classifyGuestHandoffFailure(new Error("x"))).toBe("transient");
    expect(classifyGuestHandoffFailure("boom")).toBe("transient");
    expect(classifyGuestHandoffFailure(undefined)).toBe("transient");
  });

  it("defers when the sign-in ended", () => {
    expect(classifyGuestHandoffFailure(apiError(401, "UNAUTHORIZED"))).toBe("deferred");
    expect(classifyGuestHandoffFailure(new SupersededAuthSessionError())).toBe("deferred");
  });

  it("reports vault_full only for the 422 vault marker", () => {
    expect(
      classifyGuestHandoffFailure(apiError(422, "VALIDATION_ERROR", { reason: "vault_full" })),
    ).toBe("vault_full");
  });

  it("keeps lookalike details inside their own status", () => {
    expect(
      classifyGuestHandoffFailure(apiError(422, "VALIDATION_ERROR", { reason: "asset_mismatch" })),
    ).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(422, "VALIDATION_ERROR", "vault_full"))).toBe(
      "permanent",
    );
    expect(
      classifyGuestHandoffFailure(apiError(413, "PAYLOAD_TOO_LARGE", { reason: "vault_full" })),
    ).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(422, "VALIDATION_ERROR", null))).toBe("permanent");
  });

  it("classifies by status even when the code text suggests another kind", () => {
    expect(classifyGuestHandoffFailure(apiError(422, "TRANSIENT_TRY_AGAIN"))).toBe("permanent");
    expect(classifyGuestHandoffFailure(apiError(503, "VALIDATION_ERROR"))).toBe("transient");
  });
});
