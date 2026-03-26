/**
 * Grouping workspace export integration tests.
 *
 * These tests verify that the grouping pane renders the compact export
 * cluster and teacher-facing placeholder export status without leaking
 * seating-specific wording into the grouping task.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerGroupingWorkspacePane from "./PlannerGroupingWorkspacePane.vue";
import type { DraftGroup, PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  draft: Pick<PlanDraft, "id" | "draft_kind" | "revision">;
  ungroupedStudents: Roster["students"];
  groups: DraftGroup[];
  groupAssignments: Array<{ student_id: string; group_id: string }>;
  studentsByGroupId: Record<string, Roster["students"]>;
  isWorkspaceBusy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  undoGroupingDraft: ReturnType<typeof vi.fn>;
  redoGroupingDraft: ReturnType<typeof vi.fn>;
  randomizeGroups: ReturnType<typeof vi.fn>;
  clearGroupingAssignments: ReturnType<typeof vi.fn>;
  addGroup: ReturnType<typeof vi.fn>;
  removeStudentFromGroup: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [],
      fixtures: [],
    },
    draft: { id: "draft-1", draft_kind: "grouping", revision: 2 },
    ungroupedStudents: [{ id: "student-1", display_name: "Ada Lovelace" }],
    groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
    groupAssignments: [],
    studentsByGroupId: { "group-1": [] },
    isWorkspaceBusy: false,
    canUndo: false,
    canRedo: false,
    undoGroupingDraft: vi.fn(),
    redoGroupingDraft: vi.fn(),
    randomizeGroups: vi.fn(),
    clearGroupingAssignments: vi.fn(),
    addGroup: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerGroupingWorkspacePane export wiring", () => {
  beforeEach(() => {
    stateMocks.plannerState.groupAssignments = [];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
  });

  it("renders the grouping export cluster and forwards export actions", async () => {
    const wrapper = mount(PlannerGroupingWorkspacePane, {
      global: {
        stubs: {
          PlannerStudentPool: { template: "<div data-test='student-pool-stub' />" },
          GroupBoard: { template: "<div data-test='group-board-stub' />" },
          PlannerToolbarIconButton: { template: "<button type='button'><slot /></button>" },
          PlannerToolbarOverflowMenu: { template: "<button type='button' data-test='overflow-menu-stub' />" },
          PlannerConfirmationDialog: true,
        },
      },
    });

    expect(wrapper.find('[data-test="grouping-export-group"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-export-default"]').trigger("click");
    expect(wrapper.emitted("export-default")).toEqual([[]]);

    await wrapper.get('[data-test="grouping-export-menu-trigger"]').trigger("click");
    expect(wrapper.get('[data-test="grouping-export-option-pdf"]').text()).toContain(
      "PDF (A4 stående)",
    );

    await wrapper.get('[data-test="grouping-export-option-pdf"]').trigger("click");
    expect(wrapper.emitted("export-option")).toEqual([["pdf_a4_portrait"]]);
  });

  it("shows status state, supports retry, and allows dismissal", async () => {
    const wrapper = mount(PlannerGroupingWorkspacePane, {
      props: {
        exportStatusLabel: "Exporten tar längre tid än väntat. Vi fortsätter att kontrollera den.",
        exportErrorMessage: "PDF skapades men kunde inte laddas ned automatiskt.",
        canDownloadLatestExport: true,
      },
      global: {
        stubs: {
          PlannerStudentPool: { template: "<div data-test='student-pool-stub' />" },
          GroupBoard: { template: "<div data-test='group-board-stub' />" },
          PlannerToolbarIconButton: { template: "<button type='button'><slot /></button>" },
          PlannerToolbarOverflowMenu: { template: "<button type='button' data-test='overflow-menu-stub' />" },
          PlannerConfirmationDialog: true,
        },
      },
    });

    expect(wrapper.find('[data-test="grouping-export-status-bar"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-export-status"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-export-error"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-export-download-latest"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-export-download-latest"]').trigger("click");
    expect(wrapper.emitted("download-latest-export")).toEqual([[]]);

    await wrapper.get('[data-test="grouping-export-status-dismiss"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-export-status-bar"]').exists()).toBe(false);
  });
});
