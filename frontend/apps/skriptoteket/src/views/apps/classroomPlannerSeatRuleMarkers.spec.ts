/**
 * Seat-rule marker diagnostic freshness tests.
 *
 * Purpose:
 *   Prove map markers only color soft-rule symbols from diagnostics that still
 *   match the current visible smart-rule shape and assignment state.
 *
 * Relationships:
 *   - Exercises `classroomPlannerSeatRuleMarkers.ts` without mounting a map.
 *   - Complements component tests that prove marker placement and symbols.
 */

import { describe, expect, it } from "vitest";

import { buildSeatRuleMarkersBySeatId } from "./classroomPlannerSeatRuleMarkers";
import type {
  RelationshipRule,
  RoomTemplate,
  SeatAssignment,
  SmartRuleDiagnostic,
  Student,
} from "./classroomPlannerTypes";

const template: RoomTemplate = {
  id: "template-1",
  name: "Sal 101",
  grid_cols: 3,
  grid_rows: 1,
  seats: [
    { id: "seat-a", x: 0, y: 0 },
    { id: "seat-b", x: 96, y: 0 },
    { id: "seat-c", x: 192, y: 0 },
  ],
  fixtures: [],
};

const studentsById: Record<string, Student> = {
  a: { id: "a", display_name: "Ada" },
  b: { id: "b", display_name: "Bo" },
  c: { id: "c", display_name: "Cia" },
};

const seatAssignments: SeatAssignment[] = [
  { student_id: "a", seat_id: "seat-a" },
  { student_id: "b", seat_id: "seat-b" },
  { student_id: "c", seat_id: "seat-c" },
];

function relationshipDiagnostic(
  overrides: Partial<SmartRuleDiagnostic> = {},
): SmartRuleDiagnostic {
  return {
    rule_id: "rule-1",
    rule_kind: "keep_near",
    status: "failed",
    student_ids: ["a", "b"],
    seat_ids: ["seat-a", "seat-b"],
    reason_code: "keep_near_row_not_close",
    freshness_key: "fresh-1",
    ...overrides,
  };
}

function markerToneForRule(
  relationshipRules: RelationshipRule[],
  ruleDiagnostics: SmartRuleDiagnostic[],
) {
  return buildSeatRuleMarkersBySeatId({
    template,
    studentsById,
    seatAssignments,
    relationshipRules,
    ruleDiagnostics,
  })["seat-a"]?.[0]?.tone;
}

describe("buildSeatRuleMarkersBySeatId diagnostic freshness", () => {
  it("ignores relationship diagnostics when the rule id is reused for a new kind", () => {
    expect(
      markerToneForRule(
        [{ id: "rule-1", kind: "keep_apart", student_ids: ["a", "b"] }],
        [relationshipDiagnostic()],
      ),
    ).toBe("neutral");
  });

  it("ignores relationship diagnostics when the current rule has different students", () => {
    expect(
      markerToneForRule(
        [{ id: "rule-1", kind: "keep_near", student_ids: ["a", "c"] }],
        [relationshipDiagnostic()],
      ),
    ).toBe("neutral");
  });

  it("ignores near-teacher diagnostics without the current stable preference key", () => {
    const markers = buildSeatRuleMarkersBySeatId({
      template,
      studentsById,
      seatAssignments,
      seatingPreferences: [{ student_id: "a", near_teacher: true }],
      ruleDiagnostics: [
        {
          rule_id: "near_teacher:old-a",
          rule_kind: "near_teacher",
          status: "satisfied",
          student_ids: ["a"],
          seat_ids: ["seat-a"],
          reason_code: "near_teacher_row_first_rank",
          freshness_key: "fresh-1",
        },
      ],
    });

    expect(markers["seat-a"]?.[0]?.tone).toBe("neutral");
  });

  it("ignores soft-rule diagnostics when the freshness key is missing", () => {
    expect(
      markerToneForRule(
        [{ id: "rule-1", kind: "keep_near", student_ids: ["a", "b"] }],
        [relationshipDiagnostic({ freshness_key: null })],
      ),
    ).toBe("neutral");
  });

  it("colors soft-rule diagnostics when rule shape, assignment, and freshness match", () => {
    expect(
      markerToneForRule(
        [{ id: "rule-1", kind: "keep_near", student_ids: ["a", "b"] }],
        [relationshipDiagnostic({ status: "satisfied" })],
      ),
    ).toBe("success");
  });
});
