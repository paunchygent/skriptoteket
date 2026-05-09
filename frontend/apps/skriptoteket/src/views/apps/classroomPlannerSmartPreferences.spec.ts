/**
 * Classroom planner Smart preference tests.
 *
 * Purpose:
 *   Locks authenticated draft fallback behavior and public guest preference
 *   memory for Smart, history, and seating-influenced grouping.
 *
 * Relationships:
 *   - covers `classroomPlannerSmartPreferences.ts`
 *   - supports Smart settings drawer and draft persistence behavior
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  isGroupingSeatingDistanceEnabledByDefault,
  isHistoryEnabledByDefault,
  isSmartEnabledByDefault,
  rememberGuestSmartPreference,
  resolveGuestDraftSmartPreferences,
} from "./classroomPlannerSmartPreferences";

describe("classroomPlannerSmartPreferences", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults authenticated Smart and history on while keeping grouping seating influence off", () => {
    expect(isSmartEnabledByDefault({})).toBe(true);
    expect(isHistoryEnabledByDefault({})).toBe(true);
    expect(isGroupingSeatingDistanceEnabledByDefault({})).toBe(false);
  });

  it("preserves explicit teacher draft flags", () => {
    expect(isSmartEnabledByDefault({ smart_enabled: false })).toBe(false);
    expect(isHistoryEnabledByDefault({ use_history: false })).toBe(false);
    expect(isGroupingSeatingDistanceEnabledByDefault({
      grouping_seating_distance_enabled: true,
    })).toBe(true);
  });

  it("remembers public guest preferences in browser storage for future drafts", () => {
    expect(resolveGuestDraftSmartPreferences()).toEqual({
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: false,
    });

    rememberGuestSmartPreference("grouping_seating_distance_enabled", true);

    expect(resolveGuestDraftSmartPreferences()).toEqual({
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: true,
    });
  });
});
