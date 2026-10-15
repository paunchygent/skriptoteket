import { beforeEach, describe, expect, it, vi } from "vitest";

import { updateClassroomPlannerSettings } from "./classroomPlannerSettings";

const SETTINGS_PATH = "/api/v1/profile/classroom-planner-settings";

const clientMocks = vi.hoisted(() => ({ apiPatch: vi.fn() }));

vi.mock("./client", () => ({ apiPatch: clientMocks.apiPatch }));

beforeEach(() => {
  clientMocks.apiPatch.mockReset();
});

describe("updateClassroomPlannerSettings", () => {
  it("sends the request body unchanged to the settings endpoint and returns the profile response", async () => {
    const response = { user: { id: "user-1" }, profile: { user_id: "user-1" } };
    clientMocks.apiPatch.mockResolvedValue(response);

    const result = await updateClassroomPlannerSettings({
      tutorial_seen_sections: ["planner_overview"],
    });

    expect(clientMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(clientMocks.apiPatch).toHaveBeenCalledWith(SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_overview"],
    });
    expect(result).toBe(response);
  });

  it("propagates a refused write to the caller", async () => {
    clientMocks.apiPatch.mockRejectedValue(new Error("refused"));

    await expect(updateClassroomPlannerSettings({ smart_enabled: false })).rejects.toThrow(
      "refused",
    );
  });
});
