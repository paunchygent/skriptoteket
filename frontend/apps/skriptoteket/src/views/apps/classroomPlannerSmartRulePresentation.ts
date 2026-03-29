/**
 * Smart-rule presentation helpers.
 *
 * Purpose:
 *   Keep rule labels, marker badges, and stable classroom ordering consistent
 *   across the dedicated rules workspace and the compact smart summaries.
 *
 * Relationships:
 *   - consumed by rules workspace components and task-pane summary strips
 *   - reads planner smart-rule collections without mutating planner state
 */

import type {
  RelationshipRule,
  Seat,
  Student,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";

export function formatRelationshipRuleHeading(
  rule: Pick<RelationshipRule, "kind">,
  index: number,
): string {
  const suffix = String.fromCharCode(65 + index);
  return `${rule.kind === "keep_apart" ? "Håll isär" : "Håll nära"} ${suffix}`;
}

export function buildSmartRuleMarkersByStudentId(
  seatingPreferences: readonly StudentSeatingPreference[],
  relationshipRules: readonly RelationshipRule[],
): Record<string, string[]> {
  const markers: Record<string, string[]> = {};

  for (const preference of seatingPreferences) {
    if (preference.near_teacher !== true) {
      continue;
    }
    markers[preference.student_id] = [...(markers[preference.student_id] ?? []), "Nära läraren"];
  }

  relationshipRules.forEach((rule, index) => {
    const marker = `${rule.kind === "keep_apart" ? "Isär" : "Nära"} ${String.fromCharCode(65 + index)}`;
    for (const studentId of rule.student_ids) {
      markers[studentId] = [...(markers[studentId] ?? []), marker];
    }
  });

  return markers;
}

export function resolveStudentNames(
  studentIds: readonly string[],
  studentsById: Readonly<Record<string, Student | undefined>>,
): string[] {
  return studentIds
    .map((studentId) => studentsById[studentId]?.display_name ?? null)
    .filter((displayName): displayName is string => displayName !== null);
}

export function sortStudentsAlphabetically(students: readonly Student[]): Student[] {
  return [...students].sort((left, right) => {
    return left.display_name.localeCompare(right.display_name, "sv");
  });
}

export function sortSeatsByReadingOrder(seats: readonly Seat[]): Seat[] {
  return [...seats].sort((left, right) => {
    return left.y - right.y || left.x - right.x || left.id.localeCompare(right.id);
  });
}
