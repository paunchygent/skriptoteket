/**
 * Classroom planner fixed-seat rule actions.
 *
 * Purpose:
 *   Own fixed-seat rule authoring mutations for the seating rules workspace.
 *
 * Relationships:
 *   - consumed by `classroomPlannerSmartRuleActions.ts`
 *   - uses `useSmartRuleUiState.ts` pending fixed-seat selections
 *   - persists through the roster smart-rule lane owned by the parent action
 */

import type { ComputedRef, Ref } from "vue";

import type { FixedSeatRule, RoomTemplate } from "./classroomPlannerTypes";
import type { useSmartRuleUiState } from "./useSmartRuleUiState";

type SmartRuleUiState = ReturnType<typeof useSmartRuleUiState>;

type CreateClassroomPlannerFixedSeatRuleActionsOptions = {
  template: Ref<RoomTemplate | null>;
  fixedSeatRules: Ref<FixedSeatRule[]>;
  studentsById: ComputedRef<Record<string, { id: string }>>;
  seatsById: ComputedRef<Record<string, { id: string }>>;
  isWorkspaceBusy: ComputedRef<boolean>;
  canEditSeatingSmartRules: ComputedRef<boolean>;
  smartRuleUiState: SmartRuleUiState;
  markSmartRuleMutationDirty: () => void;
};

function createFixedSeatRuleId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `fixed-seat-rule-${Date.now()}`;
}

export function createClassroomPlannerFixedSeatRuleActions(
  options: CreateClassroomPlannerFixedSeatRuleActionsOptions,
) {
  function fixedSeatRuleMatchesActiveTemplate(rule: FixedSeatRule): boolean {
    return options.template.value !== null && rule.template_id === options.template.value.id;
  }

  function fixedSeatRuleForStudent(studentId: string): FixedSeatRule | null {
    return options.fixedSeatRules.value.find((rule) => {
      return fixedSeatRuleMatchesActiveTemplate(rule) && rule.student_id === studentId;
    }) ?? null;
  }

  function fixedSeatRuleForSeat(seatId: string): FixedSeatRule | null {
    return options.fixedSeatRules.value.find((rule) => {
      return fixedSeatRuleMatchesActiveTemplate(rule) && rule.seat_id === seatId;
    }) ?? null;
  }

  function beginFixedSeatRuleEdit(ruleId: string): void {
    if (!options.canEditSeatingSmartRules.value) {
      return;
    }
    const rule = options.fixedSeatRules.value.find((candidate) => candidate.id === ruleId);
    if (!rule) {
      return;
    }
    options.smartRuleUiState.beginFixedSeatEdit(rule.id, rule.student_id, rule.seat_id);
  }

  function deleteFixedSeatRule(ruleId: string): void {
    if (!options.canEditSeatingSmartRules.value) {
      return;
    }
    const nextRules = options.fixedSeatRules.value.filter((rule) => rule.id !== ruleId);
    if (nextRules.length === options.fixedSeatRules.value.length) {
      return;
    }
    options.fixedSeatRules.value = nextRules;
    if (options.smartRuleUiState.editingFixedSeatRuleId.value === ruleId) {
      options.smartRuleUiState.clearPendingRelationshipSelection();
    } else {
      options.smartRuleUiState.clearFeedback();
    }
    options.markSmartRuleMutationDirty();
  }

  function selectFixedSeatRuleSeat(seatId: string): boolean {
    if (
      options.smartRuleUiState.activeSeatingSmartTool.value !== "fixed_seat"
      || !options.canEditSeatingSmartRules.value
      || options.isWorkspaceBusy.value
      || !options.template.value
      || !options.seatsById.value[seatId]
    ) {
      return false;
    }
    options.smartRuleUiState.togglePendingFixedSeatSeat(seatId);
    return true;
  }

  function commitPendingFixedSeatRule(): boolean {
    if (
      options.smartRuleUiState.activeSeatingSmartTool.value !== "fixed_seat"
      || !options.canEditSeatingSmartRules.value
      || options.isWorkspaceBusy.value
      || !options.template.value
    ) {
      return false;
    }
    const studentId = options.smartRuleUiState.pendingFixedSeatStudentId.value;
    if (!studentId || !options.studentsById.value[studentId]) {
      options.smartRuleUiState.setFeedbackMessage("Välj en elev först.");
      return false;
    }
    const seatId = options.smartRuleUiState.pendingFixedSeatSeatId.value;
    if (!seatId || !options.seatsById.value[seatId]) {
      options.smartRuleUiState.setFeedbackMessage("Välj en plats först.");
      return false;
    }

    const editingRuleId = options.smartRuleUiState.editingFixedSeatRuleId.value;
    const conflictingSeatRule = fixedSeatRuleForSeat(seatId);
    if (conflictingSeatRule && conflictingSeatRule.id !== editingRuleId) {
      options.smartRuleUiState.setFeedbackMessage("Platsen är redan låst. Välj en annan plats.");
      return false;
    }

    const existingStudentRule = fixedSeatRuleForStudent(studentId);
    const ruleId = editingRuleId ?? existingStudentRule?.id ?? createFixedSeatRuleId();
    const nextRule: FixedSeatRule = {
      id: ruleId,
      template_id: options.template.value.id,
      student_id: studentId,
      seat_id: seatId,
    };
    const replacedRuleIds = new Set([ruleId, existingStudentRule?.id].filter(Boolean));
    options.fixedSeatRules.value = [
      ...options.fixedSeatRules.value.filter((rule) => !replacedRuleIds.has(rule.id)),
      nextRule,
    ];
    options.smartRuleUiState.clearPendingRelationshipSelection();
    options.markSmartRuleMutationDirty();
    return true;
  }

  function handleFixedSeatStudentSelection(studentId: string): boolean {
    const existingRule = fixedSeatRuleForStudent(studentId);
    if (options.smartRuleUiState.pendingFixedSeatStudentId.value === studentId) {
      options.smartRuleUiState.togglePendingFixedSeatStudent(studentId);
      return true;
    }
    if (existingRule) {
      options.smartRuleUiState.beginFixedSeatEdit(
        existingRule.id,
        existingRule.student_id,
        existingRule.seat_id,
      );
      return true;
    }
    options.smartRuleUiState.togglePendingFixedSeatStudent(studentId);
    return true;
  }

  return {
    beginFixedSeatRuleEdit,
    deleteFixedSeatRule,
    selectFixedSeatRuleSeat,
    commitPendingFixedSeatRule,
    handleFixedSeatStudentSelection,
    fixedSeatRuleForStudent,
    fixedSeatRuleForSeat,
  };
}
