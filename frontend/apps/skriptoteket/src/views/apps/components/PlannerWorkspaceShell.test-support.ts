/** Shared planner fixtures, mocks, and explicit reset for workspace shell workflow specs. */

import type { mount } from "@vue/test-utils";
import { reactive } from "vue";
import { vi } from "vitest";

import type {
  ClassWorkspaceSummary,
  FixedSeatRule,
  PlanDraft,
  RelationshipRule,
  RoomTemplate,
  Roster,
  SeatingSmartTool,
  Student,
} from "../classroomPlannerTypes";

// Specs import this module before the shell; mock factories read it lazily.
export const toastMocks = {
  info: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
};

type PlannerStateMock = {
  roster: Roster;
  template: RoomTemplate | null;
  draft: Pick<PlanDraft, "id" | "draft_kind" | "revision"> & {
    smart_enabled?: boolean;
    use_history?: boolean;
    grouping_seating_distance_enabled?: boolean;
  };
  students: Student[];
  studentsById: Record<string, Student | undefined>;
  seatsById: Record<string, RoomTemplate["seats"][number] | undefined>;
  ungroupedStudents: Student[];
  unseatedStudents: Student[];
  groups: Array<{ id: string; name: string; sort_order: number; name_is_custom: boolean }>;
  studentsByGroupId: Record<string, Roster["students"]>;
  groupAssignments: Array<{ student_id: string; group_id: string }>;
  seats: RoomTemplate["seats"];
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  fixedSeatRules: FixedSeatRule[];
  pendingRelationshipStudentIds: string[];
  pendingFixedSeatStudentId: string | null;
  pendingFixedSeatSeatId: string | null;
  editingFixedSeatRuleId: string | null;
  editingRelationshipRuleId: string | null;
  editingNearTeacherRule: boolean;
  smartRuleFeedbackMessage: string | null;
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  smartGroupingRunMessage: string | null;
  smartGroupingRunTone: "neutral" | "success" | "warning";
  smartSeatingRunMessage: string | null;
  smartSeatingRunTone: "neutral" | "success" | "warning";
  canCommitPendingRelationshipRule: boolean;
  canCommitPendingFixedSeatRule: boolean;
  plannerStatusLabel: string;
  plannerStatusMessage: string | null;
  plannerStatusTone: "neutral" | "success" | "warning" | "danger";
  plannerConflictMessage: string | null;
  isWorkspaceBusy: boolean;
  isRunningSmartGrouping: boolean;
  isRunningSmartSeating: boolean;
  canEditSeatingSmartRules: boolean;
  canUndo: boolean;
  canRedo: boolean;
  activeSeatingSmartTool: SeatingSmartTool | null;
  beginNearTeacherEdit: ReturnType<typeof vi.fn>;
  setActiveSeatingSmartTool: ReturnType<typeof vi.fn>;
  clearPendingRelationshipSelection: ReturnType<typeof vi.fn>;
  removePendingRuleCandidate: ReturnType<typeof vi.fn>;
  isStudentInPendingRuleCandidates: ReturnType<typeof vi.fn>;
  handleSeatingSmartToolStudentSelection: ReturnType<typeof vi.fn>;
  commitPendingRelationshipRule: ReturnType<typeof vi.fn>;
  commitPendingFixedSeatRule: ReturnType<typeof vi.fn>;
  selectFixedSeatRuleSeat: ReturnType<typeof vi.fn>;
  beginRelationshipRuleEdit: ReturnType<typeof vi.fn>;
  beginFixedSeatRuleEdit: ReturnType<typeof vi.fn>;
  clearNearTeacherRule: ReturnType<typeof vi.fn>;
  deleteRelationshipRule: ReturnType<typeof vi.fn>;
  deleteFixedSeatRule: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
  setDraftUseHistoryEnabled: ReturnType<typeof vi.fn>;
  setDraftGroupingSeatingDistanceEnabled: ReturnType<typeof vi.fn>;
  reloadActiveWorkspace: ReturnType<typeof vi.fn>;
  undoGroupingDraft: ReturnType<typeof vi.fn>;
  redoGroupingDraft: ReturnType<typeof vi.fn>;
  runGroupingShuffle: ReturnType<typeof vi.fn>;
  clearGroupingAssignments: ReturnType<typeof vi.fn>;
  addGroup: ReturnType<typeof vi.fn>;
  assignStudentToGroup: ReturnType<typeof vi.fn>;
  removeStudentFromGroup: ReturnType<typeof vi.fn>;
  renameGroup: ReturnType<typeof vi.fn>;
  moveGroup: ReturnType<typeof vi.fn>;
  removeGroup: ReturnType<typeof vi.fn>;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  randomizeSeating: ReturnType<typeof vi.fn>;
  runSeatingShuffle: ReturnType<typeof vi.fn>;
  clearSeatingAssignments: ReturnType<typeof vi.fn>;
};

