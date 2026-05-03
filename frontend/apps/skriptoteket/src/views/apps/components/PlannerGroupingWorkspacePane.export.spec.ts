/**
 * Grouping workspace toolbar tests.
 *
 * These tests lock the ST-29-02 cut-over where grouping export and helper
 * feedback live in the detached shell toolbar instead of inside the work pane.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerGroupingWorkspaceToolbar from "./PlannerGroupingWorkspaceToolbar.vue";
import type { DraftGroup, PlanDraft, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  draft: (Pick<PlanDraft, "id" | "draft_kind" | "revision"> & {
    smart_enabled?: boolean;
    use_history?: boolean;
    grouping_seating_distance_enabled?: boolean;
  }) | null;
  groupAssignments: Array<{ student_id: string; group_id: string }>;
  groups: DraftGroup[];
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: Array<{ id: string; kind: "keep_near" | "keep_apart"; student_ids: string[] }>;
  isWorkspaceBusy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  undoGroupingDraft: ReturnType<typeof vi.fn>;
  redoGroupingDraft: ReturnType<typeof vi.fn>;
  runGroupingShuffle: ReturnType<typeof vi.fn>;
  clearGroupingAssignments: ReturnType<typeof vi.fn>;
  addGroup: ReturnType<typeof vi.fn>;
  removeGroup: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
  setDraftUseHistoryEnabled: ReturnType<typeof vi.fn>;
  setDraftGroupingSeatingDistanceEnabled: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    draft: {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 2,
      smart_enabled: true,
      use_history: true,
      grouping_seating_distance_enabled: true,
    },
    groupAssignments: [],
    groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ],
    isWorkspaceBusy: false,
    canUndo: false,
    canRedo: false,
    undoGroupingDraft: vi.fn(),
    redoGroupingDraft: vi.fn(),
    runGroupingShuffle: vi.fn(),
    clearGroupingAssignments: vi.fn(),
    addGroup: vi.fn(),
    removeGroup: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
    setDraftUseHistoryEnabled: vi.fn(),
    setDraftGroupingSeatingDistanceEnabled: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

function buildRosters(): Roster[] {
  return [
    { id: "roster-1", name: "SA24D", students: [] },
    { id: "roster-2", name: "SA24E", students: [] },
  ];
}

describe("PlannerGroupingWorkspaceToolbar", () => {
  beforeEach(() => {
    stateMocks.plannerState.draft = {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 2,
      smart_enabled: true,
      use_history: true,
      grouping_seating_distance_enabled: true,
    };
    stateMocks.plannerState.groupAssignments = [];
    stateMocks.plannerState.groups = [
      { id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false },
    ];
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
    stateMocks.plannerState.undoGroupingDraft.mockReset();
    stateMocks.plannerState.redoGroupingDraft.mockReset();
    stateMocks.plannerState.runGroupingShuffle.mockReset();
    stateMocks.plannerState.clearGroupingAssignments.mockReset();
    stateMocks.plannerState.addGroup.mockReset();
    stateMocks.plannerState.removeGroup.mockReset();
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
    stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled.mockReset();
  });

  it("renders the detached class selector and Smart settings trigger without extra toolbar toggles", async () => {
    const wrapper = mount(PlannerGroupingWorkspaceToolbar, {
      props: {
        availableRosters: buildRosters(),
        selectedRosterId: "roster-1",
      },
    });

    expect(wrapper.get('[data-test="grouping-roster-select"]').classes()).toContain("h-[28px]");
    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-active-rule-count"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-use-history-toggle"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-template-select"]').exists()).toBe(false);
    expect(wrapper.get('[data-zone="primary"]').find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.get('[data-zone="context"]').find('[data-test="grouping-roster-control"]').exists()).toBe(true);
    expect(wrapper.get('[data-zone="secondary"]').find('[data-test="grouping-actions-menu"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="grouping-open-settings"]').attributes("aria-label")).toBe(
      "Smart-inställningar",
    );
    expect(wrapper.get('[data-test="grouping-open-settings"]').attributes("aria-haspopup")).toBe("dialog");

    await wrapper.get('[data-test="grouping-roster-select"]').setValue("roster-2");

    expect(wrapper.emitted("change-grouping-roster")).toEqual([["roster-2"]]);
  });

  it("forwards export actions and keeps processing feedback inside the export control", async () => {
    const wrapper = mount(PlannerGroupingWorkspaceToolbar, {
      props: {
        availableRosters: buildRosters(),
        selectedRosterId: "roster-1",
        exportBusy: true,
        exportStatusLabel: "Exporterar…",
      },
    });

    expect(wrapper.find('[data-test="grouping-export-status-bar"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-export-status-pill"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="grouping-export-default"]').find('[data-ui="dense-spinner"]').exists())
      .toBe(true);
    expect(wrapper.get('[data-zone="secondary"]').find('[data-test="grouping-export-group"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-export-default"]').trigger("click");
    expect(wrapper.emitted("export-default")).toBeUndefined();

    await wrapper.get('[data-test="grouping-export-menu-trigger"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-export-option-pdf"]').exists()).toBe(false);
  });

  it("uses the quiet group-count stepper and new-draft action in the detached toolbar", async () => {
    stateMocks.plannerState.groups = [
      { id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-2", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ];

    const wrapper = mount(PlannerGroupingWorkspaceToolbar, {
      props: {
        availableRosters: buildRosters(),
        selectedRosterId: "roster-1",
      },
    });

    expect(wrapper.find('[data-test="add-group"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="group-count-value"]').text()).toContain("2");

    await wrapper.get('[data-test="randomize-groups"]').trigger("click");
    expect(stateMocks.plannerState.runGroupingShuffle).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-test="increment-group-count"]').trigger("click");
    expect(stateMocks.plannerState.addGroup).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-test="decrement-group-count"]').trigger("click");
    expect(stateMocks.plannerState.removeGroup).toHaveBeenCalledWith("group-2");

    await wrapper.get('[data-test="new-grouping-draft"]').trigger("click");
    expect(wrapper.emitted("new-grouping-draft")).toEqual([[]]);
  });
});
