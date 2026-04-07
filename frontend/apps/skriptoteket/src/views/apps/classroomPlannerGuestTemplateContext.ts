/**
 * Guest classroom-selection context helpers for Klassrumskartan.
 *
 * This module owns the one explicit rule for which classroom is currently
 * selected in the public guest workspace so overview state, grouping/seating
 * transitions, and shell affordances stay aligned.
 */

export type GuestPlannerView = "groups" | "seats" | "rules";

export function resolveGuestGroupingTemplateContext(
  selectedTemplateId: string | null,
): string | null {
  return selectedTemplateId;
}

export function resolveGuestWorkspaceTemplateContext(input: {
  currentView: GuestPlannerView;
  selectedTemplateId: string | null;
  plannerTemplateId: string | null;
}): string | null {
  if (input.currentView === "seats") {
    return input.plannerTemplateId ?? input.selectedTemplateId;
  }

  return input.selectedTemplateId;
}
