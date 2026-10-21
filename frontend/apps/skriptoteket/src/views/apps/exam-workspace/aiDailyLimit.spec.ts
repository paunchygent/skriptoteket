import { beforeEach, describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import {
  AI_DAILY_LIMIT_NOTE,
  aiDailyLimitReached,
  hasAiDailyLimit,
  isAiDailyLimitError,
  markAiDailyLimit,
  resetAiDailyLimitForTests,
} from "./aiDailyLimit";

describe("aiDailyLimit", () => {
  beforeEach(() => {
    resetAiDailyLimitForTests();
  });

  it("keeps the exact Swedish limit note", () => {
    expect(AI_DAILY_LIMIT_NOTE).toBe(
      "Du har nått dagens gräns för AI-hjälp. Försök igen i morgon.",
    );
  });

  it.each(["pool", "user_share", "usd_ceiling"] as const)("detects ai_limit %s", (ai_limit) => {
    expect(hasAiDailyLimit({ ai_limit })).toBe(true);
  });

  it("ignores a status without ai_limit", () => {
    expect(hasAiDailyLimit({ ai_limit: null })).toBe(false);
    expect(hasAiDailyLimit({})).toBe(false);
    expect(hasAiDailyLimit(null)).toBe(false);
    expect(hasAiDailyLimit(undefined)).toBe(false);
  });

  it("detects the retry limit error", () => {
    const error = new ApiError({
      code: "AI_DAILY_LIMIT_REACHED",
      message: AI_DAILY_LIMIT_NOTE,
      status: 429,
      details: { limit: "pool" },
    });
    expect(isAiDailyLimitError(error)).toBe(true);
  });

  it("ignores other errors", () => {
    expect(
      isAiDailyLimitError(new ApiError({ code: "CONFLICT", message: "x", status: 409 })),
    ).toBe(false);
    expect(isAiDailyLimitError(new Error("network down"))).toBe(false);
  });

  it("stays unset until marked for the page session", () => {
    expect(aiDailyLimitReached.value).toBe(false);
    markAiDailyLimit();
    expect(aiDailyLimitReached.value).toBe(true);
  });
});
