/**
 * Smart-rule UI state.
 *
 * Purpose:
 *   Own the transient teacher-facing smart-rule authoring state for the
 *   seating workspace: active tool, pending relationship selection, and local
 *   feedback. This bucket must reset only from explicit planner transition
 *   policy, never from save or load acknowledgements.
 *
 * Relationships:
 *   - composed by `useClassroomState.ts`
 *   - transition resets are orchestrated by `plannerTransitionPolicies.ts`
 *   - persistence lanes never mutate this bucket directly
 */

import { computed, ref } from "vue";

import type { SeatingSmartTool } from "./classroomPlannerTypes";

type UseSmartRuleUiStateOptions = {
  canEditSmartRules: () => boolean;
};

export function useSmartRuleUiState(options: UseSmartRuleUiStateOptions) {
  const activeSeatingSmartTool = ref<SeatingSmartTool | null>(null);
  const pendingRelationshipStudentIds = ref<string[]>([]);
  const feedbackMessage = ref<string | null>(null);

  const canCommitPendingRelationshipRule = computed(() => {
    return (
      (activeSeatingSmartTool.value === "keep_near" || activeSeatingSmartTool.value === "keep_apart")
      && pendingRelationshipStudentIds.value.length >= 2
      && options.canEditSmartRules()
    );
  });

  function clearFeedback(): void {
    feedbackMessage.value = null;
  }

  function clearPendingRelationshipSelection(): void {
    pendingRelationshipStudentIds.value = [];
    clearFeedback();
  }

  function setFeedbackMessage(message: string | null): void {
    feedbackMessage.value = message;
  }

  function reset(): void {
    activeSeatingSmartTool.value = null;
    clearPendingRelationshipSelection();
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

  return {
    activeSeatingSmartTool,
    pendingRelationshipStudentIds,
    feedbackMessage,
    canCommitPendingRelationshipRule,
    clearFeedback,
    clearPendingRelationshipSelection,
    setFeedbackMessage,
    reset,
    setActiveSeatingSmartTool,
    isStudentInPendingRelationshipSelection,
    togglePendingRelationshipStudent,
  };
}
