/**
 * Classroom planner store mutations and helper utilities.
 *
 * This module contains the pure-ish reducer helpers used by the classroom
 * planner Pinia store. It keeps local draft mutations and normalization logic
 * separate from the store's remote API orchestration so each file stays within
 * the repository's module-size budget.
 */

import type { ComputedRef, Ref } from "vue";

import { emptyStudentPlanningMeta, type DraftGroup, type GroupAssignment, type PairConstraint, type PairConstraintKind, type PlanningProfile, type RoomFixture, type Seat, type SeatAssignment, type Student, type StudentPlanningMeta } from "./classroomPlannerTypes";

export function buildStudentMap(students: Student[]): Record<string, Student> {
  return Object.fromEntries(students.map((student) => [student.id, student]));
}

export function buildSeatMap(seats: Seat[]): Record<string, Seat> {
  return Object.fromEntries(seats.map((seat) => [seat.id, seat]));
}

export function buildFixtureMap(fixtures: RoomFixture[]): Record<string, RoomFixture> {
  return Object.fromEntries(fixtures.map((fixture) => [fixture.id, fixture]));
}

export function buildGroupMap(groups: DraftGroup[]): Record<string, DraftGroup> {
  return Object.fromEntries(groups.map((group) => [group.id, group]));
}

export function normalizeAssignments<T extends GroupAssignment | SeatAssignment>(
  assignments: T[],
  key: "group_id" | "seat_id",
): Record<string, string | null> {
  return Object.fromEntries(
    assignments.map((assignment) => [
      assignment.student_id,
      key === "group_id"
        ? (assignment as GroupAssignment).group_id
        : (assignment as SeatAssignment).seat_id,
    ]),
  );
}

export function sortedGroups(groups: DraftGroup[]): DraftGroup[] {
  return [...groups].sort((left, right) => left.sort_order - right.sort_order);
}

export function reindexGroups(groups: DraftGroup[]): DraftGroup[] {
  return sortedGroups(groups).map((group, index) => ({ ...group, sort_order: index }));
}

export function normalizePairIds(studentIdA: string, studentIdB: string): [string, string] {
  return studentIdA <= studentIdB ? [studentIdA, studentIdB] : [studentIdB, studentIdA];
}

export function createGroupId(): string {
  return `group-${crypto.randomUUID().slice(0, 8)}`;
}

type MutationContext = {
  studentsById: ComputedRef<Record<string, Student>>;
  seatsById: ComputedRef<Record<string, Seat>>;
  groupsById: ComputedRef<Record<string, DraftGroup>>;
  groups: Ref<DraftGroup[]>;
  groupAssignmentsByStudentId: Ref<Record<string, string | null>>;
  seatAssignmentsByStudentId: Ref<Record<string, string | null>>;
  studentPlanningMetaByStudentId: Ref<Record<string, StudentPlanningMeta>>;
  pairConstraints: Ref<PairConstraint[]>;
  planningProfile: Ref<PlanningProfile>;
  markDirty: () => void;
};

