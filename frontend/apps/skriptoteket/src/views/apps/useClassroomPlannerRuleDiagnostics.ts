/**
 * Classroom planner rule diagnostics state.
 *
 * Purpose:
 *   Own the transient solver-diagnostic marker payload separately from the
 *   planner session stores so local draft and smart-rule mutations can share
 *   one explicit invalidation contract.
 *
 * Relationships:
 *   - consumed by authenticated and guest classroom planner state adapters
 *   - populated by Smart seating run helpers
 *   - cleared by local draft, template, roster, and smart-rule mutations
 */

import { ref } from "vue";

import type { SmartRuleDiagnostic } from "./classroomPlannerTypes";

export function useClassroomPlannerRuleDiagnostics() {
  const smartRuleDiagnostics = ref<SmartRuleDiagnostic[]>([]);

  function applyRuleDiagnostics(diagnostics: SmartRuleDiagnostic[]): void {
    smartRuleDiagnostics.value = diagnostics;
  }

  function clearRuleDiagnostics(): void {
    smartRuleDiagnostics.value = [];
  }

  return {
    smartRuleDiagnostics,
    applyRuleDiagnostics,
    clearRuleDiagnostics,
  };
}
