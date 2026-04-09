/**
 * Shared planner shortcut test harness data.
 *
 * This helper keeps the focused shortcut integration specs small while still
 * mounting the real planner toolbars against one realistic state surface.
 */

import { vi } from "vitest";

import type { ClassWorkspaceSummary } from "../classroomPlannerTypes";

export function createPlannerShortcutTestState() {
  return {
    roster: {
      id: "roster-1",
      name: "SA24D",
      students: [
        { id: "student-1", display_name: "Ada Lovelace" },
        { id: "student-2", display_name: "Alan Turing" },
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
    draft: {
      id: "draft-grouping-1",
      roster_id: "roster-1",
      draft_kind: "grouping" as "grouping" | "seating",
      status: "active" as const,
      revision: 3,
      last_opened_at: "2026-04-09T12:00:00Z",
      smart_enabled: true,
      use_history: true,
      grouping_seating_distance_enabled: false,
    },
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }],
    groupAssignments: [],
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ],
    canUndo: false,
    canRedo: false,
    isWorkspaceBusy: false,
    isRunningSmartSeating: false,
    activeSeatingSmartTool: null,
    smartGroupingRunMessage: null,
    smartGroupingRunTone: "neutral" as const,
    smartSeatingRunMessage: null,
    smartSeatingRunTone: "neutral" as const,
    plannerStatusLabel: null,
    plannerStatusMessage: null,
    plannerStatusTone: "neutral" as const,
    plannerConflictMessage: null,
    handleSeatingSmartToolStudentSelection: vi.fn(() => false),
    reloadActiveWorkspace: vi.fn(async () => {}),
    undoGroupingDraft: vi.fn(async () => {}),
    redoGroupingDraft: vi.fn(async () => {}),
    clearGroupingAssignments: vi.fn(),
    runGroupingShuffle: vi.fn(async () => {}),
    addGroup: vi.fn(),
    removeGroup: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
    undoSeatingDraft: vi.fn(async () => {}),
    redoSeatingDraft: vi.fn(async () => {}),
    clearSeatingAssignments: vi.fn(),
    runSeatingShuffle: vi.fn(async () => {}),
  };
}

export function buildPlannerShortcutWorkspaceSummary(): ClassWorkspaceSummary {
  return {
    roster: { id: "roster-1", name: "SA24D", student_count: 2 },
    task_entry_options: [
      { draft_kind: "grouping", classroom_selection_mode: "optional" },
      { draft_kind: "seating", classroom_selection_mode: "optional" },
    ],
    active_grouping_draft: {
      id: "grouping-active-1",
      draft_kind: "grouping",
      template_id: "template-1",
      template_name: "Sal 101",
      status: "active",
      revision: 5,
      last_opened_at: "2026-04-09T11:00:00Z",
      updated_at: "2026-04-09T11:05:00Z",
    },
    active_seating_draft: {
      id: "seating-active-1",
      draft_kind: "seating",
      template_id: "template-1",
      template_name: "Sal 101",
      status: "active",
      revision: 4,
      last_opened_at: "2026-04-09T11:00:00Z",
      updated_at: "2026-04-09T11:05:00Z",
    },
    grouping_history: [],
    seating_history: [],
  };
}

export const plannerShortcutShellStubs = {
  PlannerTopPanel: {
    template: "<div data-test='planner-top-panel-stub' />",
  },
  PlannerWorkspaceModeSurface: {
    props: ["view"],
    template: `
      <div
        class="planner-workspace-mode-surface-stub"
        :data-view="view"
      >
        <slot name="toolbar" />
        <slot />
      </div>
    `,
  },
  PlannerGroupingWorkspacePane: {
    template: "<div data-test='grouping-pane-stub' />",
  },
  PlannerSeatingWorkspacePane: {
    template: "<div data-test='seating-pane-stub' />",
  },
  PlannerRulesWorkspacePane: {
    template: "<div data-test='rules-pane-stub' />",
  },
  PlannerGroupingSettingsDrawer: {
    template: "<div data-test='grouping-settings-drawer-stub' />",
  },
  PlannerSeatingSettingsDrawer: {
    template: "<div data-test='seating-settings-drawer-stub' />",
  },
  PlannerHistoryDrawer: {
    template: "<div data-test='history-drawer-stub' />",
  },
};
