import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "../../../stores/auth";
import {
  CLASSROOM_PLANNER_SETTINGS_PATH,
  GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY,
  useTutorialSeenSections,
} from "./useTutorialSeenSections";

const apiMocks = vi.hoisted(() => ({
  apiPatch: vi.fn(),
  load: vi.fn(),
}));

vi.mock("../../../api/client", () => ({
  apiPatch: apiMocks.apiPatch,
}));

vi.mock("../../../composables/useProfile", () => ({
  useProfile: () => ({ load: apiMocks.load }),
}));

function signedInProfile(seen: string[] | null | undefined): Record<string, unknown> {
  const profile: Record<string, unknown> = { user_id: "user-1", locale: "sv-SE" };
  if (seen !== undefined) {
    profile.classroom_planner_tutorial_seen_sections = seen;
  }
  return profile;
}

beforeEach(() => {
  window.localStorage.clear();
  setActivePinia(createPinia());
  apiMocks.apiPatch.mockReset();
  apiMocks.load.mockReset();
  apiMocks.load.mockResolvedValue(undefined);
});

describe("useTutorialSeenSections for guests", () => {
  it("reads and writes the browser list under the v1 key", () => {
    window.localStorage.setItem(
      GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY,
      JSON.stringify(["planner_rules"]),
    );
    const seen = useTutorialSeenSections("public");

    expect(seen.ready.value).toBe(true);
    expect(seen.isSeen("planner_rules")).toBe(true);
    expect(seen.isSeen("planner_overview")).toBe(false);

    seen.markSeen("planner_overview");
    seen.markSeen("planner_overview");

    expect(seen.isSeen("planner_overview")).toBe(true);
    expect(
      JSON.parse(window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY) ?? "null"),
    ).toEqual(["planner_rules", "planner_overview"]);
    expect(apiMocks.apiPatch).not.toHaveBeenCalled();
  });

  it("treats corrupt or non-list storage as nothing seen", () => {
    window.localStorage.setItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY, "{broken");
    expect(useTutorialSeenSections("public").isSeen("planner_overview")).toBe(false);

    window.localStorage.setItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY, '{"a":1}');
    expect(useTutorialSeenSections("public").isSeen("planner_overview")).toBe(false);
  });

  it("keeps the in-memory value when storage writes fail", () => {
    const setItem = vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    const seen = useTutorialSeenSections("public");

    expect(() => seen.markSeen("planner_overview")).not.toThrow();
    expect(seen.isSeen("planner_overview")).toBe(true);
    setItem.mockRestore();
  });
});

describe("useTutorialSeenSections for signed-in users", () => {
  it("reads the profile list and sends the full union to the settings endpoint", async () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile(["planner_rules"]) as typeof auth.profile;
    apiMocks.apiPatch.mockResolvedValue({
      profile: signedInProfile(["planner_rules", "planner_overview"]),
    });
    const seen = useTutorialSeenSections("authenticated");

    expect(seen.ready.value).toBe(true);
    expect(seen.isSeen("planner_rules")).toBe(true);

    seen.markSeen("planner_overview");

    expect(seen.isSeen("planner_overview")).toBe(true);
    expect(apiMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(apiMocks.apiPatch).toHaveBeenCalledWith(CLASSROOM_PLANNER_SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_rules", "planner_overview"],
    });
    expect(window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY)).toBeNull();

    await vi.waitFor(() =>
      expect(
        (auth.profile as Record<string, unknown>).classroom_planner_tutorial_seen_sections,
      ).toEqual(["planner_rules", "planner_overview"]),
    );
  });

  it("treats a null profile field as nothing seen", () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile(null) as typeof auth.profile;
    apiMocks.apiPatch.mockResolvedValue({ profile: signedInProfile(["planner_seating"]) });
    const seen = useTutorialSeenSections("authenticated");

    expect(seen.isSeen("planner_seating")).toBe(false);
    seen.markSeen("planner_seating");
    expect(apiMocks.apiPatch).toHaveBeenCalledWith(CLASSROOM_PLANNER_SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_seating"],
    });
  });

  it("keeps the optimistic value after a failed write and does not retry", async () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile([]) as typeof auth.profile;
    apiMocks.apiPatch.mockRejectedValue(new Error("offline"));
    const seen = useTutorialSeenSections("authenticated");

    seen.markSeen("planner_grouping");
    await Promise.resolve();
    await Promise.resolve();

    expect(seen.isSeen("planner_grouping")).toBe(true);
    seen.markSeen("planner_grouping");
    expect(apiMocks.apiPatch).toHaveBeenCalledTimes(1);
  });

  it("is not ready until the profile is loaded, and loads it when missing", () => {
    const seen = useTutorialSeenSections("authenticated");

    expect(seen.ready.value).toBe(false);
    expect(apiMocks.load).toHaveBeenCalledTimes(1);

    const auth = useAuthStore();
    auth.profile = signedInProfile(["planner_overview"]) as typeof auth.profile;
    expect(seen.ready.value).toBe(true);
    expect(seen.isSeen("planner_overview")).toBe(true);
  });
});