export const stateMocks = {
  plannerState: ((): PlannerStateMock => ({
    roster: { id: "roster-1", name: "SA24D", students: [] },
    template: { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
    draft: { id: "draft-1", draft_kind: "grouping", revision: 3 },
    students: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    studentsById: {
      "student-1": { id: "student-1", display_name: "Ada Lovelace" },
      "student-2": { id: "student-2", display_name: "Alan Turing" },
    },
    seatsById: {
      "seat-1": { id: "seat-1", x: 0, y: 0, zone: null },
      "seat-2": { id: "seat-2", x: 120, y: 0, zone: null },
    },
    ungroupedStudents: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    unseatedStudents: [
      { id: "student-1", display_name: "Ada Lovelace" },
      { id: "student-2", display_name: "Alan Turing" },
    ],
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }],
    studentsByGroupId: { "group-a": [] },
    groupAssignments: [],
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: null },
      { id: "seat-2", x: 120, y: 0, zone: null },
    ],
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    seatingPreferences: [],
    relationshipRules: [],
    fixedSeatRules: [],
    pendingRelationshipStudentIds: [],
    pendingFixedSeatStudentId: null,
    pendingFixedSeatSeatId: null,
    editingFixedSeatRuleId: null,
    editingRelationshipRuleId: null,
    editingNearTeacherRule: false,
    smartRuleFeedbackMessage: null,
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    smartGroupingRunMessage: null,
    smartGroupingRunTone: "neutral",
    smartSeatingRunMessage: null,
    smartSeatingRunTone: "neutral",
    canCommitPendingRelationshipRule: false,
    plannerStatusLabel: "Sparad",
    plannerStatusMessage: null,
    plannerStatusTone: "success",
    plannerConflictMessage: null,
    isWorkspaceBusy: false,
    isRunningSmartGrouping: false,
    isRunningSmartSeating: false,
    canEditSeatingSmartRules: true,
    canCommitPendingFixedSeatRule: false,
    canUndo: false,
    canRedo: false,
    activeSeatingSmartTool: null,
    beginNearTeacherEdit: vi.fn(() => {
      stateMocks.plannerState.activeSeatingSmartTool = "near_teacher";
    }),
    setActiveSeatingSmartTool: vi.fn(),
    clearPendingRelationshipSelection: vi.fn(),
    removePendingRuleCandidate: vi.fn(),
    isStudentInPendingRuleCandidates: vi.fn(() => false),
    handleSeatingSmartToolStudentSelection: vi.fn(() => false),
    commitPendingRelationshipRule: vi.fn(() => true),
    commitPendingFixedSeatRule: vi.fn(() => true),
    selectFixedSeatRuleSeat: vi.fn(() => true),
    beginRelationshipRuleEdit: vi.fn(),
    beginFixedSeatRuleEdit: vi.fn(),
    clearNearTeacherRule: vi.fn(() => true),
    deleteRelationshipRule: vi.fn(),
    deleteFixedSeatRule: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
    setDraftUseHistoryEnabled: vi.fn(),
    setDraftGroupingSeatingDistanceEnabled: vi.fn(),
    reloadActiveWorkspace: vi.fn(),
    undoGroupingDraft: vi.fn(),
    redoGroupingDraft: vi.fn(),
    runGroupingShuffle: vi.fn(),
    clearGroupingAssignments: vi.fn(),
    addGroup: vi.fn(),
    assignStudentToGroup: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    renameGroup: vi.fn(),
    moveGroup: vi.fn(),
    removeGroup: vi.fn(),
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    randomizeSeating: vi.fn(),
    runSeatingShuffle: vi.fn(),
    clearSeatingAssignments: vi.fn(),
  }))(),
};

