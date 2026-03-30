/**
 * Grouping workspace smart-rule visibility tests.
 *
 * These tests keep smart-rule markers visible on student bars both before and
 * after assignment so grouping can expose whether the current grouping still
 * respects the authored rules at a glance.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerGroupingWorkspacePane from "./PlannerGroupingWorkspacePane.vue";
import type { DraftGroup, RelationshipRule, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  ungroupedStudents: Roster["students"];
  groups: DraftGroup[];
  studentsByGroupId: Record<string, Roster["students"]>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  isWorkspaceBusy: boolean;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
  removeStudentFromGroup: ReturnType<typeof vi.fn>;
  assignStudentToGroup: ReturnType<typeof vi.fn>;
  renameGroup: ReturnType<typeof vi.fn>;
  moveGroup: ReturnType<typeof vi.fn>;
  removeGroup: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    ungroupedStudents: [{ id: "student-2", display_name: "Alan Turing" }],
    groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
    studentsByGroupId: {
      "group-1": [{ id: "student-1", display_name: "Ada Lovelace" }],
    },
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ],
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    isWorkspaceBusy: false,
    retrySmartRuleHydration: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    assignStudentToGroup: vi.fn(),
    renameGroup: vi.fn(),
    moveGroup: vi.fn(),
    removeGroup: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerGroupingWorkspacePane smart-rule visibility", () => {
  beforeEach(() => {
    stateMocks.plannerState.ungroupedStudents = [{ id: "student-2", display_name: "Alan Turing" }];
    stateMocks.plannerState.groups = [
      { id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false },
    ];
    stateMocks.plannerState.studentsByGroupId = {
      "group-1": [{ id: "student-1", display_name: "Ada Lovelace" }],
    };
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ];
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
    stateMocks.plannerState.removeStudentFromGroup.mockReset();
    stateMocks.plannerState.assignStudentToGroup.mockReset();
    stateMocks.plannerState.renameGroup.mockReset();
    stateMocks.plannerState.moveGroup.mockReset();
    stateMocks.plannerState.removeGroup.mockReset();
  });

  it("keeps rule markers visible in the ungrouped pool and inside assigned group cards", () => {
    const wrapper = mount(PlannerGroupingWorkspacePane);

    expect(wrapper.get('[data-test="student-pool-markers-student-2"]').text()).toContain("Isär A");
    expect(wrapper.get('[data-test="group-student-markers-student-1"]').text()).toContain(
      "Nära läraren",
    );
    expect(wrapper.get('[data-test="group-student-markers-student-1"]').text()).toContain(
      "Isär A",
    );
  });
});
