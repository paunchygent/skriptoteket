import { describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  createDraft,
  createWorkspaceResponse,
  createSmartRulesResponse,
  createWorkspaceVariant,
  createDeferred,
  mockWorkspaceLoad,
  seedWorkspace,
  setupClassroomStateTests,
} from "./useClassroomState.specSupport";
import { useClassroomState } from "./useClassroomState";
import type { RosterSmartRulesResponse } from "./classroomPlannerTypes";

describe("useClassroomState autosave", () => {
  setupClassroomStateTests();

  it("does not let a late autosave response repopulate cleared workspace state", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const draftPatchDeferred = createDeferred<ReturnType<typeof createWorkspaceResponse>>();
    clientMocks.apiPatch.mockReturnValueOnce(draftPatchDeferred.promise);
    vi.useFakeTimers();

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();
    state.clearWorkspace();

    draftPatchDeferred.resolve(createWorkspaceResponse());
    await Promise.resolve();
    await vi.runAllTimersAsync();
    await Promise.resolve();

    expect(state.draft).toBeNull();
    expect(state.roster).toBeNull();
    expect(state.template).toBeNull();
    expect(state.draftPersistenceStatus).toBe("idle");
    expect(state.plannerStatusMessage).toBeNull();
  });

  it("ignores a late draft autosave response after switching to another workspace", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const draftPatchDeferred = createDeferred<ReturnType<typeof createWorkspaceVariant>>();
    clientMocks.apiPatch.mockReturnValueOnce(draftPatchDeferred.promise);
    clientMocks.apiGet.mockResolvedValueOnce(
      createWorkspaceVariant({
        draftId: "draft-2",
        rosterId: "roster-2",
      }),
    );
    clientMocks.apiGet.mockResolvedValueOnce({
      ...createSmartRulesResponse(),
      roster_id: "roster-2",
      seating_preferences: [{ student_id: "s2", near_teacher: true }],
    });

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();

    const loadPromise = state.loadWorkspace("draft-2");
    await Promise.resolve();

    draftPatchDeferred.resolve(
      createWorkspaceVariant({
        draftId: "draft-1",
        rosterId: "roster-1",
      }),
    );
    await Promise.resolve();
    await loadPromise;

    expect(state.draft?.id).toBe("draft-2");
    expect(state.roster?.id).toBe("roster-2");
    expect(state.seatingPreferences).toEqual([{ student_id: "s2", near_teacher: true }]);
    expect(state.seatAssignmentsByStudentId).toEqual({});
  });

  it("keeps newer draft edits dirty when an older draft autosave succeeds first", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const firstDraftSave = createDeferred<ReturnType<typeof createWorkspaceVariant>>();
    clientMocks.apiPatch
      .mockReturnValueOnce(firstDraftSave.promise)
      .mockResolvedValueOnce({
        ...createWorkspaceVariant(),
        draft: {
          ...createWorkspaceVariant().draft,
          revision: 6,
        },
        seat_assignments: [{ student_id: "s1", seat_id: "seat-2" }],
      });

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();

    state.assignStudentToSeat("s1", "seat-2");
    firstDraftSave.resolve({
      ...createWorkspaceVariant(),
      draft: {
        ...createWorkspaceVariant().draft,
        revision: 5,
      },
      seat_assignments: [{ student_id: "s1", seat_id: "seat-1" }],
    });
    await Promise.resolve();

    expect(state.seatAssignmentsByStudentId["s1"]).toBe("seat-2");
    expect(state.hasPendingAutosave).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPatch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1",
      expect.objectContaining({
        expected_revision: 5,
        seat_assignments: [{ student_id: "s1", seat_id: "seat-2" }],
      }),
    );
    expect(state.seatAssignmentsByStudentId["s1"]).toBe("seat-2");
    expect(state.draft?.revision).toBe(6);
    expect(state.hasPendingAutosave).toBe(false);
  });

  it("keeps newer smart-rule edits dirty when an older smart-rule autosave succeeds first", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const firstSmartRuleSave = createDeferred<RosterSmartRulesResponse>();
    clientMocks.apiPatch
      .mockReturnValueOnce(firstSmartRuleSave.promise)
      .mockResolvedValueOnce({
        ...createSmartRulesResponse(),
        revision: 2,
        seating_preferences: [
          { student_id: "s1", near_teacher: true },
          { student_id: "s2", near_teacher: true },
        ],
      });

    state.setActiveSeatingSmartTool("near_teacher");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.commitPendingRelationshipRule();
    await vi.advanceTimersByTimeAsync(900);
    await Promise.resolve();

    state.beginNearTeacherEdit();
    state.handleSeatingSmartToolStudentSelection("s2");
    state.commitPendingRelationshipRule();
    firstSmartRuleSave.resolve({
      ...createSmartRulesResponse(),
      revision: 1,
      seating_preferences: [{ student_id: "s1", near_teacher: true }],
    });
    await Promise.resolve();

    expect(state.seatingPreferences).toEqual([
      { student_id: "s1", near_teacher: true },
      { student_id: "s2", near_teacher: true },
    ]);
    expect(state.hasPendingAutosave).toBe(true);

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPatch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
      {
        expected_revision: 1,
        seating_preferences: [
          { student_id: "s1", near_teacher: true },
          { student_id: "s2", near_teacher: true },
        ],
        relationship_rules: [],
        fixed_seat_rules: [],
      },
    );
    expect(state.smartRulesRevision).toBe(2);
    expect(state.seatingPreferences).toEqual([
      { student_id: "s1", near_teacher: true },
      { student_id: "s2", near_teacher: true },
    ]);
    expect(state.hasPendingAutosave).toBe(false);
  });

  it("autosaves only the fundamentals payload", async () => {
    vi.useFakeTimers();
    const state = useClassroomState();
    mockWorkspaceLoad(
      createWorkspaceResponse(),
      {
        ...createSmartRulesResponse(),
        seating_preferences: [
          {
            student_id: "s2",
            near_teacher: true,
          },
        ],
      },
    );
    clientMocks.apiPatch.mockResolvedValue(createWorkspaceResponse());
    await state.loadWorkspace("draft-1");
    clientMocks.apiPatch.mockClear();

    state.assignStudentToSeat("s1", "seat-1");
    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    const payload = clientMocks.apiPatch.mock.calls[0]?.[1];
    expect(payload).toMatchObject({
      expected_revision: 4,
      groups: state.groups,
      group_assignments: [],
      seat_assignments: [{ student_id: "s1", seat_id: "seat-1" }],
    });
    expect(payload).not.toHaveProperty("seating_preferences");
    expect(payload).not.toHaveProperty("relationship_rules");
    expect(payload).not.toHaveProperty("pair_constraints");
    expect(payload).not.toHaveProperty("planning_profile");
  });

  it("keeps draft autosave dirty when smart-rule autosave fails and retries that lane on flush", async () => {
    vi.useFakeTimers();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    state.smartRulesRevision = 4;
    let smartRuleSaveAttempts = 0;
    clientMocks.apiPatch.mockImplementation(async (url: string) => {
      if (url.endsWith("/smart-rules")) {
        smartRuleSaveAttempts += 1;
        if (smartRuleSaveAttempts === 1) {
          throw new Error("smart rules unavailable");
        }
        return {
          ...createSmartRulesResponse(),
          roster_id: "roster-1",
          revision: 5,
          seating_preferences: [{ student_id: "s1", near_teacher: true }],
          relationship_rules: [],
        };
      }
      if (url.endsWith("/drafts/draft-1")) {
        return createWorkspaceResponse("template-1", "seating", {
          can_undo: false,
          can_redo: false,
        });
      }
      throw new Error(`Unexpected patch url: ${url}`);
    });

    state.assignStudentToSeat("s1", "seat-1");
    state.setActiveSeatingSmartTool("near_teacher");
    state.handleSeatingSmartToolStudentSelection("s1");
    state.commitPendingRelationshipRule();

    await vi.advanceTimersByTimeAsync(900);

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPatch.mock.calls.map((call) => call[0])).toEqual(
      expect.arrayContaining([
        "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
        "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1",
      ]),
    );
    expect(state.hasPendingAutosave).toBe(true);
    expect(state.smartRulePersistenceStatus).toBe("error");
    expect(state.draftPersistenceStatus).toBe("saved");

    const flushResult = await state.prepareForWorkspaceSwitch({
      conflictMessage: "unused",
      fallbackMessage: "unused",
    });

    expect(flushResult).toEqual({ status: "saved", message: null });
    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(3);
    expect(clientMocks.apiPatch.mock.calls[2]?.[0]).toBe(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1/smart-rules",
    );
    expect(clientMocks.apiPatch.mock.calls[2]?.[1]).toMatchObject({
      expected_revision: 4,
      seating_preferences: [{ student_id: "s1", near_teacher: true }],
      relationship_rules: [],
    });
    expect(state.hasPendingAutosave).toBe(false);
    expect(state.smartRulesRevision).toBe(5);
    expect(state.smartRulePersistenceStatus).toBe("saved");
  });
});
