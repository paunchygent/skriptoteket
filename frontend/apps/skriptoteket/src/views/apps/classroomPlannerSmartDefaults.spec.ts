/**
 * Classroom planner Smart default tests.
 *
 * Purpose:
 *   Locks authenticated draft defaults that make Smart and history opt-out
 *   controls while preserving explicit teacher choices.
 *
 * Relationships:
 *   - covers `classroomPlannerSmartDefaults.ts`
 *   - supports Smart settings drawer and draft persistence behavior
 */

import { describe, expect, it } from "vitest";

import {
  isGroupingSeatingDistanceEnabledByDefault,
  isHistoryEnabledByDefault,
  isSmartEnabledByDefault,
} from "./classroomPlannerSmartDefaults";

describe("classroomPlannerSmartDefaults", () => {
  it("defaults Smart, history, and grouping seating influence to enabled when draft flags are absent", () => {
    expect(isSmartEnabledByDefault({})).toBe(true);
    expect(isHistoryEnabledByDefault({})).toBe(true);
    expect(isGroupingSeatingDistanceEnabledByDefault({})).toBe(true);
  });

  it("preserves explicit teacher opt-out flags", () => {
    expect(isSmartEnabledByDefault({ smart_enabled: false })).toBe(false);
    expect(isHistoryEnabledByDefault({ use_history: false })).toBe(false);
    expect(isGroupingSeatingDistanceEnabledByDefault({
      grouping_seating_distance_enabled: false,
    })).toBe(false);
  });
});
