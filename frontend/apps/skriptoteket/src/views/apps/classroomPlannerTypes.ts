/**
 * Classroom planner frontend types.
 *
 * This module mirrors the bespoke Klassrumskartan API contract used by the SPA.
 * It keeps reusable roster/room entities separate from draft-scoped workspace
 * state so the store, planner view, and room/group components share one typed
 * vocabulary for hydration, autosave, suggestions, randomization, and snapshots.
 */

export const CLASSROOM_PLANNER_DRAFT_SESSION_KEY = "classroom_planner_active_draft_id";

export type LessonMode = {
  id: string;
  name: string;
};

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

export type RoomFixtureType = "whiteboard" | "teacher_desk" | "window" | "door";

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
  seats: Seat[];
  fixtures: RoomFixture[];
};

export type DraftGroup = {
  id: string;
  name: string;
  sort_order: number;
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
  teacher_proximity: number;
  independent_focus_support: number;
  stability_preference: number;
  preferred_zone?: string | null;
  avoid_zone?: string | null;
  notes?: string | null;
};

export type PairConstraintKind =
  | "keep_apart"
  | "prefer_together"
  | "temporary_conflict"
  | "stable_pair";

export type PairConstraint = {
  student_id_a: string;
  student_id_b: string;
  kind: PairConstraintKind;
  strength: number;
};

export type PlanningProfileKind = "focus_first" | "balance_first" | "rotation_first";

export type PlanningProfile = {
  profile_kind: PlanningProfileKind;
  enable_student_meta: boolean;
  enable_pair_constraints: boolean;
  enable_zone_preferences: boolean;
  enable_history_rules: boolean;
  teacher_proximity_weight: number;
  focus_support_weight: number;
  stability_weight: number;
  balance_weight: number;
  rotation_weight: number;
};

export type SuggestionEngineMetadata = {
  suggestion_id: string;
  profile_kind: PlanningProfileKind;
  generated_at: string;
  score_breakdown: Record<string, number>;
  explanation_bullets: string[];
};

export type PlanDraft = {
  id: string;
  roster_id: string;
  template_id: string;
  lesson_mode_id: string;
  revision: number;
  engine_metadata?: SuggestionEngineMetadata | null;
};

export type DraftWorkspaceResponse = {
  draft: PlanDraft;
  roster: Roster;
  template: RoomTemplate;
  groups: DraftGroup[];
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
  student_planning_meta: StudentPlanningMeta[];
  pair_constraints: PairConstraint[];
  planning_profile: PlanningProfile;
};

export type ValidationSeverity = "hard" | "soft";

export type ValidationFinding = {
  severity: ValidationSeverity;
  code: string;
  subject_ref?: string | null;
  message: string;
  explanation: string;
};

export type ValidationResultResponse = {
  findings: ValidationFinding[];
};

export type SuggestionPlan = {
  suggestion_id: string;
  label: string;
  profile_kind: PlanningProfileKind;
  groups: DraftGroup[];
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
  score_breakdown: Record<string, number>;
  findings: ValidationFinding[];
  explanation_bullets: string[];
  engine_metadata: SuggestionEngineMetadata;
};

export type SuggestionListResponse = {
  suggestions: SuggestionPlan[];
};

export type ArrangementSnapshot = {
  id: string;
  source_draft_id: string;
  lesson_mode_id: string;
  snapshot_schema_version: number;
  payload: Record<string, unknown>;
  created_at: string;
};

export type PlannerBootstrapResponse = {
  lesson_modes: LessonMode[];
  feature_flags: Record<string, boolean>;
};

export type SaveStatus = "idle" | "saving" | "saved" | "error" | "conflict";

export const defaultPlanningProfile = (): PlanningProfile => ({
  profile_kind: "balance_first",
  enable_student_meta: true,
  enable_pair_constraints: true,
  enable_zone_preferences: true,
  enable_history_rules: false,
  teacher_proximity_weight: 1,
  focus_support_weight: 1,
  stability_weight: 1,
  balance_weight: 1,
  rotation_weight: 1,
});

export const emptyStudentPlanningMeta = (studentId: string): StudentPlanningMeta => ({
  student_id: studentId,
  teacher_proximity: 0,
  independent_focus_support: 0,
  stability_preference: 0,
  preferred_zone: null,
  avoid_zone: null,
  notes: null,
});

export const pairConstraintLabels: Record<PairConstraintKind, string> = {
  keep_apart: "Håll isär",
  prefer_together: "Placera gärna ihop",
  temporary_conflict: "Tillfällig konflikt",
  stable_pair: "Stabilt par",
};

export const planningProfileLabels: Record<PlanningProfileKind, string> = {
  focus_first: "Fokus först",
  balance_first: "Balans först",
  rotation_first: "Rotation först",
};

export const roomFixturePalette: Array<{
  type: RoomFixtureType;
  label: string;
  width: number;
  height: number;
}> = [
  { type: "whiteboard", label: "Whiteboard", width: 3, height: 1 },
  { type: "teacher_desk", label: "Lärarbord", width: 2, height: 1 },
  { type: "window", label: "Fönster", width: 2, height: 1 },
  { type: "door", label: "Dörr", width: 1, height: 1 },
];
