// @vitest-environment node
/**
 * @fileoverview Locks down the VITEST_INCLUDE transport: the wrapper and the
 * Vitest config share one JSON encoder and validating decoder.
 */

import { describe, expect, it } from "vitest";

import {
  decodeVitestInclude,
  encodeVitestInclude,
  VITEST_INCLUDE_ENV,
} from "../../scripts/vitest-include.mjs";

describe("decodeVitestInclude", () => {
  it("returns null when the environment value is missing", () => {
    expect(decodeVitestInclude(undefined)).toBeNull();
  });

  it("round-trips include patterns with braces and commas intact", () => {
    const include = ["src/{a,b}/**/*.spec.ts", "src/x.spec.ts"];
    expect(decodeVitestInclude(encodeVitestInclude(include))).toEqual(include);
  });

  it.each([[""], ["not json"], ["src/a,src/b"]])("rejects non-JSON %j", (value) => {
    expect(() => decodeVitestInclude(value)).toThrow();
  });

  it.each([[`[]`], [`{}`], [`"src"`], [`[1]`], [`["a", null]`]])(
    "throws for %j",
    (value) => {
      expect(() => decodeVitestInclude(value)).toThrow(
        `${VITEST_INCLUDE_ENV} must be a non-empty JSON array of strings`,
      );
    },
  );
});

describe("encodeVitestInclude", () => {
  it("throws for an empty include list", () => {
    expect(() => encodeVitestInclude([])).toThrow(
      `${VITEST_INCLUDE_ENV} must be a non-empty JSON array of strings`,
    );
  });
});
