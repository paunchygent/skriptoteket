/**
 * Classroom planner status derivation.
 *
 * Purpose:
 *   Derive teacher-facing planner status labels, tones, and messages from the
 *   independent draft and roster smart-rule lanes. This keeps shell status
 *   presentation separate from planner orchestration.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts`
 *   - reads lane-local save/hydration state without becoming a persistence
 *     source of truth
 */

import { computed, type ComputedRef, type Ref } from "vue";

import type { SaveStatus } from "./classroomPlannerTypes";
import type { SmartRuleHydrationStatus } from "./useRosterSmartRuleLane";

export type PlannerStatusTone = "neutral" | "success" | "warning" | "danger";

type CreatePlannerStatusModelOptions = {
  draftPersistenceStatus: Ref<SaveStatus>;
  draftPersistenceMessage: Ref<string | null>;
  draftIsSaving: ComputedRef<boolean>;
  smartRulePersistenceStatus: Ref<SaveStatus>;
  smartRulePersistenceMessage: Ref<string | null>;
  smartRuleHydrationStatus: Ref<SmartRuleHydrationStatus>;
  smartRuleHydrationMessage: Ref<string | null>;
  smartRuleIsSaving: ComputedRef<boolean>;
  hasPendingAutosave: ComputedRef<boolean>;
  isWorkspaceBusy: ComputedRef<boolean>;
};

export function createPlannerStatusModel(options: CreatePlannerStatusModelOptions) {
  const plannerConflictMessage = computed(() => {
    if (options.draftPersistenceStatus.value === "conflict") {
      return options.draftPersistenceMessage.value;
    }
    if (options.smartRulePersistenceStatus.value === "conflict") {
      return options.smartRulePersistenceMessage.value;
    }
    return null;
  });

  const plannerStatusLabel = computed(() => {
    if (plannerConflictMessage.value) {
      return "Konflikt";
    }
    if (
      options.draftPersistenceStatus.value === "error"
      || options.smartRulePersistenceStatus.value === "error"
    ) {
      return "Inte sparad";
    }
    if (options.smartRuleHydrationStatus.value === "error") {
      return "Smarta regler otillgängliga";
    }
    if (
      options.draftIsSaving.value
      || options.smartRuleIsSaving.value
      || options.hasPendingAutosave.value
    ) {
      return "Sparar";
    }
    if (options.isWorkspaceBusy.value) {
      return "Arbetar";
    }
    if (
      options.draftPersistenceStatus.value === "saved"
      || options.smartRulePersistenceStatus.value === "saved"
    ) {
      return "Sparad";
    }
    return "Ingen ändring";
  });

  const plannerStatusTone = computed<PlannerStatusTone>(() => {
    if (
      plannerConflictMessage.value
      || options.draftPersistenceStatus.value === "error"
      || options.smartRulePersistenceStatus.value === "error"
    ) {
      return "danger";
    }
    if (options.smartRuleHydrationStatus.value === "error") {
      return "warning";
    }
    if (
      options.draftIsSaving.value
      || options.smartRuleIsSaving.value
      || options.hasPendingAutosave.value
      || options.isWorkspaceBusy.value
    ) {
      return "warning";
    }
    if (
      options.draftPersistenceStatus.value === "saved"
      || options.smartRulePersistenceStatus.value === "saved"
    ) {
      return "success";
    }
    return "neutral";
  });

  const plannerStatusMessage = computed(() => {
    if (plannerConflictMessage.value) {
      return plannerConflictMessage.value;
    }
    if (options.draftPersistenceStatus.value === "error") {
      return options.draftPersistenceMessage.value;
    }
    if (options.smartRulePersistenceStatus.value === "error") {
      return options.smartRulePersistenceMessage.value;
    }
    if (options.smartRuleHydrationStatus.value === "error") {
      return options.smartRuleHydrationMessage.value;
    }
    return null;
  });

  return {
    plannerConflictMessage,
    plannerStatusLabel,
    plannerStatusTone,
    plannerStatusMessage,
  };
}
