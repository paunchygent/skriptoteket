import { describe, expect, it } from "vitest";

import { usePlannerSessionController } from "./usePlannerSessionController";

describe("usePlannerSessionController", () => {
  it("tracks active session identity and invalidates tokens across replacements", () => {
    const controller = usePlannerSessionController();

    expect(controller.sessionToken.value).toBe(0);
    expect(controller.hasActiveSession.value).toBe(false);

    controller.replaceSession({ draftId: "draft-1", rosterId: "roster-1" });

    expect(controller.sessionToken.value).toBe(1);
    expect(controller.activeDraftId.value).toBe("draft-1");
    expect(controller.activeRosterId.value).toBe("roster-1");
    expect(controller.hasActiveSession.value).toBe(true);

    controller.clearSession();

    expect(controller.sessionToken.value).toBe(2);
    expect(controller.activeDraftId.value).toBeNull();
    expect(controller.activeRosterId.value).toBeNull();
    expect(controller.hasActiveSession.value).toBe(false);
  });

  it("invalidates older workspace load requests", () => {
    const controller = usePlannerSessionController();

    const firstRequestId = controller.createWorkspaceLoadRequest();
    const secondRequestId = controller.createWorkspaceLoadRequest();

    expect(controller.isCurrentWorkspaceLoadRequest(firstRequestId)).toBe(false);
    expect(controller.isCurrentWorkspaceLoadRequest(secondRequestId)).toBe(true);

    controller.invalidateAsyncState();

    expect(controller.isCurrentWorkspaceLoadRequest(secondRequestId)).toBe(false);
  });
});
