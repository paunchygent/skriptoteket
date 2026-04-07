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
  onDraftMutation?: () => void;
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
  function setDraftBooleanFlag(
    key: "smart_enabled" | "use_history" | "grouping_seating_distance_enabled",
    enabled: boolean,
  ): void {
    if (!options.draft.value || options.isWorkspaceBusy.value) {
      return;
    }
    if ((options.draft.value[key] ?? false) === enabled) {
      return;
    }
    options.draft.value = {
      ...options.draft.value,
      [key]: enabled,
    };
    options.syncVisibleSessionBindings();
    options.onDraftMutation?.();
    options.draftLane.markDirty();
  }

  function setDraftSmartEnabled(enabled: boolean): void {
    setDraftBooleanFlag("smart_enabled", enabled);
  }

  function setDraftUseHistoryEnabled(enabled: boolean): void {
    setDraftBooleanFlag("use_history", enabled);
  }

  function setDraftGroupingSeatingDistanceEnabled(enabled: boolean): void {
    setDraftBooleanFlag("grouping_seating_distance_enabled", enabled);
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

  function setStudentNearTeacherEnabled(studentId: string, enabled: boolean): boolean {
    if (
      !options.canEditSeatingSmartRules.value
      || !options.studentsById.value[studentId]
      || options.isWorkspaceBusy.value
    ) {
      return false;
    }

    if (isStudentMarkedNearTeacher(studentId) === enabled) {
      return false;
    }

    updateSeatingPreference(studentId, enabled);
    return true;
  }

  function replaceNearTeacherPreference(previousStudentId: string, nextStudentId: string): boolean {
    if (
      !options.canEditSeatingSmartRules.value
      || options.isWorkspaceBusy.value
      || !options.studentsById.value[previousStudentId]
      || !options.studentsById.value[nextStudentId]
    ) {
      return false;
    }

    if (previousStudentId === nextStudentId) {
      return false;
    }

    if (!isStudentMarkedNearTeacher(previousStudentId) || isStudentMarkedNearTeacher(nextStudentId)) {
      return false;
    }

    let replaced = false;
    options.seatingPreferences.value = options.seatingPreferences.value.map((preference) => {
      if (preference.student_id !== previousStudentId) {
        return preference;
      }
      replaced = true;
      return {
        student_id: nextStudentId,
        near_teacher: true,
      };
    });

    if (!replaced) {
      return false;
    }

    options.syncVisibleSessionBindings();
    options.smartRuleLane.markDirty();
    options.smartRuleUiState.clearFeedback();
    return true;
  }

  function commitPendingRelationshipRule(): boolean {
    const activeTool = options.smartRuleUiState.activeSeatingSmartTool.value;
    if (
      activeTool !== "near_teacher"
      && activeTool !== "keep_near"
      && activeTool !== "keep_apart"
    ) {
      return false;
    }
    if (
      !options.smartRuleUiState.canCommitPendingRelationshipRule.value
      || !options.canEditSeatingSmartRules.value
    ) {
      return false;
    }

    if (activeTool === "near_teacher") {
      options.seatingPreferences.value = options.smartRuleUiState.pendingRelationshipStudentIds.value
        .map((studentId) => {
          if (!options.studentsById.value[studentId]) {
            return null;
          }
          return {
            student_id: studentId,
            near_teacher: true,
          };
        })
        .filter((preference): preference is StudentSeatingPreference => preference !== null);
      options.smartRuleUiState.clearPendingRelationshipSelection();
      options.syncVisibleSessionBindings();
      options.smartRuleLane.markDirty();
      return true;
    }

    const editingRuleId = options.smartRuleUiState.editingRelationshipRuleId.value;
    const overlappingStudentIds = new Set(
      options.relationshipRules.value.flatMap((rule) =>
        rule.id === editingRuleId
          ? []
          : rule.student_ids.filter((studentId) =>
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

    if (editingRuleId) {
      const editedRuleFound = options.relationshipRules.value.some((rule) => rule.id === editingRuleId);
      if (!editedRuleFound) {
        return false;
      }

      options.relationshipRules.value = options.relationshipRules.value.map((rule) => {
        if (rule.id !== editingRuleId) {
          return rule;
        }
        return {
          ...rule,
          kind: activeTool,
          student_ids: [...options.smartRuleUiState.pendingRelationshipStudentIds.value],
        };
      });
      options.smartRuleUiState.clearPendingRelationshipSelection();
      options.syncVisibleSessionBindings();
      options.smartRuleLane.markDirty();
      return true;
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

  function beginRelationshipRuleEdit(ruleId: string): void {
    if (!options.canEditSeatingSmartRules.value) {
      return;
    }
    const rule = options.relationshipRules.value.find((candidate) => candidate.id === ruleId);
    if (!rule) {
      return;
    }
    options.smartRuleUiState.beginRelationshipRuleEdit(rule.id, rule.kind, rule.student_ids);
  }

  function beginNearTeacherEdit(): void {
    if (!options.canEditSeatingSmartRules.value) {
      return;
    }
    const studentIds = options.seatingPreferences.value
      .filter((preference) => preference.near_teacher === true)
      .map((preference) => preference.student_id);
    options.smartRuleUiState.beginNearTeacherEdit(studentIds, studentIds.length > 0);
  }

  function clearNearTeacherRule(): boolean {
    if (
      !options.canEditSeatingSmartRules.value
      || options.isWorkspaceBusy.value
      || options.seatingPreferences.value.length === 0
    ) {
      return false;
    }

    options.seatingPreferences.value = [];
    options.smartRuleUiState.clearFeedback();
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
    if (options.smartRuleUiState.editingRelationshipRuleId.value === ruleId) {
      options.smartRuleUiState.clearPendingRelationshipSelection();
    } else {
      options.smartRuleUiState.clearFeedback();
    }
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

    options.smartRuleUiState.togglePendingRelationshipStudent(studentId);
    return true;
  }

  return {
    setDraftSmartEnabled,
    setDraftUseHistoryEnabled,
    setDraftGroupingSeatingDistanceEnabled,
    isStudentMarkedNearTeacher,
    setStudentNearTeacherEnabled,
    replaceNearTeacherPreference,
    handleSeatingSmartToolStudentSelection,
    commitPendingRelationshipRule,
    beginRelationshipRuleEdit,
    beginNearTeacherEdit,
    clearNearTeacherRule,
    deleteRelationshipRule,
  };
}
