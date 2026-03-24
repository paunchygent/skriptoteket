/**
 * Classroom planner route-shell save guards.
 *
 * These helpers normalize the repeated "flush pending save, inspect the save
 * state, then continue or block" workflow used when Klassrumskartan switches
 * between overview, grouping, seating, and exit flows.
 */

import type { PlanDraft, SaveStatus } from "./classroomPlannerTypes";

export type PlannerRouteShellSaveController = {
  draft: PlanDraft | null;
  saveMessage: string | null;
  saveStatus: SaveStatus;
  flushPendingSave: () => Promise<boolean>;
};

export type PlannerRouteShellBlockedSaveMessages = {
  conflictMessage: string;
  fallbackMessage: string;
};

export type PlannerRouteShellSaveOutcome =
  | { status: "saved"; message: null }
  | { status: "blocked"; message: string };

function isBlockedSaveStatus(saveStatus: SaveStatus): boolean {
  return saveStatus === "conflict" || saveStatus === "error";
}

export async function flushPlannerRouteShellSave(
  plannerState: PlannerRouteShellSaveController,
  messages: PlannerRouteShellBlockedSaveMessages,
): Promise<PlannerRouteShellSaveOutcome> {
  await plannerState.flushPendingSave();
  if (!isBlockedSaveStatus(plannerState.saveStatus)) {
    return { status: "saved", message: null };
  }

  return {
    status: "blocked",
    message:
      plannerState.saveStatus === "conflict"
        ? messages.conflictMessage
        : plannerState.saveMessage ?? messages.fallbackMessage,
  };
}

export async function flushPlannerRouteShellSaveForExit(
  plannerState: PlannerRouteShellSaveController,
  timeoutMs: number,
): Promise<"saved" | "blocked" | "timed-out"> {
  if (!plannerState.draft) {
    return "saved";
  }

  return await Promise.race<"saved" | "blocked" | "timed-out">([
    plannerState.flushPendingSave().then((flushSucceeded) => (flushSucceeded ? "saved" : "blocked")),
    new Promise<"timed-out">((resolve) => {
      window.setTimeout(() => resolve("timed-out"), timeoutMs);
    }),
  ]);
}
