/**
 * Conversion Hub authenticated mode route contract.
 *
 * Domain purpose:
 *   Define the closed query-mode bridge that lets the authenticated
 *   Conversion Hub compatibility host open either Exam Converter or transcript
 *   intake without changing app ids or route records.
 *
 * Relationships:
 *   - Consumed by `ExamConverterAuthenticatedView` for route-query state.
 *   - Shared with `ConversionHubModeTabs` so tab values and route values stay
 *     one closed contract.
 */

import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from "vue-router";

export const CONVERSION_HUB_DEFAULT_MODE = "exam";
export const CONVERSION_HUB_MODE_VALUES = ["exam", "transcript"] as const;

export type ConversionHubMode = (typeof CONVERSION_HUB_MODE_VALUES)[number];

type ConversionHubModeQueryValue =
  | LocationQueryValue
  | LocationQueryValue[]
  | undefined;

export function isConversionHubMode(value: unknown): value is ConversionHubMode {
  return value === "exam" || value === "transcript";
}

export function resolveConversionHubModeQueryValue(
  value: ConversionHubModeQueryValue,
): ConversionHubMode {
  if (isConversionHubMode(value)) {
    return value;
  }
  return CONVERSION_HUB_DEFAULT_MODE;
}

export function withConversionHubModeQuery(
  currentQuery: LocationQuery,
  mode: ConversionHubMode,
): LocationQueryRaw {
  return {
    ...currentQuery,
    mode,
  };
}
