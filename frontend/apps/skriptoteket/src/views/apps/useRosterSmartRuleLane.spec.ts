import { afterEach, describe, expect, it, vi } from "vitest";

import type { RosterSmartRulesResponse } from "./classroomPlannerTypes";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";

function createSmartRulesResponse(
  revision: number,
  studentIds: string[] = ["s1"],
): RosterSmartRulesResponse {
  return {
    roster_id: "roster-1",
    revision,
    seating_preferences: studentIds.map((studentId) => ({
      student_id: studentId,
      near_teacher: true,
    })),
    relationship_rules: [],
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("useRosterSmartRuleLane", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("tracks hydration state separately from persistence state", () => {
    const lane = useRosterSmartRuleLane({
      canSchedule: () => true,
      getSessionToken: () => 0,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistSmartRules: vi.fn(),
      serializePatch: () => ({
        expected_revision: 0,
        seating_preferences: [],
        relationship_rules: [],
        fixed_seat_rules: [],
      }),
      applyCommittedRules: vi.fn(),
      applyAcknowledgement: vi.fn(),
    });

    lane.bindRoster("roster-1");
    expect(lane.hydrationStatus.value).toBe("loading");

    lane.failHydration("Kunde inte ladda smarta regler.");
    expect(lane.hydrationStatus.value).toBe("error");
    expect(lane.hydrationMessage.value).toBe("Kunde inte ladda smarta regler.");

    lane.applyHydratedRules();
    expect(lane.hydrationStatus.value).toBe("ready");
  });

  it("keeps newer smart-rule edits dirty when an older save resolves first", async () => {
    vi.useFakeTimers();
    const firstSave = createDeferred<RosterSmartRulesResponse>();
    const secondSave = createDeferred<RosterSmartRulesResponse>();
    const persistSmartRules = vi.fn()
      .mockReturnValueOnce(firstSave.promise)
      .mockReturnValueOnce(secondSave.promise);
    const applyCommittedRules = vi.fn();
    const applyAcknowledgement = vi.fn();

    const lane = useRosterSmartRuleLane({
      canSchedule: () => true,
      getSessionToken: () => 0,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistSmartRules,
      serializePatch: () => ({
        expected_revision: 0,
        seating_preferences: [{ student_id: "s1", near_teacher: true }],
        relationship_rules: [],
        fixed_seat_rules: [],
      }),
      applyCommittedRules,
      applyAcknowledgement,
    });

    lane.bindRoster("roster-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);

    lane.markDirty();
    firstSave.resolve(createSmartRulesResponse(1, ["s1"]));
    await Promise.resolve();
    await Promise.resolve();

    expect(applyAcknowledgement).toHaveBeenCalledWith(createSmartRulesResponse(1, ["s1"]));
    expect(lane.hasPendingChanges.value).toBe(true);

    secondSave.resolve(createSmartRulesResponse(2, ["s1", "s2"]));
    await Promise.resolve();
    await Promise.resolve();

    expect(persistSmartRules).toHaveBeenCalledTimes(2);
    expect(applyCommittedRules).toHaveBeenCalledWith(createSmartRulesResponse(2, ["s1", "s2"]));
    expect(lane.hasPendingChanges.value).toBe(false);
  });

  it("flushes queued smart-rule edits before reporting saved", async () => {
    vi.useFakeTimers();
    const firstSave = createDeferred<RosterSmartRulesResponse>();
    const secondSave = createDeferred<RosterSmartRulesResponse>();
    const persistSmartRules = vi.fn()
      .mockReturnValueOnce(firstSave.promise)
      .mockReturnValueOnce(secondSave.promise);
    const applyCommittedRules = vi.fn();
    const applyAcknowledgement = vi.fn();

    const lane = useRosterSmartRuleLane({
      canSchedule: () => true,
      getSessionToken: () => 0,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistSmartRules,
      serializePatch: () => ({
        expected_revision: 0,
        seating_preferences: [{ student_id: "s1", near_teacher: true }],
        relationship_rules: [],
        fixed_seat_rules: [],
      }),
      applyCommittedRules,
      applyAcknowledgement,
    });

    lane.bindRoster("roster-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);
    lane.markDirty();

    const flushPromise = lane.flushPendingChanges();
    firstSave.resolve(createSmartRulesResponse(1, ["s1"]));
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(10);

    expect(persistSmartRules).toHaveBeenCalledTimes(2);
    expect(lane.hasPendingChanges.value).toBe(true);

    secondSave.resolve(createSmartRulesResponse(2, ["s1", "s2"]));
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(10);

    await expect(flushPromise).resolves.toEqual({ status: "saved" });
    expect(applyCommittedRules).toHaveBeenCalledWith(createSmartRulesResponse(2, ["s1", "s2"]));
    expect(lane.hasPendingChanges.value).toBe(false);
  });

  it("ignores late smart-rule responses after the session token changes", async () => {
    vi.useFakeTimers();
    let sessionToken = 0;
    const saveDeferred = createDeferred<RosterSmartRulesResponse>();
    const applyCommittedRules = vi.fn();
    const lane = useRosterSmartRuleLane({
      canSchedule: () => true,
      getSessionToken: () => sessionToken,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistSmartRules: vi.fn().mockReturnValue(saveDeferred.promise),
      serializePatch: () => ({
        expected_revision: 0,
        seating_preferences: [{ student_id: "s1", near_teacher: true }],
        relationship_rules: [],
        fixed_seat_rules: [],
      }),
      applyCommittedRules,
      applyAcknowledgement: vi.fn(),
    });

    lane.bindRoster("roster-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);

    sessionToken = 1;
    lane.bindRoster("roster-2");
    saveDeferred.resolve(createSmartRulesResponse(1));
    await Promise.resolve();

    expect(applyCommittedRules).not.toHaveBeenCalled();
  });
});