stateMocks.plannerState = reactive(stateMocks.plannerState) as PlannerStateMock;

export function buildWorkspaceSummary(): ClassWorkspaceSummary {
  return {
    roster: { id: "roster-1", name: "SA24D", student_count: 28 },
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
      last_opened_at: "2026-03-21T10:00:00Z",
      updated_at: "2026-03-21T10:15:00Z",
    },
    active_seating_draft: {
      id: "seating-active-1",
      draft_kind: "seating",
      template_id: "template-1",
      template_name: "Sal 101",
      status: "active",
      revision: 4,
      last_opened_at: "2026-03-21T10:00:00Z",
      updated_at: "2026-03-21T10:15:00Z",
    },
    grouping_history: [
      {
        id: "grouping-history-1",
        draft_kind: "grouping",
        template_id: null,
        template_name: null,
        status: "superseded",
        revision: 2,
        last_opened_at: "2026-03-21T09:00:00Z",
        updated_at: "2026-03-21T09:15:00Z",
      },
    ],
    seating_history: [
      {
        id: "seating-history-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "superseded",
        revision: 3,
        last_opened_at: "2026-03-21T08:00:00Z",
        updated_at: "2026-03-21T08:20:00Z",
      },
    ],
  };
}

export function buildRosters(): Roster[] {
  return [
    { id: "roster-1", name: "SA24D", students: [] },
    { id: "roster-2", name: "SA24E", students: [] },
  ];
}

export function findWorkspaceModeToggle(
  wrapper: ReturnType<typeof mount>,
  label: "Översikt" | "Grupper" | "Sittplatser" | "Regler",
) {
  const button = wrapper.findAll('[data-ui="segmented-toggle"] button').find(
    (candidate) => candidate.text() === label,
  );
  if (!button) {
    throw new Error(`Expected the planner top panel to expose ${label}.`);
  }
  return button;
}

