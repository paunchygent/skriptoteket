/**
 * Seating workspace smart-rule interaction tests.
 *
 * These tests lock the first visible smart-rule toolbar flow in the seating
 * pane so the room surface drives rule authoring instead of a drawer-first
 * interaction model.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerSeatingWorkspacePane from "./PlannerSeatingWorkspacePane.vue";
import type { PlanDraft, RelationshipRule, RoomTemplate, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  draft: (
    Pick<PlanDraft, "id" | "draft_kind" | "revision">
    & { smart_enabled?: boolean; use_history?: boolean }
  ) | null;
  canEditSeatingSmartRules: boolean;
  students: Roster["students"];
  studentsById: Record<string, Roster["students"][number]>;
  unseatedStudents: Roster["students"];
  seats: RoomTemplate["seats"];
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  pendingRelationshipStudentIds: string[];
  activeSeatingSmartTool: "near_teacher" | "keep_near" | "keep_apart" | null;
  smartRuleFeedbackMessage: string | null;
  smartSeatingRunMessage: string | null;
  smartSeatingRunTone: "neutral" | "success" | "warning";
  canCommitPendingRelationshipRule: boolean;
  isWorkspaceBusy: boolean;
  isRunningSmartSeating: boolean;
  canUndo: boolean;
  canRedo: boolean;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  randomizeSeating: ReturnType<typeof vi.fn>;
  runSeatingShuffle: ReturnType<typeof vi.fn>;
  clearSeatAssignment: ReturnType<typeof vi.fn>;
  clearSeatingAssignments: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
  setDraftUseHistoryEnabled: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    },
    draft: { id: "draft-1", draft_kind: "seating", revision: 2, smart_enabled: true },
    canEditSeatingSmartRules: true,
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    studentsById: {
      "student-1": { id: "student-1", display_name: "Ada Lovelace" },
      "student-2": { id: "student-2", display_name: "Alan Turing" },
    },
    unseatedStudents: [{ id: "student-2", display_name: "Alan Turing" }],
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ],
    pendingRelationshipStudentIds: [],
    activeSeatingSmartTool: null,
    smartRuleFeedbackMessage: null,
    smartSeatingRunMessage: null,
    smartSeatingRunTone: "neutral",
    canCommitPendingRelationshipRule: false,
    isWorkspaceBusy: false,
    isRunningSmartSeating: false,
    canUndo: false,
    canRedo: false,
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    commitPendingRelationshipRule: vi.fn(() => true),
    deleteRelationshipRule: vi.fn(),
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    randomizeSeating: vi.fn(),
    runSeatingShuffle: vi.fn(),
    clearSeatAssignment: vi.fn(),
    clearSeatingAssignments: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
    setDraftUseHistoryEnabled: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerSeatingWorkspacePane smart rules", () => {
  beforeEach(() => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "seating",
      revision: 2,
      smart_enabled: true,
    };
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ];
    stateMocks.plannerState.activeSeatingSmartTool = null;
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.smartRuleFeedbackMessage = null;
    stateMocks.plannerState.smartSeatingRunMessage = null;
    stateMocks.plannerState.smartSeatingRunTone = "neutral";
    stateMocks.plannerState.canCommitPendingRelationshipRule = false;
    stateMocks.plannerState.canEditSeatingSmartRules = true;
    stateMocks.plannerState.isRunningSmartSeating = false;
    stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
    stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
    stateMocks.plannerState.runSeatingShuffle.mockReset();
  });

  it("renders the visible smart-rule toolbar and summary in the seating pane", () => {
    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.find('[data-test="seating-smart-rule-surface"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Närmare läraren");
    expect(wrapper.text()).toContain("Håll isär");
    expect(wrapper.text()).toContain("Håll nära");
    expect(wrapper.text()).toContain("Aktiva regler");
    expect(wrapper.text()).toContain("Ada Lovelace");
  });

  it("forwards toolbar tool selection and explicit relation commits", async () => {
    stateMocks.plannerState.activeSeatingSmartTool = "keep_apart";
    stateMocks.plannerState.pendingRelationshipStudentIds = ["student-1", "student-2"];
    stateMocks.plannerState.canCommitPendingRelationshipRule = true;

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    await wrapper.get('[data-test="seating-smart-tool-near-teacher"]').trigger("click");
    await wrapper.get('[data-test="seating-smart-commit-rule"]').trigger("click");
    await wrapper.get('[data-test="seating-smart-clear-selection"]').trigger("click");

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("near_teacher");
    expect(stateMocks.plannerState.commitPendingRelationshipRule).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.clearPendingRelationshipSelection).toHaveBeenCalledTimes(1);
  });

  it("shows the overlap feedback message from the store", () => {
    stateMocks.plannerState.smartRuleFeedbackMessage =
      "En elev kan bara ingå i en relationsregel åt gången.";

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.get('[data-test="seating-smart-feedback"]').text()).toContain(
      "En elev kan bara ingå i en relationsregel åt gången.",
    );
  });

  it("disables relationship-rule deletion while the workspace is busy", () => {
    stateMocks.plannerState.canEditSeatingSmartRules = false;

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.get('[data-test="seating-smart-delete-rule-0"]').attributes("disabled")).toBeDefined();
  });

  it("keeps rule authoring enabled even when smart run mode is off", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "seating",
      revision: 2,
      smart_enabled: false,
    };

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.text()).toContain("Smart slumpa: Av");
    expect(wrapper.get('[data-test="seating-smart-tool-near-teacher"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="seating-smart-tool-near-teacher"]').trigger("click");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("near_teacher");
  });

  it("does not render false-valued near-teacher preferences as active markers", () => {
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: false }];
    stateMocks.plannerState.relationshipRules = [];

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.text()).toContain("Inga smarta regler ännu.");
    expect(wrapper.text()).not.toContain("Ada Lovelace");
  });

  it("branches Slumpa through the shared seating shuffle action and exposes use-history", async () => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "seating",
      revision: 2,
      smart_enabled: true,
      use_history: true,
    };

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    await wrapper.get('[data-test="randomize-seating"]').trigger("click");
    await wrapper.get('[data-test="seating-use-history-toggle"] input').setValue(false);

    expect(stateMocks.plannerState.runSeatingShuffle).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.setDraftUseHistoryEnabled).toHaveBeenCalledWith(false);
  });

  it("renders smart-run feedback in the seating pane", () => {
    stateMocks.plannerState.smartSeatingRunMessage =
      "För att använda historik behöver du först exportera ett sittschema för just det här klassrummet.";
    stateMocks.plannerState.smartSeatingRunTone = "warning";

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.get('[data-test="seating-smart-run-message"]').text()).toContain(
      "För att använda historik behöver du först exportera ett sittschema för just det här klassrummet.",
    );
  });
});
