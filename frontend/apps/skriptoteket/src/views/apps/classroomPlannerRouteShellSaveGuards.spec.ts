import { afterEach, describe, expect, it, vi } from "vitest";

import {
  flushPlannerRouteShellSave,
  flushPlannerRouteShellSaveForExit,
  type PlannerRouteShellSaveController,
} from "./classroomPlannerRouteShellSaveGuards";

function createPlannerState(
  overrides?: Partial<PlannerRouteShellSaveController>,
): PlannerRouteShellSaveController {
  return {
    draft: {
      id: "draft-1",
      roster_id: "roster-1",
      draft_kind: "grouping",
      template_id: null,
      status: "active",
      revision: 1,
      last_opened_at: "2026-03-24T10:00:00Z",
    },
    saveMessage: null,
    saveStatus: "idle",
    flushPendingSave: vi.fn().mockResolvedValue(true),
    ...overrides,
  };
}

describe("classroomPlannerRouteShellSaveGuards", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns a blocked conflict message when the flush ends in a save conflict", async () => {
    const plannerState = createPlannerState({
      saveStatus: "conflict",
    });

    await expect(
      flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "Lös sparkonflikten innan du fortsätter.",
        fallbackMessage: "Kunde inte spara ändringarna.",
      }),
    ).resolves.toEqual({
      status: "blocked",
      message: "Lös sparkonflikten innan du fortsätter.",
    });
  });

  it("returns the backend save message for non-conflict blocked saves", async () => {
    const plannerState = createPlannerState({
      saveStatus: "error",
      saveMessage: "Sparningen stoppades av servern.",
    });

    await expect(
      flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "unused",
        fallbackMessage: "Kunde inte spara ändringarna.",
      }),
    ).resolves.toEqual({
      status: "blocked",
      message: "Sparningen stoppades av servern.",
    });
  });

  it("times out exit autosave when the flush promise does not resolve in time", async () => {
    vi.useFakeTimers();
    const plannerState = createPlannerState({
      flushPendingSave: vi.fn(() => new Promise<boolean>(() => undefined)),
    });

    const resultPromise = flushPlannerRouteShellSaveForExit(plannerState, 1500);
    await vi.advanceTimersByTimeAsync(1500);

    await expect(resultPromise).resolves.toBe("timed-out");
  });

  it("skips the exit flush when there is no active draft", async () => {
    const plannerState = createPlannerState({
      draft: null,
    });

    await expect(flushPlannerRouteShellSaveForExit(plannerState, 1500)).resolves.toBe("saved");
    expect(plannerState.flushPendingSave).not.toHaveBeenCalled();
  });
});
