/**
 * Workspace draft and template resolution for Klassrumskartan.
 *
 * Route-shell workspace actions use these helpers to choose the active draft
 * and classroom template when moving between overview, grouping, seating, and
 * rules modes.
 */

import type { ClassWorkspaceSummary, PlanDraftSummary } from "./classroomPlannerTypes";

export function activeDraftId(
  summary: ClassWorkspaceSummary | null,
  draftKind: "grouping" | "seating",
): string | null {
  const draft: PlanDraftSummary | null =
    draftKind === "grouping"
      ? (summary?.active_grouping_draft ?? null)
      : (summary?.active_seating_draft ?? null);
  return draft?.id ?? null;
}

export function resolveRulesWorkspaceTemplateId(options: {
  bootstrapsSeatingHost: boolean;
  plannerTemplateId: string | null;
  activeSeatingTemplateId: string | null;
  selectedWorkspaceTemplateId: string | null;
}): string | null {
  if (options.bootstrapsSeatingHost) {
    return (
      options.selectedWorkspaceTemplateId
      ?? options.plannerTemplateId
      ?? options.activeSeatingTemplateId
      ?? null
    );
  }

  return (
    options.plannerTemplateId
    ?? options.activeSeatingTemplateId
    ?? options.selectedWorkspaceTemplateId
    ?? null
  );
}

export function resolveSeatingWorkspaceTemplateId(options: {
  plannerTemplateId: string | null;
  activeSeatingTemplateId: string | null;
  selectedWorkspaceTemplateId: string | null;
}): string | null {
  return (
    options.plannerTemplateId
    ?? options.activeSeatingTemplateId
    ?? options.selectedWorkspaceTemplateId
    ?? null
  );
}
