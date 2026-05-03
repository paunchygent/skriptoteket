/**
 * Seating workspace toolbar tests.
 *
 * These tests lock the ST-29-02 cut-over where seating export and compact
 * helper affordances live in the detached shell toolbar instead of the pane.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerSeatingWorkspaceToolbar from "./PlannerSeatingWorkspaceToolbar.vue";
import type { PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  draft: (Pick<PlanDraft, "id" | "draft_kind" | "revision"> & {
    smart_enabled?: boolean;
    use_history?: boolean;
  }) | null;
  students: Roster["students"];
  seats: RoomTemplate["seats"];
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: Array<{ id: string; kind: "keep_near" | "keep_apart"; student_ids: string[] }>;
  isWorkspaceBusy: boolean;
  isRunningSmartSeating: boolean;
  canUndo: boolean;
  canRedo: boolean;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  runSeatingShuffle: ReturnType<typeof vi.fn>;
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
    draft: {
      id: "draft-1",
      draft_kind: "seating",
      revision: 2,
      smart_enabled: true,
      use_history: true,
    },
    students: [{ id: "student-1", display_name: "Ada Lovelace" }],
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ],
    isWorkspaceBusy: false,
    isRunningSmartSeating: false,
    canUndo: false,
    canRedo: false,
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    runSeatingShuffle: vi.fn(),
    clearSeatingAssignments: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
    setDraftUseHistoryEnabled: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

function buildTemplate(): RoomTemplate {
  return {
    id: "template-1",
    name: "Sal 101",
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    fixtures: [],
  };
}

describe("PlannerSeatingWorkspaceToolbar", () => {
  beforeEach(() => {
    stateMocks.plannerState.template = buildTemplate();
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "seating",
      revision: 2,
      smart_enabled: true,
      use_history: true,
    };
    stateMocks.plannerState.students = [{ id: "student-1", display_name: "Ada Lovelace" }];
    stateMocks.plannerState.seats = [{ id: "seat-1", x: 0, y: 0, zone: null }];
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.isRunningSmartSeating = false;
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
    stateMocks.plannerState.undoSeatingDraft.mockReset();
    stateMocks.plannerState.redoSeatingDraft.mockReset();
    stateMocks.plannerState.runSeatingShuffle.mockReset();
    stateMocks.plannerState.clearSeatingAssignments.mockReset();
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
  });

  it("renders the detached seating selector and smart-settings trigger without a redundant rule pill", () => {
    const wrapper = mount(PlannerSeatingWorkspaceToolbar, {
      props: {
        availableTemplates: [buildTemplate()],
        selectedTemplateId: "template-1",
      },
    });

    expect(wrapper.get('[data-test="seating-template-select"]').classes()).toContain("h-[28px]");
    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-use-history-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-open-rules"]').exists()).toBe(false);
    expect(wrapper.get('[data-zone="primary"]').find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.get('[data-zone="context"]').find('[data-test="seating-workspace-setup"]').exists()).toBe(true);
    expect(wrapper.get('[data-zone="secondary"]').find('[data-test="seating-actions-menu"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="seating-open-settings"]').attributes("aria-label")).toBe(
      "Smart-inställningar",
    );
    expect(wrapper.find('[data-test="seating-active-rule-count"]').exists()).toBe(false);
  });

  it("routes seating actions through the detached toolbar controls", async () => {
    const wrapper = mount(PlannerSeatingWorkspaceToolbar, {
      props: {
        availableTemplates: [buildTemplate()],
        selectedTemplateId: "template-1",
      },
    });

    await wrapper.get('[data-test="randomize-seating"]').trigger("click");
    await wrapper.get('[data-test="seating-open-settings"]').trigger("click");

    expect(stateMocks.plannerState.runSeatingShuffle).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted("open-settings")).toEqual([[]]);
  });

  it("keeps processing feedback inside the export control and forwards seating export actions", async () => {
    const wrapper = mount(PlannerSeatingWorkspaceToolbar, {
      props: {
        availableTemplates: [buildTemplate()],
        selectedTemplateId: "template-1",
        exportBusy: true,
        exportStatusLabel: "Exporterar…",
      },
    });

    expect(wrapper.find('[data-test="seating-export-status-bar"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-export-status-pill"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="seating-export-default"]').find('[data-ui="dense-spinner"]').exists())
      .toBe(true);
    expect(wrapper.get('[data-zone="secondary"]').find('[data-test="seating-export-group"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-export-default"]').trigger("click");
    expect(wrapper.emitted("export-default")).toBeUndefined();

    await wrapper.get('[data-test="seating-export-menu-trigger"]').trigger("click");
    expect(wrapper.find('[data-test="seating-export-option-xlsx"]').exists()).toBe(false);
  });

  it("focuses the classroom picker instead of starting a draft without a classroom", async () => {
    const wrapper = mount(PlannerSeatingWorkspaceToolbar, {
      attachTo: document.body,
      props: {
        availableTemplates: [buildTemplate()],
        selectedTemplateId: null,
      },
    });

    await wrapper.get('[data-test="new-seating-draft"]').trigger("click");

    expect(wrapper.emitted("new-seating-draft")).toBeUndefined();
    expect(wrapper.get('[data-test="seating-template-select"]').element).toBe(document.activeElement);
    expect(wrapper.text()).toContain("Välj klassrum innan du startar ett nytt sittschema.");

    wrapper.unmount();
  });
});