export function resetPlannerState(): void {
  toastMocks.info.mockReset();
  toastMocks.success.mockReset();
  toastMocks.warning.mockReset();
  stateMocks.plannerState.reloadActiveWorkspace.mockReset();
  stateMocks.plannerState.plannerConflictMessage = null;
  stateMocks.plannerState.undoGroupingDraft.mockReset();
  stateMocks.plannerState.redoGroupingDraft.mockReset();
  stateMocks.plannerState.runGroupingShuffle.mockReset();
  stateMocks.plannerState.clearGroupingAssignments.mockReset();
  stateMocks.plannerState.addGroup.mockReset();
  stateMocks.plannerState.assignStudentToGroup.mockReset();
  stateMocks.plannerState.removeStudentFromGroup.mockReset();
  stateMocks.plannerState.renameGroup.mockReset();
  stateMocks.plannerState.moveGroup.mockReset();
  stateMocks.plannerState.removeGroup.mockReset();
  stateMocks.plannerState.undoSeatingDraft.mockReset();
  stateMocks.plannerState.redoSeatingDraft.mockReset();
  stateMocks.plannerState.randomizeSeating.mockReset();
  stateMocks.plannerState.runSeatingShuffle.mockReset();
  stateMocks.plannerState.clearSeatingAssignments.mockReset();
  stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
  stateMocks.plannerState.template = {
    id: "template-1",
    name: "Sal 101",
    seats: [],
    fixtures: [],
  };
  stateMocks.plannerState.students = [
    { id: "student-1", display_name: "Ada Lovelace" },
    { id: "student-2", display_name: "Alan Turing" },
  ];
  stateMocks.plannerState.studentsById = {
    "student-1": { id: "student-1", display_name: "Ada Lovelace" },
    "student-2": { id: "student-2", display_name: "Alan Turing" },
  };
  stateMocks.plannerState.ungroupedStudents = [...stateMocks.plannerState.students];
  stateMocks.plannerState.unseatedStudents = [...stateMocks.plannerState.students];
  stateMocks.plannerState.groups = [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }];
  stateMocks.plannerState.studentsByGroupId = { "group-a": [] };
  stateMocks.plannerState.groupAssignments = [];
  stateMocks.plannerState.seats = [
    { id: "seat-1", x: 0, y: 0, zone: null },
    { id: "seat-2", x: 120, y: 0, zone: null },
  ];
  stateMocks.plannerState.seatsById = {
    "seat-1": { id: "seat-1", x: 0, y: 0, zone: null },
    "seat-2": { id: "seat-2", x: 120, y: 0, zone: null },
  };
  stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
  stateMocks.plannerState.seatingPreferences = [];
  stateMocks.plannerState.relationshipRules = [];
  stateMocks.plannerState.fixedSeatRules = [];
  stateMocks.plannerState.pendingRelationshipStudentIds = [];
  stateMocks.plannerState.pendingFixedSeatStudentId = null;
  stateMocks.plannerState.pendingFixedSeatSeatId = null;
  stateMocks.plannerState.editingFixedSeatRuleId = null;
  stateMocks.plannerState.editingRelationshipRuleId = null;
  stateMocks.plannerState.editingNearTeacherRule = false;
  stateMocks.plannerState.smartRuleFeedbackMessage = null;
  stateMocks.plannerState.smartRuleHydrationStatus = "ready";
  stateMocks.plannerState.smartRuleHydrationMessage = null;
  stateMocks.plannerState.smartGroupingRunMessage = null;
  stateMocks.plannerState.smartGroupingRunTone = "neutral";
  stateMocks.plannerState.smartSeatingRunMessage = null;
  stateMocks.plannerState.smartSeatingRunTone = "neutral";
  stateMocks.plannerState.canCommitPendingRelationshipRule = false;
  stateMocks.plannerState.canCommitPendingFixedSeatRule = false;
  stateMocks.plannerState.isWorkspaceBusy = false;
  stateMocks.plannerState.isRunningSmartGrouping = false;
  stateMocks.plannerState.canEditSeatingSmartRules = true;
  stateMocks.plannerState.canUndo = false;
  stateMocks.plannerState.canRedo = false;
  stateMocks.plannerState.activeSeatingSmartTool = null;
  stateMocks.plannerState.beginNearTeacherEdit.mockReset();
  stateMocks.plannerState.beginNearTeacherEdit.mockImplementation(() => {
    stateMocks.plannerState.activeSeatingSmartTool = "near_teacher";
  });
  stateMocks.plannerState.setActiveSeatingSmartTool.mockReset();
  stateMocks.plannerState.clearPendingRelationshipSelection.mockReset();
  stateMocks.plannerState.removePendingRuleCandidate.mockReset();
  stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReset();
  stateMocks.plannerState.isStudentInPendingRuleCandidates.mockReturnValue(false);
  stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReset();
  stateMocks.plannerState.handleSeatingSmartToolStudentSelection.mockReturnValue(false);
  stateMocks.plannerState.commitPendingRelationshipRule.mockReset();
  stateMocks.plannerState.commitPendingRelationshipRule.mockReturnValue(true);
  stateMocks.plannerState.commitPendingFixedSeatRule.mockReset();
  stateMocks.plannerState.commitPendingFixedSeatRule.mockReturnValue(true);
  stateMocks.plannerState.selectFixedSeatRuleSeat.mockReset();
  stateMocks.plannerState.selectFixedSeatRuleSeat.mockReturnValue(true);
  stateMocks.plannerState.beginRelationshipRuleEdit.mockReset();
  stateMocks.plannerState.beginFixedSeatRuleEdit.mockReset();
  stateMocks.plannerState.clearNearTeacherRule.mockReset();
  stateMocks.plannerState.clearNearTeacherRule.mockReturnValue(true);
  stateMocks.plannerState.deleteRelationshipRule.mockReset();
  stateMocks.plannerState.deleteFixedSeatRule.mockReset();
  stateMocks.plannerState.setDraftSmartEnabled.mockReset();
  stateMocks.plannerState.setDraftUseHistoryEnabled.mockReset();
  stateMocks.plannerState.setDraftGroupingSeatingDistanceEnabled.mockReset();
  stateMocks.plannerState.draft = {
    id: "draft-1",
    draft_kind: "grouping",
    revision: 3,
  };
}
