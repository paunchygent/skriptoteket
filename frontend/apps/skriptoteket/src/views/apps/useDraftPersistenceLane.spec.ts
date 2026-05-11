import { afterEach, describe, expect, it, vi } from "vitest";

import type { DraftWorkspaceResponse } from "./classroomPlannerTypes";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";

function createWorkspaceResponse(revision: number): DraftWorkspaceResponse {
  return {
    draft: {
      id: "draft-1",
      roster_id: "roster-1",
      draft_kind: "grouping",
      template_id: "template-1",
      status: "active",
      revision,
      last_opened_at: "2026-03-27T10:00:00Z",
    },
    roster: {
      id: "roster-1",
      name: "Klass 9A",
      students: [],
    },
    template: null,
    groups: [],
    group_assignments: [],
    seat_assignments: [],
    history_status: {
      can_undo: revision > 4,
      can_redo: false,
    },
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("useDraftPersistenceLane", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("persists a dirty draft lane and applies the committed workspace", async () => {
    vi.useFakeTimers();
    const sessionToken = 0;
    const applyCommittedWorkspace = vi.fn();
    const applyAcknowledgement = vi.fn();
    const persistDraft = vi.fn().mockResolvedValue(createWorkspaceResponse(5));

    const lane = useDraftPersistenceLane({
      canSchedule: () => true,
      getSessionToken: () => sessionToken,
      normalizeErrorMessage: (error, fallback) => fallback,
      persistDraft,
      serializePatch: () => ({
        expected_revision: 4,
        smart_enabled: false,
        use_history: false,
        grouping_seating_distance_enabled: false,
        groups: [],
        group_assignments: [],
        seat_assignments: [],
      }),
      applyCommittedWorkspace,
      applyAcknowledgement,
    });

    lane.resetBoundDraft("draft-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);

    expect(persistDraft).toHaveBeenCalledTimes(1);
    expect(applyCommittedWorkspace).toHaveBeenCalledWith(createWorkspaceResponse(5));
    expect(applyAcknowledgement).not.toHaveBeenCalled();
    expect(lane.status.value).toBe("saved");
    expect(lane.hasPendingChanges.value).toBe(false);
  });

  it("keeps newer draft edits dirty when an older save resolves first", async () => {
    vi.useFakeTimers();
    const firstSave = createDeferred<DraftWorkspaceResponse>();
    const secondSave = createDeferred<DraftWorkspaceResponse>();
    const persistDraft = vi.fn()
      .mockReturnValueOnce(firstSave.promise)
      .mockReturnValueOnce(secondSave.promise);
    const applyCommittedWorkspace = vi.fn();
    const applyAcknowledgement = vi.fn();

    const lane = useDraftPersistenceLane({
      canSchedule: () => true,
      getSessionToken: () => 0,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistDraft,
      serializePatch: () => ({
        expected_revision: 4,
        smart_enabled: false,
        use_history: false,
        grouping_seating_distance_enabled: false,
        groups: [],
        group_assignments: [],
        seat_assignments: [],
      }),
      applyCommittedWorkspace,
      applyAcknowledgement,
    });

    lane.resetBoundDraft("draft-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);

    lane.markDirty();
    firstSave.resolve(createWorkspaceResponse(5));
    await Promise.resolve();
    await Promise.resolve();

    expect(applyAcknowledgement).toHaveBeenCalledWith(createWorkspaceResponse(5));
    expect(lane.hasPendingChanges.value).toBe(true);

    secondSave.resolve(createWorkspaceResponse(6));
    await Promise.resolve();
    await Promise.resolve();

    expect(persistDraft).toHaveBeenCalledTimes(2);
    expect(applyCommittedWorkspace).toHaveBeenCalledWith(createWorkspaceResponse(6));
    expect(lane.hasPendingChanges.value).toBe(false);
  });

  it("flushes queued draft edits before reporting saved", async () => {
    vi.useFakeTimers();
    const firstSave = createDeferred<DraftWorkspaceResponse>();
    const secondSave = createDeferred<DraftWorkspaceResponse>();
    const persistDraft = vi.fn()
      .mockReturnValueOnce(firstSave.promise)
      .mockReturnValueOnce(secondSave.promise);
    const applyCommittedWorkspace = vi.fn();
    const applyAcknowledgement = vi.fn();

    const lane = useDraftPersistenceLane({
      canSchedule: () => true,
      getSessionToken: () => 0,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistDraft,
      serializePatch: () => ({
        expected_revision: 4,
        smart_enabled: false,
        use_history: false,
        grouping_seating_distance_enabled: false,
        groups: [],
        group_assignments: [],
        seat_assignments: [],
      }),
      applyCommittedWorkspace,
      applyAcknowledgement,
    });

    lane.resetBoundDraft("draft-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);
    lane.markDirty();

    const flushPromise = lane.flushPendingChanges();
    firstSave.resolve(createWorkspaceResponse(5));
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(10);

    expect(persistDraft).toHaveBeenCalledTimes(2);
    expect(lane.hasPendingChanges.value).toBe(true);

    secondSave.resolve(createWorkspaceResponse(6));
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(10);

    await expect(flushPromise).resolves.toEqual({ status: "saved" });
    expect(applyCommittedWorkspace).toHaveBeenCalledWith(createWorkspaceResponse(6));
    expect(lane.hasPendingChanges.value).toBe(false);
  });

  it("ignores late responses after the session token changes", async () => {
    vi.useFakeTimers();
    let sessionToken = 0;
    const saveDeferred = createDeferred<DraftWorkspaceResponse>();
    const applyCommittedWorkspace = vi.fn();
    const lane = useDraftPersistenceLane({
      canSchedule: () => true,
      getSessionToken: () => sessionToken,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistDraft: vi.fn().mockReturnValue(saveDeferred.promise),
      serializePatch: () => ({
        expected_revision: 4,
        smart_enabled: false,
        use_history: false,
        grouping_seating_distance_enabled: false,
        groups: [],
        group_assignments: [],
        seat_assignments: [],
      }),
      applyCommittedWorkspace,
      applyAcknowledgement: vi.fn(),
    });

    lane.resetBoundDraft("draft-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);

    sessionToken = 1;
    lane.resetBoundDraft("draft-2");
    saveDeferred.resolve(createWorkspaceResponse(5));
    await Promise.resolve();

    expect(applyCommittedWorkspace).not.toHaveBeenCalled();
  });

  it("acknowledges an external commit without replaying an older in-flight save", async () => {
    vi.useFakeTimers();
    const saveDeferred = createDeferred<DraftWorkspaceResponse>();
    const applyCommittedWorkspace = vi.fn();
    const applyAcknowledgement = vi.fn();
    const lane = useDraftPersistenceLane({
      canSchedule: () => true,
      getSessionToken: () => 0,
      normalizeErrorMessage: (_error, fallback) => fallback,
      persistDraft: vi.fn().mockReturnValue(saveDeferred.promise),
      serializePatch: () => ({
        expected_revision: 4,
        smart_enabled: false,
        use_history: false,
        grouping_seating_distance_enabled: false,
        groups: [],
        group_assignments: [],
        seat_assignments: [],
      }),
      applyCommittedWorkspace,
      applyAcknowledgement,
    });

    lane.resetBoundDraft("draft-1");
    lane.markDirty();
    await vi.advanceTimersByTimeAsync(900);

    lane.acknowledgeExternalCommit("draft-1");
    saveDeferred.resolve(createWorkspaceResponse(5));
    await Promise.resolve();
    await Promise.resolve();

    expect(lane.hasPendingChanges.value).toBe(false);
    expect(lane.status.value).toBe("saved");
    expect(applyCommittedWorkspace).not.toHaveBeenCalled();
    expect(applyAcknowledgement).not.toHaveBeenCalled();
  });
});
