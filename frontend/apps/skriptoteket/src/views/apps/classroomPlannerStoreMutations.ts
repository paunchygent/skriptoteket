/**
 * Classroom planner store mutations and helper utilities.
 *
 * This module contains the pure-ish reducer helpers used by the classroom
 * planner Pinia store. It keeps local draft mutations and normalization logic
 * separate from the store's remote API orchestration so each file stays within
 * the repository's module-size budget.
 */

import type { ComputedRef, Ref } from "vue";

import {
  emptyStudentPlanningMeta,
  type DraftGroup,
  type GroupAssignment,
  type RoomFixture,
  type Seat,
  type SeatAssignment,
  type Student,
  type StudentPlanningMeta,
} from "./classroomPlannerTypes";

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

export function buildDefaultGroupName(position: number): string {
  return `Grupp ${position + 1}`;
}

function resolveCustomGroupNameState(name: string, sortOrder: number): boolean {
  return name !== buildDefaultGroupName(sortOrder);
}

export function reindexGroups(groups: DraftGroup[]): DraftGroup[] {
  return groups.map((group, index) => ({
    ...group,
    sort_order: index,
    name: group.name_is_custom ? group.name : buildDefaultGroupName(index),
  }));
}

export function createGroupId(): string {
  return `group-${crypto.randomUUID().slice(0, 8)}`;
}

type MutationContext = {
  students: ComputedRef<Student[]>;
  studentsById: ComputedRef<Record<string, Student>>;
  seatsById: ComputedRef<Record<string, Seat>>;
  groupsById: ComputedRef<Record<string, DraftGroup>>;
  groups: Ref<DraftGroup[]>;
  groupAssignmentsByStudentId: Ref<Record<string, string | null>>;
  seatAssignmentsByStudentId: Ref<Record<string, string | null>>;
  studentPlanningMetaByStudentId: Ref<Record<string, StudentPlanningMeta>>;
  canMutate: () => boolean;
  markDirty: () => void;
};

function shuffleStudents(students: Student[]): Student[] {
  const shuffled = [...students];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const targetIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[targetIndex]] = [shuffled[targetIndex]!, shuffled[index]!];
  }
  return shuffled;
}

export function buildRandomizedGroupAssignments(
  students: Student[],
  groups: DraftGroup[],
): Record<string, string | null> {
  if (groups.length === 0) {
    return Object.fromEntries(students.map((student) => [student.id, null]));
  }

  const randomizedStudents = shuffleStudents(students);
  const orderedGroups = sortedGroups(groups);

  return Object.fromEntries(
    randomizedStudents.map((student, index) => [
      student.id,
      orderedGroups[index % orderedGroups.length]?.id ?? null,
    ]),
  );
}

export function buildRandomizedSeatAssignments(
  students: Student[],
  seats: Seat[],
): Record<string, string | null> {
  const randomizedStudents = shuffleStudents(students);
  const orderedSeatIds = seats.map((seat) => seat.id);

  return Object.fromEntries(
    randomizedStudents.map((student, index) => [
      student.id,
      orderedSeatIds[index] ?? null,
    ]),
  );
}

export function createPlannerMutationActions(context: MutationContext) {
  function assignStudentToGroup(studentId: string, groupId: string): void {
    if (!context.canMutate()) {
      return;
    }
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
    if (!context.canMutate()) {
      return;
    }
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
    if (!context.canMutate()) {
      return;
    }
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
    if (!context.canMutate()) {
      return;
    }
    const nextAssignments = { ...context.seatAssignmentsByStudentId.value };
    const seatA = nextAssignments[studentIdA] ?? null;
    const seatB = nextAssignments[studentIdB] ?? null;
    nextAssignments[studentIdA] = seatB;
    nextAssignments[studentIdB] = seatA;
    context.seatAssignmentsByStudentId.value = nextAssignments;
    context.markDirty();
  }

  function clearSeatAssignment(studentId: string): void {
    if (!context.canMutate()) {
      return;
    }
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
    if (!context.canMutate()) {
      return;
    }
    const nextSortOrder = context.groups.value.length;
    const normalizedName = name?.trim() || buildDefaultGroupName(nextSortOrder);
    context.groups.value = reindexGroups([
      ...context.groups.value,
      {
        id: createGroupId(),
        name: normalizedName,
        sort_order: nextSortOrder,
        name_is_custom: resolveCustomGroupNameState(normalizedName, nextSortOrder),
      },
    ]);
    context.markDirty();
  }

  function renameGroup(groupId: string, name: string): void {
    if (!context.canMutate()) {
      return;
    }
    let didChange = false;
    context.groups.value = context.groups.value.map((group) => {
      if (group.id !== groupId) {
        return group;
      }
      const normalizedName = name.trim() || buildDefaultGroupName(group.sort_order);
      const nameIsCustom = resolveCustomGroupNameState(normalizedName, group.sort_order);
      const nextName = nameIsCustom ? normalizedName : buildDefaultGroupName(group.sort_order);
      if (group.name === nextName && group.name_is_custom === nameIsCustom) {
        return group;
      }
      didChange = true;
      return {
        ...group,
        name: nextName,
        name_is_custom: nameIsCustom,
      };
    });
    if (!didChange) {
      return;
    }
    context.markDirty();
  }

  function moveGroup(groupId: string, offset: number): void {
    if (!context.canMutate()) {
      return;
    }
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
    if (!context.canMutate()) {
      return;
    }
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

  function randomizeGroups(): void {
    if (!context.canMutate()) {
      return;
    }
    context.groupAssignmentsByStudentId.value = buildRandomizedGroupAssignments(
      context.students.value,
      context.groups.value,
    );
    context.markDirty();
  }

  function randomizeSeating(): void {
    if (!context.canMutate()) {
      return;
    }
    context.seatAssignmentsByStudentId.value = buildRandomizedSeatAssignments(
      context.students.value,
      Object.values(context.seatsById.value),
    );
    context.markDirty();
  }

  function setStudentPlanningMeta(studentId: string, patch: Partial<StudentPlanningMeta>): void {
    if (!context.canMutate()) {
      return;
    }
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
    if (!context.canMutate()) {
      return;
    }
    if (!context.studentPlanningMetaByStudentId.value[studentId]) {
      return;
    }
    const nextMeta = { ...context.studentPlanningMetaByStudentId.value };
    delete nextMeta[studentId];
    context.studentPlanningMetaByStudentId.value = nextMeta;
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
    randomizeGroups,
    randomizeSeating,
    setStudentPlanningMeta,
    resetStudentPlanningMeta,
  };
}
