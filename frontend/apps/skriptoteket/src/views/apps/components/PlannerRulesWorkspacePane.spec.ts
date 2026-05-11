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
import type {
  FixedSeatRule,
  RelationshipRule,
  RoomTemplate,
  SeatingSmartTool,
  Student,
} from "../classroomPlannerTypes";

type PlannerStateMock = {
  roster: { id: string; name: string; students: Student[] } | null;
  template: RoomTemplate | null;
  students: Student[];
  studentsById: Record<string, Student | undefined>;
  seatsById: Record<string, { id: string; x: number; y: number; zone?: string | null } | undefined>;
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  fixedSeatRules: FixedSeatRule[];
  pendingRelationshipStudentIds: string[];
  pendingFixedSeatStudentId: string | null;
  pendingFixedSeatSeatId: string | null;
  activeSeatingSmartTool: SeatingSmartTool | null;
  canEditSeatingSmartRules: boolean;
  editingFixedSeatRuleId: string | null;
  editingRelationshipRuleId: string | null;
  editingNearTeacherRule: boolean;
  canCommitPendingRelationshipRule: boolean;
  smartRuleFeedbackMessage: string | null;
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  canCommitPendingFixedSeatRule: boolean;
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
  fixedSeatRuleForStudent: ReturnType<typeof vi.fn>;
  fixedSeatRuleForSeat: ReturnType<typeof vi.fn>;
  replaceNearTeacherPreference: ReturnType<typeof vi.fn>;
  handleSeatingSmartToolStudentSelection: ReturnType<typeof vi.fn>;
  isStudentInPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  isStudentInPendingRuleCandidates: ReturnType<typeof vi.fn>;
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
    seatsById: {
      "seat-1": { id: "seat-1", x: 0, y: 0, zone: null },
      "seat-2": { id: "seat-2", x: 120, y: 0, zone: null },
    },
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [
      { student_id: "student-1", near_teacher: true },
      { student_id: "student-2", near_teacher: true },
    ],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ],
    fixedSeatRules: [],
    pendingRelationshipStudentIds: ["student-2", "student-3"],
    pendingFixedSeatStudentId: null,
    pendingFixedSeatSeatId: null,
    activeSeatingSmartTool: "keep_apart",
    canEditSeatingSmartRules: true,
    editingFixedSeatRuleId: null,
    editingRelationshipRuleId: null,
    editingNearTeacherRule: false,
    canCommitPendingRelationshipRule: true,
    smartRuleFeedbackMessage: null,
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    canCommitPendingFixedSeatRule: false,
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    clearPendingRuleCandidates: vi.fn(),
    removePendingRuleCandidate: vi.fn(),
    retrySmartRuleHydration: vi.fn(),
    beginRelationshipRuleEdit: vi.fn(),
    beginNearTeacherEdit: vi.fn(),
    beginFixedSeatRuleEdit: vi.fn(),
    clearNearTeacherRule: vi.fn(() => true),
    deleteRelationshipRule: vi.fn(),
    deleteFixedSeatRule: vi.fn(),
    commitPendingRelationshipRule: vi.fn(() => true),
    commitPendingFixedSeatRule: vi.fn(() => true),
    selectFixedSeatRuleSeat: vi.fn(() => true),
    fixedSeatRuleForStudent: vi.fn(() => null),
    fixedSeatRuleForSeat: vi.fn(() => null),
    replaceNearTeacherPreference: vi.fn(),
    handleSeatingSmartToolStudentSelection: vi.fn(() => true),
    isStudentInPendingRelationshipSelection: vi.fn(() => false),
    isStudentInPendingRuleCandidates: vi.fn(() => false),
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
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: null },
        { id: "seat-2", x: 120, y: 0, zone: null },
      ],
      fixtures: [],
    };
    stateMocks.plannerState.seatsById = {
      "seat-1": { id: "seat-1", x: 0, y: 0, zone: null },
      "seat-2": { id: "seat-2", x: 120, y: 0, zone: null },
    };
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.seatingPreferences = [
      { student_id: "student-1", near_teacher: true },
      { student_id: "student-2", near_teacher: true },
    ];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
    ];
    stateMocks.plannerState.fixedSeatRules = [];
    stateMocks.plannerState.pendingRelationshipStudentIds = ["student-2", "student-3"];
    stateMocks.plannerState.pendingFixedSeatStudentId = null;
    stateMocks.plannerState.pendingFixedSeatSeatId = null;
    stateMocks.plannerState.activeSeatingSmartTool = "keep_apart";
    stateMocks.plannerState.canEditSeatingSmartRules = true;
    stateMocks.plannerState.editingFixedSeatRuleId = null;
    stateMocks.plannerState.editingRelationshipRuleId = null;
    stateMocks.plannerState.editingNearTeacherRule = false;
    stateMocks.plannerState.canCommitPendingRelationshipRule = true;
    stateMocks.plannerState.smartRuleFeedbackMessage = null;
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.canCommitPendingFixedSeatRule = false;
    stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
    stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.clearPendingRuleCandidates.mockReset();
    stateMocks.plannerState.removePendingRuleCandidate.mockReset();
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
    stateMocks.plannerState.beginRelationshipRuleEdit.mockReset();
    stateMocks.plannerState.beginNearTeacherEdit.mockReset();
    stateMocks.plannerState.beginFixedSeatRuleEdit.mockReset();
    stateMocks.plannerState.clearNearTeacherRule.mockReset();
    stateMocks.plannerState.clearNearTeacherRule.mockReturnValue(true);
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.deleteFixedSeatRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
    stateMocks.plannerState.commitPendingFixedSeatRule.mockReset();
    stateMocks.plannerState.commitPendingFixedSeatRule.mockReturnValue(true);
    stateMocks.plannerState.selectFixedSeatRuleSeat.mockReset();
    stateMocks.plannerState.selectFixedSeatRuleSeat.mockReturnValue(true);
    stateMocks.plannerState.fixedSeatRuleForStudent.mockReset();
    stateMocks.plannerState.fixedSeatRuleForStudent.mockReturnValue(null);
    stateMocks.plannerState.fixedSeatRuleForSeat.mockReset();
    stateMocks.plannerState.fixedSeatRuleForSeat.mockReturnValue(null);
    stateMocks.plannerState.replaceNearTeacherPreference.mockReset();
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReset();
    stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReturnValue(true);
    stateMocks.plannerState.isStudentInPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.isStudentInPendingRelationshipSelection.mockReturnValue(false);
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReset();
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReturnValue(false);
  });

  it("defaults to Klassrumsvy when a classroom exists and preserves explicit switches", async () => {
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
                  @click="$emit('update:mapView', 'planning_map')"
                >
                  Planeringskarta
                </button>
                <button
                  type="button"
                  data-test="rules-map-view-seating"
                >
                  Klassrumsvy
                </button>
                <div data-test='rules-map-canvas-stub'>{{ mapView }}</div>
              </div>
            `,
          },
        },
      },
    });

    expect(wrapper.find('[data-test="rules-summary-panel"]').exists()).toBe(true);
    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("seating_arrangement");
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

    await wrapper.get('[data-test="rules-map-view-planning"]').trigger("click");

    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("planning_map");
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

  it("routes Fast plats from Planeringskarta through the classroom-view prompt", async () => {
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
                  @click="$emit('update:mapView', 'planning_map')"
                >
                  Planeringskarta
                </button>
                <div data-test='rules-map-canvas-stub'>{{ mapView }}</div>
              </div>
            `,
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-map-view-planning"]').trigger("click");
    await wrapper.get('[data-test="rules-tool-fixed_seat"]').trigger("click");

    expect(wrapper.get('[data-test="rules-fixed-seat-switch-prompt"]').text()).toContain("Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?");
    expect(wrapper.get('[data-test="rules-fixed-seat-switch-prompt"]').classes()).toContain("bg-canvas");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).not.toHaveBeenCalledWith("fixed_seat");

    await wrapper.get('[data-test="rules-fixed-seat-switch-no"]').trigger("click");

    expect(wrapper.find('[data-test="rules-fixed-seat-switch-prompt"]').exists()).toBe(false);
    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("planning_map");

    await wrapper.get('[data-test="rules-tool-fixed_seat"]').trigger("click");
    await wrapper.get('[data-test="rules-fixed-seat-switch-yes"]').trigger("click");

    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("seating_arrangement");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("fixed_seat");
  });

  it("renders fixed-seat rules in the active rules summary", async () => {
    stateMocks.plannerState.fixedSeatRules = [
      {
        id: "fixed-1",
        template_id: "template-1",
        student_id: "student-2",
        seat_id: "seat-2",
      },
    ];

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="rules-fixed-seat-card"]').text()).toContain("Fast plats");
    expect(wrapper.get('[data-test="rules-fixed-seat-card"]').text()).toContain("Alan Turing");

    await wrapper.get('[data-test="rules-edit-fixed-seat-fixed-1"]').trigger("click");
    await wrapper.get('[data-test="rules-delete-fixed-seat-fixed-1"]').trigger("click");

    expect(stateMocks.plannerState.beginFixedSeatRuleEdit).toHaveBeenCalledWith("fixed-1");
    expect(stateMocks.plannerState.deleteFixedSeatRule).toHaveBeenCalledWith("fixed-1");
  });

  it("shows fixed-seat pending binding, clear selection, and explicit create action", async () => {
    stateMocks.plannerState.activeSeatingSmartTool = "fixed_seat";
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.pendingFixedSeatStudentId = "student-1";
    stateMocks.plannerState.pendingFixedSeatSeatId = "seat-2";
    stateMocks.plannerState.canCommitPendingFixedSeatRule = true;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });
    expect(wrapper.get('[data-test="rules-fixed-seat-panel"]').text()).toContain("Ada Lovelace");
    expect(wrapper.get('[data-test="rules-fixed-seat-panel"]').text()).toContain("plats-2");
    expect(wrapper.get('[data-test="rules-tool-rail"]').text()).toContain("Pågående fast plats");
    expect(wrapper.get('[data-test="rules-tool-rail"]').text()).not.toContain("2 valda");
    expect(wrapper.get('[data-test="rules-fixed-seat-help"]').text()).toBe("Skapa regel låser eleven till platsen.");
    expect(wrapper.get('[data-test="rules-fixed-seat-pending-binding"]').text()).not.toContain("->");
    expect(wrapper.get('[data-test="rules-fixed-seat-pending-link"]').html()).toContain("lucide-link-2");
    expect(wrapper.get('[data-test="rules-fixed-seat-pending-seat"]').classes()).toContain("bg-white");
    expect(wrapper.get('[data-test="rules-commit-fixed-seat"]').text()).toBe("Skapa regel");
    expect(wrapper.get('[data-test="rules-commit-fixed-seat"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="rules-clear-selection"]').attributes("disabled")).toBeUndefined();
    await wrapper.get('[data-test="rules-clear-selection"]').trigger("click");
    await wrapper.get('[data-test="rules-commit-fixed-seat"]').trigger("click");
    expect(stateMocks.plannerState.commitPendingFixedSeatRule).toHaveBeenCalledWith();
  });

  it("edits the persisted near-teacher rule from the summary panel", async () => {
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

  it("activates the near-teacher tool without entering persisted edit mode", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="phone-rules-tool-near_teacher"]').trigger("click");

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("near_teacher");
    expect(stateMocks.plannerState.beginNearTeacherEdit).not.toHaveBeenCalled();
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
    wrapper.get(".planner-rules-tool-column");
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
    expect(wrapper.get('[data-test="phone-rules-tool-keep_apart"]').html()).toContain(
      "text-button-primary-text/75",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-near_teacher"]').html()).toContain(
      "lucide-user-star",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-near_teacher"]').html()).not.toContain(
      "lucide-school",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_near"]').html()).toContain(
      "lucide-magnet",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_near"]').html()).not.toContain(
      "lucide-link-2",
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
    expect(stateMocks.plannerState.clearPendingRuleCandidates).toHaveBeenCalledWith();
    expect(stateMocks.plannerState.commitPendingRelationshipRule).toHaveBeenCalledWith();
  });

  it("removes phone selected candidates with an idempotent remove action", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="phone-rules-selected-student"] button').trigger("click");

    expect(stateMocks.plannerState.removePendingRuleCandidate).toHaveBeenCalledWith("student-2");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
  });

  it("removes already-selected phone student cards instead of toggling them back in", async () => {
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockImplementation(
      (studentId: string) => studentId === "student-2",
    );

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper
      .findAll('[data-test="phone-rules-student-pool"] button')[1]
      .trigger("click");

    expect(stateMocks.plannerState.removePendingRuleCandidate).toHaveBeenCalledWith("student-2");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
  });

  it("renders the approved phone fixed-seat map flow without replacing relationship tools", async () => {
    stateMocks.plannerState.activeSeatingSmartTool = "fixed_seat";
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.pendingFixedSeatStudentId = "student-1";
    stateMocks.plannerState.pendingFixedSeatSeatId = "seat-2";
    stateMocks.plannerState.canCommitPendingFixedSeatRule = true;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.find('[data-test="phone-rules-selection"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="phone-fixed-seat-panel"]').text()).toContain("Välj elev och plats.");
    expect(wrapper.get('[data-test="phone-fixed-seat-pending-student"]').text()).toContain("Ada Lovelace");
    expect(wrapper.get('[data-test="phone-fixed-seat-pending-seat"]').text()).toContain("plats-2");
    expect(wrapper.findAll('button[data-test^="phone-fixed-seat-map-seat-seat-"]')).toHaveLength(2);
    expect(wrapper.get('[data-test="phone-rules-commit-fixed-seat"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-commit-fixed-seat"]').trigger("click");

    expect(stateMocks.plannerState.selectFixedSeatRuleSeat).toHaveBeenCalledWith("seat-1");
    expect(stateMocks.plannerState.commitPendingFixedSeatRule).toHaveBeenCalledWith();
  });

  it("explains that Fast plats requires a classroom on phone", async () => {
    stateMocks.plannerState.template = null;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="phone-rules-tool-fixed_seat"]').trigger("click");

    expect(wrapper.get('[data-test="phone-rules-fixed-seat-classroom-required"]').text()).toContain(
      "Fast plats kräver ett klassrum.",
    );
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).not.toHaveBeenCalledWith("fixed_seat");
  });

  it("starts the rules workspace with a blank near-teacher tool instead of editing persisted rules", () => {
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

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("near_teacher");
    expect(stateMocks.plannerState.beginNearTeacherEdit).not.toHaveBeenCalled();
  });
});
