/**
 * Classroom planner route-shell save guards.
 *
 * These helpers keep the route shell aligned with the explicit planner
 * transition matrix. They ask the store for transition-specific preparation
 * rather than inspecting planner-global save truth.
 */

import type { PlanDraft } from "./classroomPlannerTypes";
import type { PlannerExitResult, PlannerTransitionResult } from "./plannerTransitionPolicies";

export type PlannerRouteShellSaveController = {
  draft: PlanDraft | null;
  prepareForPlannerExit: () => Promise<PlannerExitResult>;
  prepareForWorkspaceSwitch: (messages: PlannerRouteShellBlockedSaveMessages) => Promise<PlannerTransitionResult>;
};

export type PlannerRouteShellBlockedSaveMessages = {
  conflictMessage: string;
  fallbackMessage: string;
};

export type PlannerRouteShellSaveOutcome =
  | { status: "saved"; message: null }
  | { status: "blocked"; message: string };

export async function flushPlannerRouteShellSave(
  plannerState: PlannerRouteShellSaveController,
  messages: PlannerRouteShellBlockedSaveMessages,
): Promise<PlannerRouteShellSaveOutcome> {
  const result = await plannerState.prepareForWorkspaceSwitch(messages);
  if (result.status === "saved") {
    return { status: "saved", message: null };
  }
  return {
    status: "blocked",
    message: result.message,
  };
}

export async function flushPlannerRouteShellSaveForExit(
  plannerState: PlannerRouteShellSaveController,
): Promise<"saved" | "blocked" | "timed-out"> {
  if (!plannerState.draft) {
    return "saved";
  }

  const result = await plannerState.prepareForPlannerExit();
  if (result.status === "saved") {
    return "saved";
  }
  if (result.status === "confirm-discard") {
    return "timed-out";
  }
  return "blocked";
}
