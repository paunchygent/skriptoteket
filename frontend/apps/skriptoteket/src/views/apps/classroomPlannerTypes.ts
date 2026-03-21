/**
 * Classroom planner frontend types.
 *
 * This module mirrors the active Klassrumskartan frontend contract used by the
 * SPA. It keeps reusable roster/room entities separate from the draft-scoped
 * fundamentals that power the current grouping and seating workflow.
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
  stability_preference: number;
  preferred_zone?: string | null;
  avoid_zone?: string | null;
  notes?: string | null;
};

export type PlanDraftKind = "grouping" | "seating";

export type PlanDraft = {
  id: string;
  roster_id: string;
  draft_kind: PlanDraftKind;
  template_id?: string | null;
  status: "active" | "abandoned" | "superseded";
  revision: number;
  last_opened_at: string;
};

export type ResumablePlanDraft = {
  draft: PlanDraft;
  roster_name: string;
  template_name?: string | null;
};

export type DraftWorkspaceResponse = {
  draft: PlanDraft;
  roster: Roster;
  template?: RoomTemplate | null;
  groups: DraftGroup[];
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
  student_planning_meta: StudentPlanningMeta[];
};

export type SaveStatus = "idle" | "saving" | "saved" | "error" | "conflict";

export const emptyStudentPlanningMeta = (studentId: string): StudentPlanningMeta => ({
  student_id: studentId,
  teacher_proximity: 0,
  stability_preference: 0,
  preferred_zone: null,
  avoid_zone: null,
  notes: null,
});

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
