/**
 * Phone rules workspace active-summary integration tests.
 *
 * Purpose:
 *   Prove the reduced phone `Regler` workspace routes persisted-rule
 *   management through the same planner-state actions as the desktop inspector.
 *
 * Relationships:
 *   - covers `PlannerRulesWorkspacePane.vue`
 *   - complements `PlannerPhoneRulesSummary.vue` unit tests
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";
import type { FixedSeatRule, RelationshipRule, RoomTemplate, Student } from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  students: Student[];
  studentsById: Record<string, Student | undefined>;
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  fixedSeatRules: FixedSeatRule[];
  smartRuleDiagnostics: [];
  pendingRelationshipStudentIds: string[];
  pendingFixedSeatStudentId: string | null;
  pendingFixedSeatSeatId: string | null;
  activeSeatingSmartTool: "near_teacher" | "keep_near" | "keep_apart" | "fixed_seat" | null;
  canEditSeatingSmartRules: boolean;
  editingFixedSeatRuleId: string | null;
  editingRelationshipRuleId: string | null;
  editingNearTeacherRule: boolean;
  canCommitPendingRelationshipRule: boolean;
  canCommitPendingFixedSeatRule: boolean;
  smartRuleHydrationStatus: "ready";
  smartRuleHydrationMessage: null;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  clearPendingRuleCandidates: ReturnType<typeof vi.fn>;
  removePendingRuleCandidate: ReturnType<typeof vi.fn>;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
  beginRelationshipRuleEdit: ReturnType<typeof vi.fn>;
  beginNearTeacherEdit: ReturnType<typeof vi.fn>;
  beginFixedSeatRuleEdit: ReturnType<typeof vi.fn>;
  clearNearTeacherRule: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  deleteFixedSeatRule: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  commitPendingFixedSeatRule: ReturnType<typeof vi.fn>;
  selectFixedSeatRuleSeat: ReturnType<typeof vi.fn>;
  handleSeatingSmartToolStudentSelection: ReturnType<typeof vi.fn>;
  isStudentInPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  isStudentInPendingRuleCandidates: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => {
  const students: Student[] = [
    { id: "student-1", display_name: "Ada Lovelace" },
    { id: "student-2", display_name: "Alan Turing" },
    { id: "student-3", display_name: "Grace Hopper" },
  ];
  return {
    plannerState: {
      template: {
        id: "template-1",
        name: "Sal 101",
        seats: [
          { id: "seat-1", x: 0, y: 0, zone: null },
          { id: "seat-2", x: 120, y: 0, zone: null },
        ],
        fixtures: [],
      },
      students,
      studentsById: Object.fromEntries(students.map((student) => [student.id, student])),
      seatAssignments: [],
      seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
      relationshipRules: [
        { id: "relationship-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
      ],
      fixedSeatRules: [
        {
          id: "fixed-active",
          template_id: "template-1",
          student_id: "student-2",
          seat_id: "seat-2",
        },
        {
          id: "fixed-inactive",
          template_id: "template-other",
          student_id: "student-3",
          seat_id: "seat-99",
        },
      ],
      smartRuleDiagnostics: [],
      pendingRelationshipStudentIds: ["student-2", "student-3"],
      pendingFixedSeatStudentId: null,
      pendingFixedSeatSeatId: null,
      activeSeatingSmartTool: "keep_apart",
      canEditSeatingSmartRules: true,
      editingFixedSeatRuleId: null,
      editingRelationshipRuleId: null,
      editingNearTeacherRule: false,
      canCommitPendingRelationshipRule: true,
      canCommitPendingFixedSeatRule: false,
      smartRuleHydrationStatus: "ready",
      smartRuleHydrationMessage: null,
      setActiveSeatingSmartTool: vi.fn(),
      clearPendingRelationshipSelection: vi.fn(),
      clearPendingRuleCandidates: vi.fn(),
      removePendingRuleCandidate: vi.fn(),
      retrySmartRuleHydration: vi.fn(),
      beginRelationshipRuleEdit: vi.fn(),
      beginNearTeacherEdit: vi.fn(),
      beginFixedSeatRuleEdit: vi.fn(),
      clearNearTeacherRule: vi.fn(),
      deleteRelationshipRule: vi.fn(),
      deleteFixedSeatRule: vi.fn(),
      commitPendingRelationshipRule: vi.fn(),
      commitPendingFixedSeatRule: vi.fn(),
      selectFixedSeatRuleSeat: vi.fn(),
      handleSeatingSmartToolStudentSelection: vi.fn(),
      isStudentInPendingRelationshipSelection: vi.fn(() => false),
      isStudentInPendingRuleCandidates: vi.fn(() => false),
    } satisfies PlannerStateMock,
  };
});

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane phone active-rule management", () => {
  beforeEach(() => {
    stateMocks.plannerState.beginRelationshipRuleEdit.mockReset();
    stateMocks.plannerState.beginNearTeacherEdit.mockReset();
    stateMocks.plannerState.beginFixedSeatRuleEdit.mockReset();
    stateMocks.plannerState.removePendingRuleCandidate.mockReset();
    stateMocks.plannerState.clearNearTeacherRule.mockReset();
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.deleteFixedSeatRule.mockReset();
    stateMocks.plannerState.isStudentInPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.isStudentInPendingRelationshipSelection.mockReturnValue(false);
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReset();
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReturnValue(false);
  });

  it("filters fixed-seat rules to the active template and routes phone row actions", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="phone-rules-active-count"]').text()).toBe("3");
    expect(wrapper.findAll('[data-test="phone-rules-active-row-fixed-seat"]')).toHaveLength(1);
    expect(wrapper.text()).toContain("Alan Turing");
    expect(wrapper.text()).not.toContain("plats-99");

    await wrapper.get('[data-test="phone-rules-edit-near-teacher"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-delete-near-teacher"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-edit-rule-0"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-delete-rule-0"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-edit-fixed-seat-fixed-active"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-delete-fixed-seat-fixed-active"]').trigger("click");

    expect(stateMocks.plannerState.beginNearTeacherEdit).toHaveBeenCalledWith();
    expect(stateMocks.plannerState.clearNearTeacherRule).toHaveBeenCalledWith();
    expect(stateMocks.plannerState.beginRelationshipRuleEdit).toHaveBeenCalledWith("relationship-1");
    expect(stateMocks.plannerState.deleteRelationshipRule).toHaveBeenCalledWith("relationship-1");
    expect(stateMocks.plannerState.beginFixedSeatRuleEdit).toHaveBeenCalledWith("fixed-active");
    expect(stateMocks.plannerState.deleteFixedSeatRule).toHaveBeenCalledWith("fixed-active");
  });
});
