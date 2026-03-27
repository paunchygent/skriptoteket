/**
 * Classroom planner frontend types.
 *
 * This module mirrors the active Klassrumskartan frontend contract used by the
 * SPA. It keeps reusable roster/room entities and roster-global smart rules
 * separate from the draft-scoped fundamentals that power the current grouping
 * and seating workflow.
 */

export type Student = {
  id: string;
  display_name: string;
};

export type Roster = {
  id: string;
  name: string;
  students: Student[];
};

export type Seat = {
  id: string;
  x: number;
  y: number;
  zone?: string | null;
};

export type RoomFixtureType =
  | "whiteboard"
  | "teacher_desk"
  | "window"
  | "door"
  | "round_table"
  | "square_table"
  | "bench";

export type RoomFixture = {
  id: string;
  type: RoomFixtureType;
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string | null;
};

export type RoomTemplate = {
  id: string;
  name: string;
  grid_cols?: number;
  grid_rows?: number;
  seats: Seat[];
  fixtures: RoomFixture[];
};

export type DraftGroup = {
  id: string;
  name: string;
  sort_order: number;
  name_is_custom: boolean;
};

export type GroupAssignment = {
  student_id: string;
  group_id: string;
};

export type SeatAssignment = {
  student_id: string;
  seat_id: string;
};

export type StudentPlanningMeta = {
  student_id: string;
  notes?: string | null;
};

export type PlanDraftKind = "grouping" | "seating";
export type ClassroomSelectionMode = "optional" | "required";

export type PlanDraft = {
  id: string;
  roster_id: string;
  draft_kind: PlanDraftKind;
  template_id?: string | null;
  smart_enabled?: boolean;
  use_history?: boolean;
  grouping_seating_distance_enabled?: boolean;
  status: "active" | "abandoned" | "superseded";
  revision: number;
  last_opened_at: string;
};

export type StudentSeatingPreference = {
  student_id: string;
  near_teacher: boolean;
};

export type SeatingSmartTool = "near_teacher" | "keep_near" | "keep_apart";

export type RelationshipRuleKind = "keep_near" | "keep_apart";

export type RelationshipRule = {
  id: string;
  kind: RelationshipRuleKind;
  student_ids: string[];
};

export type ResumablePlanDraft = {
  draft: PlanDraft;
  roster_name: string;
  template_name?: string | null;
};

export type TaskEntryOption = {
  draft_kind: PlanDraftKind;
  classroom_selection_mode: ClassroomSelectionMode;
};

export type PlanDraftSummary = {
  id: string;
  draft_kind: PlanDraftKind;
  template_id?: string | null;
  template_name?: string | null;
  status: "active" | "abandoned" | "superseded";
  revision: number;
  last_opened_at: string;
  updated_at: string;
};

export type ClassWorkspaceRosterSummary = {
  id: string;
  name: string;
  student_count: number;
};

export type ClassWorkspaceSummary = {
  roster: ClassWorkspaceRosterSummary;
  task_entry_options: TaskEntryOption[];
  active_grouping_draft?: PlanDraftSummary | null;
  active_seating_draft?: PlanDraftSummary | null;
  grouping_history: PlanDraftSummary[];
  seating_history: PlanDraftSummary[];
};

export type DraftWorkspaceResponse = {
  draft: PlanDraft;
  roster: Roster;
  template?: RoomTemplate | null;
  groups: DraftGroup[];
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
  student_planning_meta: StudentPlanningMeta[];
  history_status: {
    can_undo: boolean;
    can_redo: boolean;
  };
};

export type AppliedSmartSeatingRunResponse = {
  status: "applied";
  workspace: DraftWorkspaceResponse;
  used_history: boolean;
  message?: string | null;
};

export type BlockedSmartSeatingRunResponse = {
  status: "blocked";
  reason: "no_history";
  workspace: null;
  used_history: false;
  message: string;
};

export type SmartSeatingRunResponse =
  | AppliedSmartSeatingRunResponse
  | BlockedSmartSeatingRunResponse;

export type RosterSmartRulesResponse = {
  roster_id: string;
  revision: number;
  seating_preferences: StudentSeatingPreference[];
  relationship_rules: RelationshipRule[];
};

export type DraftHistoryStatus = DraftWorkspaceResponse["history_status"];

export type SaveStatus = "idle" | "saving" | "saved" | "error" | "conflict";

export const emptyStudentPlanningMeta = (studentId: string): StudentPlanningMeta => ({
  student_id: studentId,
  notes: null,
});
