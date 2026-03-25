/**
 * Seating workspace export integration tests.
 *
 * These tests verify that the seating pane renders the compact export cluster
 * and teacher-facing export status behaviors without hard-coding presentation
 * copy into the contract.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerSeatingWorkspacePane from "./PlannerSeatingWorkspacePane.vue";
import type { PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  template: RoomTemplate | null;
  draft: Pick<PlanDraft, "id" | "draft_kind" | "revision">;
  students: Roster["students"];
  unseatedStudents: Roster["students"];
  seats: RoomTemplate["seats"];
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  isWorkspaceBusy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  randomizeSeating: ReturnType<typeof vi.fn>;
  clearSeatAssignment: ReturnType<typeof vi.fn>;
  clearSeatingAssignments: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: null },
      ],
      fixtures: [],
    },
    draft: { id: "draft-1", draft_kind: "seating", revision: 2 },
    students: [{ id: "student-1", display_name: "Ada Lovelace" }],
    unseatedStudents: [{ id: "student-1", display_name: "Ada Lovelace" }],
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    seatAssignments: [],
    isWorkspaceBusy: false,
    canUndo: false,
    canRedo: false,
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    randomizeSeating: vi.fn(),
    clearSeatAssignment: vi.fn(),
    clearSeatingAssignments: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerSeatingWorkspacePane export wiring", () => {
  beforeEach(() => {
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    };
    stateMocks.plannerState.students = [{ id: "student-1", display_name: "Ada Lovelace" }];
    stateMocks.plannerState.unseatedStudents = [{ id: "student-1", display_name: "Ada Lovelace" }];
    stateMocks.plannerState.seats = [{ id: "seat-1", x: 0, y: 0, zone: null }];
    stateMocks.plannerState.seatAssignments = [];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
  });

  it("renders the compact export group and forwards export actions", async () => {
    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
      },
      global: {
        stubs: {
          PlannerStudentPool: { template: "<div data-test='student-pool-stub' />" },
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
          PlannerToolbarIconButton: { template: "<button type='button'><slot /></button>" },
          PlannerToolbarOverflowMenu: { template: "<button type='button' data-test='overflow-menu-stub' />" },
          PlannerConfirmationDialog: true,
        },
      },
    });

    expect(wrapper.find('[data-test="seating-export-group"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-export-default"]').trigger("click");
    expect(wrapper.emitted("export-default")).toEqual([[]]);

    await wrapper.get('[data-test="seating-export-menu-trigger"]').trigger("click");
    expect(wrapper.get('[data-test="seating-export-option-xlsx"]').text()).toContain(
      "Excel (.xlsx)",
    );

    await wrapper.get('[data-test="seating-export-option-xlsx"]').trigger("click");
    expect(wrapper.emitted("export-option")).toEqual([["xlsx"]]);
  });

  it("shows status state, supports retry, and allows dismissal", async () => {
    const wrapper = mount(PlannerSeatingWorkspacePane, {
      props: {
        selectedTemplateId: "template-1",
        exportStatusLabel: "PDF hämtad och sparad i Mina filer.",
        exportErrorMessage: "PDF skapades men kunde inte laddas ned automatiskt.",
        canDownloadLatestExport: true,
      },
      global: {
        stubs: {
          PlannerStudentPool: { template: "<div data-test='student-pool-stub' />" },
          RoomCanvas: { template: "<div data-test='room-canvas-stub' />" },
          PlannerToolbarIconButton: { template: "<button type='button'><slot /></button>" },
          PlannerToolbarOverflowMenu: { template: "<button type='button' data-test='overflow-menu-stub' />" },
          PlannerConfirmationDialog: true,
        },
      },
    });

    expect(wrapper.find('[data-test="seating-export-status-bar"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-export-status"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-export-error"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-export-download-latest"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-export-download-latest"]').trigger("click");
    expect(wrapper.emitted("download-latest-export")).toEqual([[]]);

    await wrapper.get('[data-test="seating-export-status-dismiss"]').trigger("click");
    expect(wrapper.find('[data-test="seating-export-status-bar"]').exists()).toBe(false);
  });
});
