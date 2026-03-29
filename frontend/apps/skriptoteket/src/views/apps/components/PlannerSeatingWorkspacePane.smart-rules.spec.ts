/**
 * Seating workspace smart-rule interaction tests.
 *
 * These tests lock the compact smart-summary cut-over in the seating pane so
 * rule authoring stays inside the dedicated `Regler` workspace.
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
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
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
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
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
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
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
    retrySmartRuleHydration: vi.fn(),
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
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.smartSeatingRunMessage = null;
    stateMocks.plannerState.smartSeatingRunTone = "neutral";
    stateMocks.plannerState.canCommitPendingRelationshipRule = false;
    stateMocks.plannerState.canEditSeatingSmartRules = true;
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.isRunningSmartSeating = false;
    stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
    stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
    stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
    stateMocks.plannerState.deleteRelationshipRule.mockReset();
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
    stateMocks.plannerState.runSeatingShuffle.mockReset();
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
  });

  it("renders the compact smart summary and Regler entry point in the seating pane", () => {
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

    expect(wrapper.find('[data-test="seating-smart-rule-surface"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-open-rules"]').exists()).toBe(true);
    expect(wrapper.get('[aria-label="Aktiva regler"]').text()).toContain("2 aktiva regler");
    expect(wrapper.text()).toContain("Närmare läraren");
    expect(wrapper.text()).toContain("Håll isär");
    expect(wrapper.text()).toContain("Ada Lovelace");
  });

  it("opens Regler from the small settings affordance beside Smart", async () => {
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

    await wrapper.get('[data-test="seating-open-rules"]').trigger("click");

    expect(wrapper.emitted("open-rules")).toEqual([[]]);
  });

  it("shows smart-rule hydration errors without reintroducing inline editing", () => {
    stateMocks.plannerState.smartRuleHydrationStatus = "error";
    stateMocks.plannerState.smartRuleHydrationMessage = "Kunde inte ladda smarta regler.";

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

    expect(wrapper.get('[data-test="seating-smart-hydration-error"]').text()).toContain(
      "Kunde inte ladda smarta regler.",
    );
    expect(wrapper.find('[data-test="seating-smart-commit-rule"]').exists()).toBe(false);
  });

  it("disables the Regler entry point while the seating lifecycle is busy", () => {
    stateMocks.plannerState.isWorkspaceBusy = true;

    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
        seatingLifecycleBusy: true,
      },
      global: {
        stubs: {
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
        },
      },
    });

    expect(wrapper.get('[data-test="seating-open-rules"]').attributes("disabled")).toBeDefined();
  });

  it("keeps the Regler entry point available even when smart run mode is off", async () => {
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

    expect(wrapper.get('[aria-label="Aktiva regler"]').text()).toContain("2 aktiva regler");
    expect(wrapper.get('[data-test="seating-open-rules"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="seating-open-rules"]').trigger("click");
    expect(wrapper.emitted("open-rules")).toEqual([[]]);
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

    expect(wrapper.text()).toContain("Inga regler ännu. Öppna Regler för att lägga till eller ändra dem.");
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
    await wrapper.get('[data-test="seating-use-history-toggle"]').trigger("click");

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
