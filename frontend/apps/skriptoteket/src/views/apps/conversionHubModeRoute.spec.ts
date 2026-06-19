/**
 * Conversion Hub authenticated mode route contract tests.
 *
 * Slice purpose:
 *   Prove the authenticated compatibility host accepts only the governed
 *   `mode=exam|transcript` query values and preserves route context when tabs
 *   write mode state.
 */

import { describe, expect, it } from "vitest";

import {
  CONVERSION_HUB_DEFAULT_MODE,
  resolveConversionHubModeQueryValue,
  withConversionHubModeQuery,
} from "./conversionHubModeRoute";

describe("conversionHubModeRoute", () => {
  it.each([
    ["exam", "exam"],
    ["transcript", "transcript"],
  ] as const)("accepts %s as a Conversion Hub mode", (value, expectedMode) => {
    expect(resolveConversionHubModeQueryValue(value)).toBe(expectedMode);
  });

  it.each<[string, string | null | string[] | undefined]>([
    ["absent", undefined],
    ["invalid", "audio"],
    ["empty", ""],
    ["null", null],
    ["repeated", ["exam", "transcript"]],
    ["array-valued transcript", ["transcript"]],
  ])("defaults %s mode query state to exam", (_, value) => {
    expect(resolveConversionHubModeQueryValue(value)).toBe(CONVERSION_HUB_DEFAULT_MODE);
  });

  it("writes explicit selected mode while preserving unrelated query keys", () => {
    expect(
      withConversionHubModeQuery(
        {
          debug: "1",
          mode: ["audio", "transcript"],
          preview: null,
          source: ["dashboard", "favorites"],
        },
        "transcript",
      ),
    ).toEqual({
      debug: "1",
      mode: "transcript",
      preview: null,
      source: ["dashboard", "favorites"],
    });
  });
});
