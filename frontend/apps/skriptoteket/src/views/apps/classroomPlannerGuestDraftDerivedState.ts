/**
 * Classroom planner guest draft derived state.
 *
 * This module centralizes the pure computed projections for the guest planner
 * session so the main session controller can focus on lifecycle and
 * persistence boundaries.
 */

import { computed, type Ref } from "vue";

import {
  buildFixtureMap,
  buildGroupMap,
  buildSeatMap,
  buildStudentMap,
} from "./classroomPlannerStoreMutations";
import type {
  DraftGroup,
  GroupAssignment,
  RoomTemplate,
  Roster,
  SeatAssignment,
  Student,
} from "./classroomPlannerTypes";

type AssignmentMap = Record<string, string | null>;

function hasAssignedTarget(entry: [string, string | null]): entry is [string, string] {
  return typeof entry[1] === "string" && entry[1].length > 0;
}

export function createClassroomPlannerGuestDraftDerivedState(options: {
  roster: Ref<Roster | null>;
  template: Ref<RoomTemplate | null>;
  groups: Ref<DraftGroup[]>;
  groupAssignmentsByStudentId: Ref<AssignmentMap>;
  seatAssignmentsByStudentId: Ref<AssignmentMap>;
}) {
  const students = computed(() => options.roster.value?.students ?? []);
  const seats = computed(() => options.template.value?.seats ?? []);
  const fixtures = computed(() => options.template.value?.fixtures ?? []);
  const studentsById = computed(() => buildStudentMap(students.value));
  const seatsById = computed(() => buildSeatMap(seats.value));
  const fixturesById = computed(() => buildFixtureMap(fixtures.value));
  const groupsById = computed(() => buildGroupMap(options.groups.value));

  const groupAssignments = computed<GroupAssignment[]>(() => {
    return Object.entries(options.groupAssignmentsByStudentId.value)
      .filter(hasAssignedTarget)
      .map(([studentId, groupId]) => ({ student_id: studentId, group_id: groupId }));
  });

  const seatAssignments = computed<SeatAssignment[]>(() => {
    return Object.entries(options.seatAssignmentsByStudentId.value)
      .filter(hasAssignedTarget)
      .map(([studentId, seatId]) => ({ student_id: studentId, seat_id: seatId }));
  });

  const ungroupedStudents = computed<Student[]>(() => {
    return students.value.filter((student) => !options.groupAssignmentsByStudentId.value[student.id]);
  });

  const unseatedStudents = computed<Student[]>(() => {
    return students.value.filter((student) => !options.seatAssignmentsByStudentId.value[student.id]);
  });

  const studentsByGroupId = computed<Record<string, Student[]>>(() => {
    const grouped: Record<string, Student[]> = {};
    for (const group of options.groups.value) {
      grouped[group.id] = [];
    }
    for (const student of students.value) {
      const groupId = options.groupAssignmentsByStudentId.value[student.id];
      if (groupId && grouped[groupId]) {
        grouped[groupId].push(student);
      }
    }
    return grouped;
  });

  const studentBySeatId = computed<Record<string, Student | null>>(() => {
    const placed: Record<string, Student | null> = {};
    for (const seat of seats.value) {
      placed[seat.id] = null;
    }
    for (const student of students.value) {
      const seatId = options.seatAssignmentsByStudentId.value[student.id];
      if (seatId && placed[seatId] !== undefined) {
        placed[seatId] = student;
      }
    }
    return placed;
  });

  const zones = computed(() => {
    return Array.from(
      new Set(
        seats.value
          .map((seat) => seat.zone ?? null)
          .filter((zone): zone is string => typeof zone === "string" && zone.length > 0),
      ),
    ).sort();
  });

  return {
    students,
    seats,
    fixtures,
    studentsById,
    seatsById,
    fixturesById,
    groupsById,
    groupAssignments,
    seatAssignments,
    ungroupedStudents,
    unseatedStudents,
    studentsByGroupId,
    studentBySeatId,
    zones,
  };
}
