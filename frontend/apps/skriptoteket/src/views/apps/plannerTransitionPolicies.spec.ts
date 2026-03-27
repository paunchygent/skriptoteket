import { afterEach, describe, expect, it, vi } from "vitest";

import {
  discardPlannerSession,
  preparePlannerAbandonDraft,
  preparePlannerExit,
  preparePlannerHistoryAction,
  preparePlannerWorkspaceSwitch,
} from "./plannerTransitionPolicies";

function createController() {
  return {
    draft: {
      id: "draft-1",
      roster_id: "roster-1",
      draft_kind: "seating" as const,
      template_id: "template-1",
      status: "active" as const,
      revision: 4,
      last_opened_at: "2026-03-27T10:00:00Z",
    },
    flushDraftPersistenceLane: vi.fn().mockResolvedValue({ status: "saved" }),
    flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
    discardDraftPersistenceLane: vi.fn(),
    discardSmartRuleLane: vi.fn(),
  };
}

describe("plannerTransitionPolicies", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("flushes both lanes for workspace switches and maps conflict wording", async () => {
    const controller = createController();
    controller.flushSmartRuleLane.mockResolvedValue({
      status: "blocked",
      reason: "conflict",
      message: "backend conflict",
    });

    await expect(
      preparePlannerWorkspaceSwitch(controller, {
        conflictMessage: "Lös sparkonflikten innan du byter arbetsyta.",
        fallbackMessage: "Kunde inte byta arbetsyta just nu.",
      }),
    ).resolves.toEqual({
      status: "blocked",
      reason: "conflict",
      message: "Lös sparkonflikten innan du byter arbetsyta.",
    });

    expect(controller.flushSmartRuleLane).toHaveBeenCalledTimes(1);
    expect(controller.flushDraftPersistenceLane).not.toHaveBeenCalled();
  });

  it("flushes only the draft lane for history actions", async () => {
    const controller = createController();

    await expect(preparePlannerHistoryAction(controller)).resolves.toEqual({
      status: "saved",
    });

    expect(controller.flushDraftPersistenceLane).toHaveBeenCalledTimes(1);
    expect(controller.flushSmartRuleLane).not.toHaveBeenCalled();
  });

  it("returns confirm-discard when exit waiting times out", async () => {
    vi.useFakeTimers();
    const controller = createController();
    controller.flushSmartRuleLane.mockImplementation(
      () => new Promise(() => undefined),
    );

    const resultPromise = preparePlannerExit(controller, 1500, {
      conflictMessage: "unused",
      fallbackMessage: "unused",
    });
    await vi.advanceTimersByTimeAsync(1500);

    await expect(resultPromise).resolves.toEqual({ status: "confirm-discard" });
  });

  it("discards both lanes during explicit teardown", () => {
    const controller = createController();

    discardPlannerSession(controller);

    expect(controller.discardSmartRuleLane).toHaveBeenCalledTimes(1);
    expect(controller.discardDraftPersistenceLane).toHaveBeenCalledTimes(1);
  });

  it("requires confirm-discard when abandon cannot save smart rules first", async () => {
    const controller = createController();
    controller.flushSmartRuleLane.mockResolvedValue({
      status: "blocked",
      reason: "error",
      message: "Smarta regler kunde inte sparas.",
    });

    await expect(
      preparePlannerAbandonDraft(controller, {
        continueAnywayMessage: "Fortsätter du nu förlorar du osparade klassövergripande smarta regler.",
      }),
    ).resolves.toEqual({
      status: "confirm-discard",
      message: "Fortsätter du nu förlorar du osparade klassövergripande smarta regler.",
    });
  });
});
