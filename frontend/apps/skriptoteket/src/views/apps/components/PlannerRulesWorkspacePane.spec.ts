/**
 * Rules workspace pane tests.
 *
 * These tests lock the dedicated `Regler` workspace behavior so the map view
 * and inspector stay authoritative for smart-rule authoring after the cut-over.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";
import type { RelationshipRule, RoomTemplate, Student } from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  students: Student[];
  studentsById: Record<string, Student | undefined>;
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  pendingRelationshipStudentIds: string[];
  activeSeatingSmartTool: "near_teacher" | "keep_near" | "keep_apart" | null;
  canEditSeatingSmartRules: boolean;
  editingRelationshipRuleId: string | null;
  canCommitPendingRelationshipRule: boolean;
  smartRuleFeedbackMessage: string | null;
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
  beginRelationshipRuleEdit: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  setStudentNearTeacherEnabled: ReturnType<typeof vi.fn>;
  replaceNearTeacherPreference: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: null },
        { id: "seat-2", x: 120, y: 0, zone: null },
      ],
      fixtures: [],
    },
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
      { id: "student-3", display_name: "Grace Hopper" },
    ],
    studentsById: {
      "student-1": { id: "student-1", display_name: "Ada Lovelace" },
      "student-2": { id: "student-2", display_name: "Alan Turing" },
      "student-3": { id: "student-3", display_name: "Grace Hopper" },
    },
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ],
    pendingRelationshipStudentIds: ["student-2", "student-3"],
    activeSeatingSmartTool: "keep_apart",
    canEditSeatingSmartRules: true,
    editingRelationshipRuleId: null,
    canCommitPendingRelationshipRule: true,
    smartRuleFeedbackMessage: null,
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    retrySmartRuleHydration: vi.fn(),
    beginRelationshipRuleEdit: vi.fn(),
    deleteRelationshipRule: vi.fn(),
    commitPendingRelationshipRule: vi.fn(() => true),
    setStudentNearTeacherEnabled: vi.fn(),
    replaceNearTeacherPreference: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane", () => {
  beforeEach(() => {
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ];
    stateMocks.plannerState.pendingRelationshipStudentIds = ["student-2", "student-3"];
    stateMocks.plannerState.activeSeatingSmartTool = "keep_apart";
    stateMocks.plannerState.canEditSeatingSmartRules = true;
    stateMocks.plannerState.editingRelationshipRuleId = null;
    stateMocks.plannerState.canCommitPendingRelationshipRule = true;
    stateMocks.plannerState.smartRuleFeedbackMessage = null;
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
    stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
    stateMocks.plannerState.beginRelationshipRuleEdit.mockReset();
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
    stateMocks.plannerState.setStudentNearTeacherEnabled.mockReset();
    stateMocks.plannerState.replaceNearTeacherPreference.mockReset();
  });

  it("defaults to Planeringskarta and lets teachers switch to Sittschema without clearing the active rule selection", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            props: ["mapView"],
            template: "<div data-test='rules-map-canvas-stub'>{{ mapView }}</div>",
          },
        },
      },
    });

    const mapToggleButtons = wrapper.get("[data-ui='segmented-toggle']").findAll("button");
    const planningButton = mapToggleButtons.find((button) => button.text() === "Planeringskarta");
    const seatingButton = mapToggleButtons.find((button) => button.text() === "Sittschema");

    expect(planningButton?.attributes("aria-pressed")).toBe("true");
    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("planning_map");
    expect(wrapper.text()).toContain("2 valda");

    await seatingButton?.trigger("click");

    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("seating_arrangement");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.clearPendingRelationshipSelection).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("2 valda");
  });

  it("edits existing relationship rules from the inspector", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-edit-rule-0"]').trigger("click");

    expect(stateMocks.plannerState.beginRelationshipRuleEdit).toHaveBeenCalledWith("rule-1");
  });

  it("edits near-teacher rules directly from the inspector", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-edit-near-teacher-0"]').trigger("click");
    await wrapper.get('[data-test="rules-near-teacher-select-0"]').setValue("student-2");
    await wrapper.get('[data-test="rules-save-near-teacher-0"]').trigger("click");

    expect(stateMocks.plannerState.replaceNearTeacherPreference).toHaveBeenCalledWith(
      "student-1",
      "student-2",
    );
  });

  it("removes near-teacher rules directly from the inspector", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-delete-near-teacher-0"]').trigger("click");

    expect(stateMocks.plannerState.setStudentNearTeacherEnabled).toHaveBeenCalledWith(
      "student-1",
      false,
    );
  });
});
