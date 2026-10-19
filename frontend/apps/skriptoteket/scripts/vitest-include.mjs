/**
 * @fileoverview Owns the VITEST_INCLUDE transport between the SPA Vitest
 * wrapper and `vitest.config.ts` so glob braces survive intact as JSON.
 */

export const VITEST_INCLUDE_ENV = "VITEST_INCLUDE";

/** Encodes a non-empty include list for the VITEST_INCLUDE environment. */
export function encodeVitestInclude(include) {
  if (include.length === 0) {
    throw new Error(`${VITEST_INCLUDE_ENV} must be a non-empty JSON array of strings`);
  }
  return JSON.stringify(include);
}

/** Decodes the VITEST_INCLUDE environment value with runtime validation. */
export function decodeVitestInclude(value) {
  if (value === undefined) {
    return null;
  }
  const parsed = JSON.parse(value);
  if (
    !Array.isArray(parsed) ||
    parsed.length === 0 ||
    !parsed.every((entry) => typeof entry === "string")
  ) {
    throw new Error(`${VITEST_INCLUDE_ENV} must be a non-empty JSON array of strings`);
  }
  return parsed;
}
