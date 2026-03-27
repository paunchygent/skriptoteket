/**
 * Classroom planner smart-rule actions.
 *
 * Purpose:
 *   Own smart seating authoring mutations and draft smart-toggle mutations
 *   without mixing them into workspace loading or route-transition logic.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts`
 *   - mutates roster-global smart-rule state and draft-local smart-enabled
 *     state
 *   - coordinates with `useRosterSmartRuleLane.ts` and
 *     `useSmartRuleUiState.ts`
 */

import type { ComputedRef, Ref } from "vue";

import type {
  PlanDraft,
  RelationshipRule,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import type { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import type { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";
import type { useSmartRuleUiState } from "./useSmartRuleUiState";

type DraftLane = ReturnType<typeof useDraftPersistenceLane>;
type SmartRuleLane = ReturnType<typeof useRosterSmartRuleLane>;
type SmartRuleUiState = ReturnType<typeof useSmartRuleUiState>;

type CreateClassroomPlannerSmartRuleActionsOptions = {
  draft: Ref<PlanDraft | null>;
  seatingPreferences: Ref<StudentSeatingPreference[]>;
  relationshipRules: Ref<RelationshipRule[]>;
  studentsById: ComputedRef<Record<string, { id: string }>>;
  isWorkspaceBusy: ComputedRef<boolean>;
  canEditSeatingSmartRules: ComputedRef<boolean>;
  draftLane: DraftLane;
  smartRuleLane: SmartRuleLane;
  smartRuleUiState: SmartRuleUiState;
  syncVisibleSessionBindings: () => void;
};

function createRelationshipRuleId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `relationship-rule-${Date.now()}`;
}

export function createClassroomPlannerSmartRuleActions(
  options: CreateClassroomPlannerSmartRuleActionsOptions,
) {
  function setDraftSmartEnabled(enabled: boolean): void {
    if (!options.draft.value || options.isWorkspaceBusy.value) {
      return;
    }
    if ((options.draft.value.smart_enabled ?? false) === enabled) {
      return;
    }
    options.draft.value = {
      ...options.draft.value,
      smart_enabled: enabled,
    };
    options.syncVisibleSessionBindings();
    options.draftLane.markDirty();
  }

  function isStudentMarkedNearTeacher(studentId: string): boolean {
    return options.seatingPreferences.value.some(
      (preference) => preference.student_id === studentId && preference.near_teacher === true,
    );
  }

  function updateSeatingPreference(studentId: string, enabled: boolean): void {
    const existingIndex = options.seatingPreferences.value.findIndex(
      (preference) => preference.student_id === studentId,
    );
    if (enabled) {
      if (existingIndex >= 0) {
        return;
      }
      options.seatingPreferences.value = [
        ...options.seatingPreferences.value,
        {
          student_id: studentId,
          near_teacher: true,
        },
      ];
      options.syncVisibleSessionBindings();
      options.smartRuleLane.markDirty();
      options.smartRuleUiState.clearFeedback();
      return;
    }

    if (existingIndex < 0) {
      return;
    }
    options.seatingPreferences.value = options.seatingPreferences.value.filter(
      (preference) => preference.student_id !== studentId,
    );
    options.syncVisibleSessionBindings();
    options.smartRuleLane.markDirty();
    options.smartRuleUiState.clearFeedback();
  }

  function toggleNearTeacherPreference(studentId: string): void {
    updateSeatingPreference(studentId, !isStudentMarkedNearTeacher(studentId));
  }

  function commitPendingRelationshipRule(): boolean {
    const activeTool = options.smartRuleUiState.activeSeatingSmartTool.value;
    if (activeTool !== "keep_near" && activeTool !== "keep_apart") {
      return false;
    }
    if (
      !options.smartRuleUiState.canCommitPendingRelationshipRule.value
      || !options.canEditSeatingSmartRules.value
    ) {
      return false;
    }

    const overlappingStudentIds = new Set(
      options.relationshipRules.value.flatMap((rule) =>
        rule.student_ids.filter((studentId) =>
          options.smartRuleUiState.pendingRelationshipStudentIds.value.includes(studentId),
        ),
      ),
    );
    if (overlappingStudentIds.size > 0) {
      options.smartRuleUiState.setFeedbackMessage(
        "En elev kan bara ingå i en relationsregel åt gången.",
      );
      return false;
    }

    options.relationshipRules.value = [
      ...options.relationshipRules.value,
      {
        id: createRelationshipRuleId(),
        kind: activeTool,
        student_ids: [...options.smartRuleUiState.pendingRelationshipStudentIds.value],
      },
    ];
    options.smartRuleUiState.clearPendingRelationshipSelection();
    options.syncVisibleSessionBindings();
    options.smartRuleLane.markDirty();
    return true;
  }

  function deleteRelationshipRule(ruleId: string): void {
    if (!options.canEditSeatingSmartRules.value) {
      return;
    }
    const nextRules = options.relationshipRules.value.filter((rule) => rule.id !== ruleId);
    if (nextRules.length === options.relationshipRules.value.length) {
      return;
    }
    options.relationshipRules.value = nextRules;
    options.smartRuleUiState.clearFeedback();
    options.syncVisibleSessionBindings();
    options.smartRuleLane.markDirty();
  }

  function handleSeatingSmartToolStudentSelection(studentId: string): boolean {
    if (
      !options.studentsById.value[studentId]
      || !options.smartRuleUiState.activeSeatingSmartTool.value
      || options.isWorkspaceBusy.value
    ) {
      return false;
    }

    if (options.smartRuleUiState.activeSeatingSmartTool.value === "near_teacher") {
      toggleNearTeacherPreference(studentId);
      return true;
    }

    options.smartRuleUiState.togglePendingRelationshipStudent(studentId);
    return true;
  }

  return {
    setDraftSmartEnabled,
    isStudentMarkedNearTeacher,
    handleSeatingSmartToolStudentSelection,
    commitPendingRelationshipRule,
    deleteRelationshipRule,
  };
}
