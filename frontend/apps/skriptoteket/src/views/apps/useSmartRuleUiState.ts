/**
 * Smart-rule UI state.
 *
 * Purpose:
 *   Keeps transient rule authoring selections for the seating workspace:
 *   active tool, pending students, pending fixed-seat binding, and local
 *   feedback. Planner transition policies decide when this state resets.
 *
 * Relationships:
 *   - composed by `useClassroomState.ts`
 *   - transition resets run through `plannerTransitionPolicies.ts`
 *   - persistence lanes read this state through smart-rule actions
 */

import { computed, ref } from "vue";

import type { SeatingSmartTool } from "./classroomPlannerTypes";

type UseSmartRuleUiStateOptions = {
  canEditSmartRules: () => boolean;
};

export function useSmartRuleUiState(options: UseSmartRuleUiStateOptions) {
  const activeSeatingSmartTool = ref<SeatingSmartTool | null>(null);
  const pendingRelationshipStudentIds = ref<string[]>([]);
  const pendingFixedSeatStudentId = ref<string | null>(null);
  const pendingFixedSeatSeatId = ref<string | null>(null);
  const editingFixedSeatRuleId = ref<string | null>(null);
  const editingRelationshipRuleId = ref<string | null>(null);
  const editingNearTeacherRule = ref(false);
  const feedbackMessage = ref<string | null>(null);

  const canCommitPendingRelationshipRule = computed(() => {
    if (!options.canEditSmartRules()) {
      return false;
    }
    if (activeSeatingSmartTool.value === "near_teacher") {
      return pendingRelationshipStudentIds.value.length >= 1;
    }
    return (
      (activeSeatingSmartTool.value === "keep_near" || activeSeatingSmartTool.value === "keep_apart")
      && pendingRelationshipStudentIds.value.length >= 2
    );
  });
  const canCommitPendingFixedSeatRule = computed(() => {
    return (
      options.canEditSmartRules()
      && activeSeatingSmartTool.value === "fixed_seat"
      && pendingFixedSeatStudentId.value !== null
      && pendingFixedSeatSeatId.value !== null
    );
  });

  function clearFeedback(): void {
    feedbackMessage.value = null;
  }

  function clearPendingRelationshipSelection(): void {
    pendingRelationshipStudentIds.value = [];
    pendingFixedSeatStudentId.value = null;
    pendingFixedSeatSeatId.value = null;
    editingFixedSeatRuleId.value = null;
    editingRelationshipRuleId.value = null;
    editingNearTeacherRule.value = false;
    clearFeedback();
  }

  function setFeedbackMessage(message: string | null): void {
    feedbackMessage.value = message;
  }

  function reset(): void {
    activeSeatingSmartTool.value = null;
    clearPendingRelationshipSelection();
  }

  function beginRelationshipRuleEdit(
    ruleId: string,
    tool: Extract<SeatingSmartTool, "keep_near" | "keep_apart">,
    studentIds: readonly string[],
  ): void {
    if (!options.canEditSmartRules()) {
      return;
    }
    activeSeatingSmartTool.value = tool;
    pendingRelationshipStudentIds.value = [...studentIds];
    editingRelationshipRuleId.value = ruleId;
    editingNearTeacherRule.value = false;
    clearFeedback();
  }

  function beginNearTeacherEdit(studentIds: readonly string[], existingRule = true): void {
    if (!options.canEditSmartRules()) {
      return;
    }
    activeSeatingSmartTool.value = "near_teacher";
    pendingRelationshipStudentIds.value = [...studentIds];
    editingRelationshipRuleId.value = null;
    editingNearTeacherRule.value = existingRule;
    clearFeedback();
  }

  function beginFixedSeatEdit(ruleId: string | null, studentId: string, seatId: string | null): void {
    if (!options.canEditSmartRules()) {
      return;
    }
    activeSeatingSmartTool.value = "fixed_seat";
    pendingRelationshipStudentIds.value = [];
    pendingFixedSeatStudentId.value = studentId;
    pendingFixedSeatSeatId.value = seatId;
    editingFixedSeatRuleId.value = ruleId;
    editingRelationshipRuleId.value = null;
    editingNearTeacherRule.value = false;
    clearFeedback();
  }

  function setActiveSeatingSmartTool(tool: SeatingSmartTool | null): void {
    if (tool !== null && !options.canEditSmartRules()) {
      return;
    }
    if (activeSeatingSmartTool.value === tool) {
      activeSeatingSmartTool.value = null;
      clearPendingRelationshipSelection();
      return;
    }
    activeSeatingSmartTool.value = tool;
    clearPendingRelationshipSelection();
  }

  function isStudentInPendingRelationshipSelection(studentId: string): boolean {
    return pendingRelationshipStudentIds.value.includes(studentId);
  }

  function togglePendingRelationshipStudent(studentId: string): void {
    if (isStudentInPendingRelationshipSelection(studentId)) {
      pendingRelationshipStudentIds.value = pendingRelationshipStudentIds.value.filter(
        (pendingStudentId) => pendingStudentId !== studentId,
      );
    } else {
      pendingRelationshipStudentIds.value = [...pendingRelationshipStudentIds.value, studentId];
    }
    clearFeedback();
  }

  function setPendingFixedSeatStudent(studentId: string): void {
    pendingRelationshipStudentIds.value = [];
    pendingFixedSeatStudentId.value = studentId;
    editingRelationshipRuleId.value = null;
    editingNearTeacherRule.value = false;
    clearFeedback();
  }

  function togglePendingFixedSeatStudent(studentId: string): void {
    pendingRelationshipStudentIds.value = [];
    pendingFixedSeatStudentId.value = pendingFixedSeatStudentId.value === studentId ? null : studentId;
    editingRelationshipRuleId.value = null;
    editingNearTeacherRule.value = false;
    clearFeedback();
  }

  function togglePendingFixedSeatSeat(seatId: string): void {
    pendingRelationshipStudentIds.value = [];
    pendingFixedSeatSeatId.value = pendingFixedSeatSeatId.value === seatId ? null : seatId;
    editingRelationshipRuleId.value = null;
    editingNearTeacherRule.value = false;
    clearFeedback();
  }

  return {
    activeSeatingSmartTool,
    pendingRelationshipStudentIds,
    pendingFixedSeatStudentId,
    pendingFixedSeatSeatId,
    editingFixedSeatRuleId,
    editingRelationshipRuleId,
    editingNearTeacherRule,
    feedbackMessage,
    canCommitPendingRelationshipRule,
    canCommitPendingFixedSeatRule,
    clearFeedback,
    clearPendingRelationshipSelection,
    setFeedbackMessage,
    reset,
    beginRelationshipRuleEdit,
    beginNearTeacherEdit,
    beginFixedSeatEdit,
    setActiveSeatingSmartTool,
    isStudentInPendingRelationshipSelection,
    togglePendingRelationshipStudent,
    setPendingFixedSeatStudent,
    togglePendingFixedSeatStudent,
    togglePendingFixedSeatSeat,
  };
}
