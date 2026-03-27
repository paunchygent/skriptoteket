/**
 * Planner transition policies.
 *
 * Purpose:
 *   Centralize the explicit transition matrix for Klassrumskartan. These
 *   policies decide which lane may flush, which lane must not flush, when a
 *   timeout becomes confirm-discard, and how teardown discards pending work.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts` for history and abandon semantics
 *   - consumed by route-shell helpers for workspace and exit orchestration
 *   - depends on the draft and smart-rule lanes instead of planner-global
 *     save truth
 */

import type { PlanDraft } from "./classroomPlannerTypes";

type LaneBlockedReason = "conflict" | "error";

type LaneResult =
  | { status: "saved" }
  | { status: "blocked"; reason: LaneBlockedReason; message: string };

export type PlannerTransitionResult =
  | { status: "saved"; message: null }
  | { status: "blocked"; reason: LaneBlockedReason; message: string };

export type PlannerExitResult =
  | { status: "saved" }
  | { status: "blocked"; reason: LaneBlockedReason; message: string }
  | { status: "confirm-discard" };

export type PlannerAbandonResult =
  | { status: "saved" }
  | { status: "confirm-discard"; message: string };

type PlannerTransitionMessages = {
  conflictMessage: string;
  fallbackMessage: string;
};

type PlannerTransitionController = {
  draft: PlanDraft | null;
  flushDraftPersistenceLane: () => Promise<LaneResult>;
  flushSmartRuleLane: () => Promise<LaneResult>;
  discardDraftPersistenceLane: () => void;
  discardSmartRuleLane: () => void;
};

function mapBlockedLaneResult(
  result: Extract<LaneResult, { status: "blocked" }>,
  messages: PlannerTransitionMessages,
): PlannerTransitionResult {
  if (result.reason === "conflict") {
    return {
      status: "blocked",
      reason: "conflict",
      message: messages.conflictMessage,
    };
  }
  return {
    status: "blocked",
    reason: "error",
    message: result.message || messages.fallbackMessage,
  };
}

async function flushBothLanes(
  controller: PlannerTransitionController,
  messages: PlannerTransitionMessages,
): Promise<PlannerTransitionResult> {
  const smartLaneResult = await controller.flushSmartRuleLane();
  if (smartLaneResult.status === "blocked") {
    return mapBlockedLaneResult(smartLaneResult, messages);
  }

  const draftLaneResult = await controller.flushDraftPersistenceLane();
  if (draftLaneResult.status === "blocked") {
    return mapBlockedLaneResult(draftLaneResult, messages);
  }

  return { status: "saved", message: null };
}

export async function preparePlannerWorkspaceSwitch(
  controller: PlannerTransitionController,
  messages: PlannerTransitionMessages,
): Promise<PlannerTransitionResult> {
  return await flushBothLanes(controller, messages);
}

export async function preparePlannerExport(
  controller: PlannerTransitionController,
  messages: PlannerTransitionMessages,
): Promise<PlannerTransitionResult> {
  return await flushBothLanes(controller, messages);
}

export async function preparePlannerHistoryAction(
  controller: PlannerTransitionController,
): Promise<LaneResult> {
  return await controller.flushDraftPersistenceLane();
}

export async function preparePlannerExit(
  controller: PlannerTransitionController,
  timeoutMs: number,
  messages: PlannerTransitionMessages,
): Promise<PlannerExitResult> {
  if (!controller.draft) {
    return { status: "saved" };
  }

  return await Promise.race<PlannerExitResult>([
    flushBothLanes(controller, messages).then((result) => {
      if (result.status === "saved") {
        return { status: "saved" } satisfies PlannerExitResult;
      }
      return result;
    }),
    new Promise<PlannerExitResult>((resolve) => {
      window.setTimeout(() => resolve({ status: "confirm-discard" }), timeoutMs);
    }),
  ]);
}

export function discardPlannerSession(controller: PlannerTransitionController): void {
  controller.discardSmartRuleLane();
  controller.discardDraftPersistenceLane();
}

export async function preparePlannerAbandonDraft(
  controller: PlannerTransitionController,
  messages: {
    continueAnywayMessage: string;
  },
): Promise<PlannerAbandonResult> {
  const smartLaneResult = await controller.flushSmartRuleLane();
  if (smartLaneResult.status === "blocked") {
    return {
      status: "confirm-discard",
      message: messages.continueAnywayMessage,
    };
  }
  return { status: "saved" };
}
