import { describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  createDraft,
  createWorkspaceResponse,
  createProfileResponse,
  createDeferred,
  mockWorkspaceLoad,
  seedWorkspace,
  setupClassroomStateTests,
} from "./useClassroomState.specSupport";
import { useAuthStore } from "../../stores/auth";
import { useClassroomState } from "./useClassroomState";

describe("useClassroomState lifecycle", () => {
  setupClassroomStateTests();

  it("ignores a late workspace load after the workspace has been cleared", async () => {
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "seating");
    const workspaceDeferred = createDeferred<ReturnType<typeof createWorkspaceResponse>>();
    clientMocks.apiGet.mockReturnValueOnce(workspaceDeferred.promise);

    const loadPromise = state.loadWorkspace("draft-2");

    state.clearWorkspace();
    workspaceDeferred.resolve(createWorkspaceResponse());
    await loadPromise;

    expect(state.draft).toBeNull();
    expect(state.roster).toBeNull();
    expect(state.template).toBeNull();
    expect(clientMocks.apiGet).toHaveBeenCalledTimes(1);
  });

  it("resolves drafts without legacy lesson-mode payload fields", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft());
    mockWorkspaceLoad(createWorkspaceResponse());

    await state.resolveDraft("roster-1", "template-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
      {
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: "template-1",
      },
    );
    expect(clientMocks.apiPost.mock.calls[0]?.[1]).not.toHaveProperty("lesson_mode_id");
  });

  it("keeps seating workspaces alive even before a classroom has been selected", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft(null));
    mockWorkspaceLoad(createWorkspaceResponse(null));

    await state.resolveDraft("roster-1", null);

    expect(state.hasWorkspace).toBe(true);
    expect(state.template).toBeNull();
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
      {
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
      },
    );
  });

  it("starts a brand-new blank grouping draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "grouping"));
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "grouping"));

    await state.startNewGroupingDraft("roster-1", "template-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
      {
        roster_id: "roster-1",
        template_id: "template-1",
      },
    );
    expect(state.draft?.draft_kind).toBe("grouping");
    expect(state.groupAssignments).toEqual([]);
  });

  it("waits for ordered Smart preference persistence before starting a new grouping draft", async () => {
    // Profile writes update an already admitted teacher; they cannot sign one in.
    const auth = useAuthStore();
    auth.user = createProfileResponse().user;
    const session = auth.captureSession();
    const state = seedWorkspace();
    state.draft = createDraft("template-1", "grouping");
    const firstPreferenceWrite = createDeferred<ReturnType<typeof createProfileResponse>>();
    const secondPreferenceWrite = createDeferred<ReturnType<typeof createProfileResponse>>();
    clientMocks.apiPatch
      .mockReturnValueOnce(firstPreferenceWrite.promise)
      .mockReturnValueOnce(secondPreferenceWrite.promise);
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "grouping"));
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "grouping"));

    state.setDraftGroupingSeatingDistanceEnabled(true);
    state.setDraftGroupingSeatingDistanceEnabled(false);
    const newDraftPromise = state.startNewGroupingDraft("roster-1", "template-1");
    await vi.waitFor(() => expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1));

    expect(clientMocks.apiPatch).toHaveBeenNthCalledWith(
      1,
      "/api/v1/profile/classroom-planner-settings",
      { grouping_seating_distance_enabled: true },
    );
    expect(clientMocks.apiPost).not.toHaveBeenCalled();

    firstPreferenceWrite.resolve(createProfileResponse());
    await vi.waitFor(() => expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2));
    expect(clientMocks.apiPatch).toHaveBeenNthCalledWith(
      2,
      "/api/v1/profile/classroom-planner-settings",
      { grouping_seating_distance_enabled: false },
    );
    expect(clientMocks.apiPost).not.toHaveBeenCalled();

    secondPreferenceWrite.resolve(createProfileResponse());
    await newDraftPromise;

    expect(auth.isCurrentSession(session)).toBe(true);
    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new",
      {
        roster_id: "roster-1",
        template_id: "template-1",
      },
    );
    expect(
      clientMocks.apiPatch.mock.invocationCallOrder[1],
    ).toBeLessThan(clientMocks.apiPost.mock.invocationCallOrder[0]);
  });

  it("starts a brand-new seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "seating"));
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "seating"));

    await state.startNewSeatingDraft("roster-1", "template-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
      {
        roster_id: "roster-1",
        template_id: "template-1",
      },
    );
    expect(state.draft?.draft_kind).toBe("seating");
    expect(state.seatAssignments).toEqual([]);
  });

  it("activates a historical grouping draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "grouping"));
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "grouping"));

    await state.activateGroupingHistoryDraft("draft-history-1");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft-history-1/activate",
    );
    expect(clientMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/workspace",
    );
    expect(state.draft?.draft_kind).toBe("grouping");
  });

  it("deletes a historical grouping draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiDelete.mockResolvedValue(undefined);

    await state.deleteGroupingHistoryDraft("draft-history-1");

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft-history-1",
    );
  });

  it("activates a historical seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiPost.mockResolvedValue(createDraft("template-1", "seating"));
    mockWorkspaceLoad(createWorkspaceResponse("template-1", "seating"));

    await state.activateSeatingHistoryDraft("draft-history-2");

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/draft-history-2/activate",
    );
    expect(clientMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/draft-1/workspace",
    );
    expect(state.draft?.draft_kind).toBe("seating");
  });

  it("deletes a historical seating draft through the dedicated lifecycle endpoint", async () => {
    const state = useClassroomState();
    clientMocks.apiDelete.mockResolvedValue(undefined);

    await state.deleteSeatingHistoryDraft("draft-history-2");

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/draft-history-2",
    );
  });
});