export function createPlannerMutationActions(context: MutationContext) {
  function assignStudentToGroup(studentId: string, groupId: string): void {
    if (!context.studentsById.value[studentId] || !context.groupsById.value[groupId]) {
      return;
    }
    context.groupAssignmentsByStudentId.value = {
      ...context.groupAssignmentsByStudentId.value,
      [studentId]: groupId,
    };
    context.markDirty();
  }

  function removeStudentFromGroup(studentId: string): void {
    if (!context.studentsById.value[studentId]) {
      return;
    }
    context.groupAssignmentsByStudentId.value = {
      ...context.groupAssignmentsByStudentId.value,
      [studentId]: null,
    };
    context.markDirty();
  }

  function assignStudentToSeat(studentId: string, seatId: string): void {
    if (!context.studentsById.value[studentId] || !context.seatsById.value[seatId]) {
      return;
    }
    const nextAssignments = { ...context.seatAssignmentsByStudentId.value };
    for (const [candidateStudentId, assignedSeatId] of Object.entries(nextAssignments)) {
      if (assignedSeatId === seatId) {
        nextAssignments[candidateStudentId] = null;
      }
    }
    nextAssignments[studentId] = seatId;
    context.seatAssignmentsByStudentId.value = nextAssignments;
    context.markDirty();
  }

  function swapSeatAssignments(studentIdA: string, studentIdB: string): void {
    const nextAssignments = { ...context.seatAssignmentsByStudentId.value };
    const seatA = nextAssignments[studentIdA] ?? null;
    const seatB = nextAssignments[studentIdB] ?? null;
    nextAssignments[studentIdA] = seatB;
    nextAssignments[studentIdB] = seatA;
    context.seatAssignmentsByStudentId.value = nextAssignments;
    context.markDirty();
  }

  function clearSeatAssignment(studentId: string): void {
    if (!context.studentsById.value[studentId]) {
      return;
    }
    context.seatAssignmentsByStudentId.value = {
      ...context.seatAssignmentsByStudentId.value,
      [studentId]: null,
    };
    context.markDirty();
  }

  function addGroup(name?: string): void {
    context.groups.value = reindexGroups([
      ...context.groups.value,
      {
        id: createGroupId(),
        name: name?.trim() || `Grupp ${context.groups.value.length + 1}`,
        sort_order: context.groups.value.length,
      },
    ]);
    context.markDirty();
  }

  function renameGroup(groupId: string, name: string): void {
    context.groups.value = context.groups.value.map((group) =>
      group.id === groupId ? { ...group, name: name.trim() || group.name } : group,
    );
    context.markDirty();
  }

  function moveGroup(groupId: string, offset: number): void {
    const currentIndex = context.groups.value.findIndex((group) => group.id === groupId);
    const targetIndex = currentIndex + offset;
    if (currentIndex < 0 || targetIndex < 0 || targetIndex >= context.groups.value.length) {
      return;
    }
    const nextGroups = [...sortedGroups(context.groups.value)];
    const [movedGroup] = nextGroups.splice(currentIndex, 1);
    nextGroups.splice(targetIndex, 0, movedGroup);
    context.groups.value = reindexGroups(nextGroups);
    context.markDirty();
  }

  function removeGroup(groupId: string): void {
    if (context.groups.value.length <= 1) {
      return;
    }
    context.groups.value = reindexGroups(context.groups.value.filter((group) => group.id !== groupId));
    const nextAssignments = { ...context.groupAssignmentsByStudentId.value };
    for (const [studentId, assignedGroupId] of Object.entries(nextAssignments)) {
      if (assignedGroupId === groupId) {
        nextAssignments[studentId] = null;
      }
    }
    context.groupAssignmentsByStudentId.value = nextAssignments;
    context.markDirty();
  }

  function updatePlanningProfile(patch: Partial<PlanningProfile>): void {
    context.planningProfile.value = {
      ...context.planningProfile.value,
      ...patch,
    };
    context.markDirty();
  }

  function setStudentPlanningMeta(studentId: string, patch: Partial<StudentPlanningMeta>): void {
    if (!context.studentsById.value[studentId]) {
      return;
    }
    const current =
      context.studentPlanningMetaByStudentId.value[studentId] ?? emptyStudentPlanningMeta(studentId);
    context.studentPlanningMetaByStudentId.value = {
      ...context.studentPlanningMetaByStudentId.value,
      [studentId]: { ...current, ...patch, student_id: studentId },
    };
    context.markDirty();
  }

  function resetStudentPlanningMeta(studentId: string): void {
    if (!context.studentPlanningMetaByStudentId.value[studentId]) {
      return;
    }
    const nextMeta = { ...context.studentPlanningMetaByStudentId.value };
    delete nextMeta[studentId];
    context.studentPlanningMetaByStudentId.value = nextMeta;
    context.markDirty();
  }

  function setPairConstraint(
    studentIdA: string,
    studentIdB: string,
    kind: PairConstraintKind,
    enabled: boolean,
    strength = 1,
  ): void {
    const [normalizedA, normalizedB] = normalizePairIds(studentIdA, studentIdB);
    const existingIndex = context.pairConstraints.value.findIndex(
      (constraint) =>
        constraint.student_id_a === normalizedA &&
        constraint.student_id_b === normalizedB &&
        constraint.kind === kind,
    );

    if (!enabled) {
      if (existingIndex < 0) {
        return;
      }
      context.pairConstraints.value = context.pairConstraints.value.filter(
        (_, index) => index !== existingIndex,
      );
      context.markDirty();
      return;
    }

    const nextConstraint: PairConstraint = {
      student_id_a: normalizedA,
      student_id_b: normalizedB,
      kind,
      strength,
    };

    if (existingIndex < 0) {
      context.pairConstraints.value = [...context.pairConstraints.value, nextConstraint];
    } else {
      context.pairConstraints.value = context.pairConstraints.value.map((constraint, index) =>
        index === existingIndex ? nextConstraint : constraint,
      );
    }
    context.markDirty();
  }

  return {
    assignStudentToGroup,
    removeStudentFromGroup,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment,
    addGroup,
    renameGroup,
    moveGroup,
    removeGroup,
    updatePlanningProfile,
    setStudentPlanningMeta,
    resetStudentPlanningMeta,
    setPairConstraint,
  };
}
