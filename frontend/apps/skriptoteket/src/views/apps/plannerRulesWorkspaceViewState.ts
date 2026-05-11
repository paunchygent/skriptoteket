/**
 * Rules workspace derived view state.
 *
 * Purpose:
 *   Builds the read-only rule and selection projections consumed by the
 *   `Regler` workspace shell without letting the shell own planner model logic.
 *
 * Relationships:
 *   - consumed by `PlannerRulesWorkspacePane.vue`
 *   - reuses smart-rule presentation helpers for rule markers and seat labels
 *   - reads state from `useClassroomState()` without mutating planner data
 */

import { computed } from "vue";

import type { Student } from "./classroomPlannerTypes";
import {
  buildSmartRuleMarkersByStudentId,
  formatSeatDisplayLabel,
} from "./classroomPlannerSmartRulePresentation";
import type { useClassroomState } from "./useClassroomState";

type ClassroomPlannerState = ReturnType<typeof useClassroomState>;

export function usePlannerRulesWorkspaceViewState(plannerState: ClassroomPlannerState) {
  const nearTeacherStudents = computed<Student[]>(() => {
    return plannerState.seatingPreferences
      .filter((preference) => preference.near_teacher === true)
      .map((preference) => plannerState.studentsById[preference.student_id] ?? null)
      .filter((student): student is Student => student !== null);
  });
  const activeFixedSeatRules = computed(() => {
    const templateId = plannerState.template?.id ?? null;
    if (!templateId) {
      return [];
    }
    return plannerState.fixedSeatRules.filter((rule) => rule.template_id === templateId);
  });
  const smartRuleMarkersByStudentId = computed(() => {
    return buildSmartRuleMarkersByStudentId(
      plannerState.seatingPreferences,
      plannerState.relationshipRules,
      activeFixedSeatRules.value,
    );
  });
  const pendingFixedSeatStudentName = computed(() => {
    const studentId = plannerState.pendingFixedSeatStudentId;
    if (!studentId) {
      return null;
    }
    return plannerState.studentsById[studentId]?.display_name ?? null;
  });
  const pendingFixedSeatSeatLabel = computed(() => {
    const seatId = plannerState.pendingFixedSeatSeatId;
    return seatId ? formatSeatDisplayLabel(seatId) : null;
  });
  const pendingSelectionCount = computed(() => {
    if (plannerState.activeSeatingSmartTool === "fixed_seat") {
      return Number(plannerState.pendingFixedSeatStudentId !== null)
        + Number(plannerState.pendingFixedSeatSeatId !== null);
    }
    return plannerState.pendingRelationshipStudentIds.length;
  });
  const pendingRuleStudents = computed(() => {
    return plannerState.pendingRelationshipStudentIds
      .map((studentId) => {
        const student = plannerState.studentsById[studentId];
        if (!student) {
          return null;
        }
        return { id: student.id, name: student.display_name };
      })
      .filter((student): student is { id: string; name: string } => student !== null);
  });
  const phoneStudentCountLabel = computed(() => {
    const count = plannerState.students.length;
    return count === 1 ? "1 elev" : `${count} elever`;
  });
  const phoneCanCommitRelationshipRule = computed(() => {
    return (
      plannerState.activeSeatingSmartTool !== "fixed_seat"
      && plannerState.activeSeatingSmartTool !== null
    );
  });
  const canUseClassroomView = computed(() => plannerState.template !== null);
  const seatingArrangementUnavailableMessage = computed(() => {
    if (plannerState.template === null) {
      return "Klassrumsvyn blir tillgänglig när klassen har ett klassrum.";
    }
    return null;
  });
  const phoneSelectedStudentIds = computed(() => {
    if (plannerState.activeSeatingSmartTool === "fixed_seat") {
      return plannerState.pendingFixedSeatStudentId ? [plannerState.pendingFixedSeatStudentId] : [];
    }
    return plannerState.pendingRelationshipStudentIds;
  });

  return {
    activeFixedSeatRules,
    canUseClassroomView,
    nearTeacherStudents,
    pendingFixedSeatSeatLabel,
    pendingFixedSeatStudentName,
    pendingRuleStudents,
    pendingSelectionCount,
    phoneCanCommitRelationshipRule,
    phoneSelectedStudentIds,
    phoneStudentCountLabel,
    seatingArrangementUnavailableMessage,
    smartRuleMarkersByStudentId,
  };
}
