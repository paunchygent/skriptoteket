/**
 * Rules workspace pane tests.
 *
 * These tests lock the dedicated `Regler` workspace behavior so the map view
 * and top summary panel stay authoritative for smart-rule authoring after the
 * cut-over.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";
import type { RelationshipRule, RoomTemplate, Student } from "../classroomPlannerTypes";

type PlannerStateMock = {
  roster: { id: string; name: string; students: Student[] } | null;
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
  editingNearTeacherRule: boolean;
  canCommitPendingRelationshipRule: boolean;
  smartRuleFeedbackMessage: string | null;
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
  beginRelationshipRuleEdit: ReturnType<typeof vi.fn>;
  beginNearTeacherEdit: ReturnType<typeof vi.fn>;
  clearNearTeacherRule: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  replaceNearTeacherPreference: ReturnType<typeof vi.fn>;
  handleSeatingSmartToolStudentSelection: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    roster: {
      id: "roster-1",
      name: "SR24D",
      students: [
        { id: "student-1", display_name: "Ada Lovelace" },
        { id: "student-2", display_name: "Alan Turing" },
        { id: "student-3", display_name: "Grace Hopper" },
      ],
    },
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
    seatingPreferences: [
      { student_id: "student-1", near_teacher: true },
      { student_id: "student-2", near_teacher: true },
    ],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ],
    pendingRelationshipStudentIds: ["student-2", "student-3"],
    activeSeatingSmartTool: "keep_apart",
    canEditSeatingSmartRules: true,
    editingRelationshipRuleId: null,
    editingNearTeacherRule: false,
    canCommitPendingRelationshipRule: true,
    smartRuleFeedbackMessage: null,
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    retrySmartRuleHydration: vi.fn(),
    beginRelationshipRuleEdit: vi.fn(),
    beginNearTeacherEdit: vi.fn(),
    clearNearTeacherRule: vi.fn(() => true),
    deleteRelationshipRule: vi.fn(),
    commitPendingRelationshipRule: vi.fn(() => true),
    replaceNearTeacherPreference: vi.fn(),
    handleSeatingSmartToolStudentSelection: vi.fn(() => true),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane", () => {
  beforeEach(() => {
    stateMocks.plannerState.roster = {
      id: "roster-1",
      name: "SR24D",
      students: [
        { id: "student-1", display_name: "Ada Lovelace" },
        { id: "student-2", display_name: "Alan Turing" },
        { id: "student-3", display_name: "Grace Hopper" },
      ],
    };
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.seatingPreferences = [
      { student_id: "student-1", near_teacher: true },
      { student_id: "student-2", near_teacher: true },
    ];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ];
    stateMocks.plannerState.pendingRelationshipStudentIds = ["student-2", "student-3"];
    stateMocks.plannerState.activeSeatingSmartTool = "keep_apart";
    stateMocks.plannerState.canEditSeatingSmartRules = true;
    stateMocks.plannerState.editingRelationshipRuleId = null;
    stateMocks.plannerState.editingNearTeacherRule = false;
    stateMocks.plannerState.canCommitPendingRelationshipRule = true;
    stateMocks.plannerState.smartRuleFeedbackMessage = null;
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
    stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
    stateMocks.plannerState.beginRelationshipRuleEdit.mockReset();
    stateMocks.plannerState.beginNearTeacherEdit.mockReset();
    stateMocks.plannerState.clearNearTeacherRule.mockReset();
    stateMocks.plannerState.clearNearTeacherRule.mockReturnValue(true);
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
    stateMocks.plannerState.replaceNearTeacherPreference.mockReset();
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReset();
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReturnValue(true);
  });

  it("defaults to Planeringskarta and lets teachers switch to Sittschema without clearing the active rule selection", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            props: ["mapView"],
            emits: ["update:mapView"],
            template: `
              <div>
                <button
                  type="button"
                  data-test="rules-map-view-planning"
                  aria-checked="true"
                >
                  Planeringskarta
                </button>
                <button
                  type="button"
                  data-test="rules-map-view-seating"
                  @click="$emit('update:mapView', 'seating_arrangement')"
                >
                  Sittschema
                </button>
                <div data-test='rules-map-canvas-stub'>{{ mapView }}</div>
              </div>
            `,
          },
        },
      },
    });

    const planningButton = wrapper.get('[data-test="rules-map-view-planning"]');
    const seatingButton = wrapper.get('[data-test="rules-map-view-seating"]');

    expect(wrapper.find('[data-test="rules-summary-panel"]').exists()).toBe(true);
    expect(planningButton.attributes("aria-checked")).toBe("true");
    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("planning_map");
    expect(wrapper.text()).toContain("2 valda");
    expect(wrapper.text()).toContain("Nära läraren");
    expect(wrapper.text()).not.toContain("Närmare läraren");
    expect(wrapper.text()).not.toContain("totalt");
    expect(
      wrapper.find('[data-test="rules-tool-rail"] [data-test="rules-pending-panel"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-test="rules-summary-panel"] [data-test="rules-commit-rule"]').exists(),
    ).toBe(false);

    await seatingButton.trigger("click");

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

  it("activates the near-teacher tool from the summary panel instead of opening a dropdown edit flow", async () => {
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

    expect(stateMocks.plannerState.beginNearTeacherEdit).toHaveBeenCalledWith();
  });

  it("removes the consolidated near-teacher rule directly from the inspector", async () => {
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

    expect(stateMocks.plannerState.clearNearTeacherRule).toHaveBeenCalledWith();
  });

  it("keeps the tool rail on a bounded sticky lane beside the map and reserves the summary panel height before rules exist", () => {
    stateMocks.plannerState.seatingPreferences = [];
    stateMocks.plannerState.relationshipRules = [];
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.activeSeatingSmartTool = null;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="rules-workspace-layout"]').classes()).toContain("planner-rules-layout-row");
    expect(wrapper.get('[data-test="rules-tool-rail"]').classes()).toEqual(
      expect.arrayContaining(["planner-rules-tool-lane", "flex", "flex-col"]),
    );
    expect(wrapper.get('[data-test="rules-summary-empty-state"]').classes()).toContain("min-h-full");
  });

  it("renders the phone rules workspace with a default-open student list and sticky drop target", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="phone-rules-workspace"]').text()).toContain(
      "Reglerna gäller hela klassen.",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_apart"]').classes()).toContain(
      "planner-phone-rule-row-active",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-near_teacher"]').html()).toContain(
      "lucide-graduation-cap",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-near_teacher"]').html()).not.toContain(
      "lucide-school",
    );
    expect(wrapper.get('[data-test="phone-rules-selection"]').classes()).toContain(
      "planner-phone-rules-selection",
    );
    expect(wrapper.get('[data-test="phone-rules-selected-student"]').text()).toContain(
      "Alan Turing",
    );
    expect(wrapper.get('[data-test="phone-rules-student-list"]').text()).toContain("Ada Lovelace");

    await wrapper.get('[data-test="phone-rules-tool-keep_near"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-student-pool"]').trigger("drop", {
      dataTransfer: { getData: () => "student-1", dropEffect: "move" },
    });
    await wrapper.get('[data-test="phone-rules-selection"]').trigger("drop", {
      dataTransfer: { getData: () => "student-1", dropEffect: "move" },
    });
    await wrapper.get('[data-test="phone-rules-clear-selection"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-commit-rule"]').trigger("click");

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("keep_near");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).toHaveBeenCalledWith("student-1");
    expect(stateMocks.plannerState.clearPendingRelationshipSelection).toHaveBeenCalledWith();
    expect(stateMocks.plannerState.commitPendingRelationshipRule).toHaveBeenCalledWith();
  });

  it("starts the phone rules workspace with a usable near-teacher selection target", () => {
    stateMocks.plannerState.activeSeatingSmartTool = null;
    stateMocks.plannerState.pendingRelationshipStudentIds = [];

    mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(stateMocks.plannerState.beginNearTeacherEdit).toHaveBeenCalledWith();
  });
});
