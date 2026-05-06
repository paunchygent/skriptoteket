/**
 * Classroom planner Smart default and opt-out copy.
 *
 * Purpose:
 *   Keeps Smart, history, and grouping seating-influence opt-out defaults plus
 *   teacher-facing feedback consistent between authenticated and public
 *   planner workspaces.
 *
 * Relationships:
 *   - read by planner draft persistence, Smart run routing, and workspace
 *     toolbar controls
 *   - mirrors the backend draft default without coupling the UI to API
 *     implementation details
 */

import type { PlanDraft } from "./classroomPlannerTypes";

export const SMART_DISABLED_NOTICE =
  "Smart är avstängt. När du slumpar tas ingen hänsyn till regler, fasta platser, nära läraren eller ihop/isär.";

export function isSmartEnabledByDefault(
  draft: Pick<PlanDraft, "smart_enabled"> | null | undefined,
): boolean {
  return draft?.smart_enabled ?? true;
}

export function isHistoryEnabledByDefault(
  draft: Pick<PlanDraft, "use_history"> | null | undefined,
): boolean {
  return draft?.use_history ?? true;
}

export function isGroupingSeatingDistanceEnabledByDefault(
  draft: Pick<PlanDraft, "grouping_seating_distance_enabled"> | null | undefined,
): boolean {
  return draft?.grouping_seating_distance_enabled ?? true;
}
