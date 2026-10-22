import { beforeEach, describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import {
  AI_APP_LIMIT_NOTE,
  AI_USER_LIMIT_NOTE,
  aiDailyLimit,
  aiDailyLimitNote,
  aiDailyLimitReached,
  aiLimitFromError,
  aiLimitFromStatus,
  aiLimitNote,
  hasAiDailyLimit,
  isAiDailyLimitError,
  markAiDailyLimit,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";
import type { AiDailyLimit } from "./aiDailyLimit";

const allLimits: AiDailyLimit[] = ["pool", "user_share", "usd_ceiling"];

describe("aiDailyLimit", () => {
  beforeEach(() => {
    resetAiDailyLimitForTests();
  });

  it("shows the user-share note for the user's own limit", () => {
    expect(AI_USER_LIMIT_NOTE).toBe(
      "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.",
    );
    expect(aiLimitNote("user_share")).toBe(AI_USER_LIMIT_NOTE);
  });

  it("shows the app note for the pool and ceiling limits", () => {
    expect(AI_APP_LIMIT_NOTE).toBe(
      "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon.",
    );
    expect(aiLimitNote("pool")).toBe(AI_APP_LIMIT_NOTE);
    expect(aiLimitNote("usd_ceiling")).toBe(AI_APP_LIMIT_NOTE);
  });

  it.each(allLimits)("detects ai_limit %s", (ai_limit) => {
    expect(hasAiDailyLimit({ ai_limit })).toBe(true);
    expect(aiLimitFromStatus({ ai_limit })).toBe(ai_limit);
  });

  it("ignores a status without ai_limit", () => {
    expect(hasAiDailyLimit({ ai_limit: null })).toBe(false);
    expect(hasAiDailyLimit({})).toBe(false);
    expect(hasAiDailyLimit(null)).toBe(false);
    expect(hasAiDailyLimit(undefined)).toBe(false);
    expect(aiLimitFromStatus({ ai_limit: null })).toBeNull();
    expect(aiLimitFromStatus({})).toBeNull();
    expect(aiLimitFromStatus(null)).toBeNull();
  });

  it("detects the retry limit error", () => {
    const error = new ApiError({
      code: "AI_DAILY_LIMIT_REACHED",
      message: "refused",
      status: 429,
      details: { limit: "pool" },
    });
    expect(isAiDailyLimitError(error)).toBe(true);
    expect(aiLimitFromError(error)).toBe("pool");
  });

  it("reads the user_share limit from the retry error details", () => {
    const error = new ApiError({
      code: "AI_DAILY_LIMIT_REACHED",
      message: "refused",
      status: 429,
      details: { limit: "user_share" },
    });
    expect(aiLimitFromError(error)).toBe("user_share");
  });

  it("ignores other errors", () => {
    expect(
      isAiDailyLimitError(new ApiError({ code: "CONFLICT", message: "x", status: 409 })),
    ).toBe(false);
    expect(isAiDailyLimitError(new Error("network down"))).toBe(false);
    expect(aiLimitFromError(new Error("network down"))).toBeNull();
  });

  it("remembers the first limit for the page session", () => {
    expect(aiDailyLimitReached.value).toBe(false);
    expect(aiDailyLimit.value).toBeNull();
    expect(aiDailyLimitNote.value).toBeNull();
    markAiDailyLimit("user_share");
    expect(aiDailyLimit.value).toBe("user_share");
    expect(aiDailyLimitReached.value).toBe(true);
    expect(aiDailyLimitNote.value).toBe(AI_USER_LIMIT_NOTE);
    markAiDailyLimit("pool");
    expect(aiDailyLimit.value).toBe("user_share");
    expect(aiDailyLimitNote.value).toBe(AI_USER_LIMIT_NOTE);
  });

  it("reads no limit from a retry error that names none", () => {
    const error = new ApiError({
      code: "AI_DAILY_LIMIT_REACHED",
      message: "refused",
      status: 429,
      details: null,
    });
    expect(aiLimitFromError(error)).toBeNull();
  });
});
