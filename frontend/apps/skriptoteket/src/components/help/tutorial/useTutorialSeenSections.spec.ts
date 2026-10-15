import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "../../../stores/auth";
import { useToastStore } from "../../../stores/toast";
import { TUTORIAL_COPY } from "./tutorialCopy";
import {
  GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY,
  useTutorialSeenSections,
} from "./useTutorialSeenSections";

const SETTINGS_PATH = "/api/v1/profile/classroom-planner-settings";

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

type SeenBody = { tutorial_seen_sections: string[] };

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function signedInProfile(seen: string[] | null | undefined): Record<string, unknown> {
  const profile: Record<string, unknown> = { user_id: "user-1", locale: "sv-SE" };
  if (seen !== undefined) {
    profile.classroom_planner_tutorial_seen_sections = seen;
  }
  return profile;
}

function profileResponse(seen: string[]): Record<string, unknown> {
  return { user: { id: "user-1" }, profile: signedInProfile(seen) };
}

function profileSeen(): unknown {
  const auth = useAuthStore();
  return (auth.profile as Record<string, unknown> | null)?.classroom_planner_tutorial_seen_sections;
}

async function flush(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
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
    expect(seen.persistence.value).toBe("confirmed");
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

  it("suppresses the section for this visit and reports a failed save when storage is blocked", () => {
    const setItem = vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    const seen = useTutorialSeenSections("public");

    expect(() => seen.markSeen("planner_overview")).not.toThrow();
    expect(seen.isSeen("planner_overview")).toBe(true);
    expect(seen.persistence.value).toBe("failed");
    setItem.mockRestore();
  });
});

describe("useTutorialSeenSections for signed-in users", () => {
  it("reads the profile list and sends the full union to the settings endpoint", async () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile(["planner_rules"]) as typeof auth.profile;
    apiMocks.apiPatch.mockResolvedValue(profileResponse(["planner_rules", "planner_overview"]));
    const seen = useTutorialSeenSections("authenticated");

    expect(seen.ready.value).toBe(true);
    expect(seen.isSeen("planner_rules")).toBe(true);

    seen.markSeen("planner_overview");

    expect(seen.isSeen("planner_overview")).toBe(true);
    expect(seen.persistence.value).toBe("pending");
    expect(apiMocks.apiPatch).toHaveBeenCalledTimes(1);
    expect(apiMocks.apiPatch).toHaveBeenCalledWith(SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_rules", "planner_overview"],
    });
    expect(window.localStorage.getItem(GUEST_TUTORIAL_SEEN_SECTIONS_STORAGE_KEY)).toBeNull();

    await vi.waitFor(() => expect(seen.persistence.value).toBe("confirmed"));
    expect(profileSeen()).toEqual(["planner_rules", "planner_overview"]);
  });

  it("treats a null profile field as nothing seen", () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile(null) as typeof auth.profile;
    apiMocks.apiPatch.mockResolvedValue(profileResponse(["planner_seating"]));
    const seen = useTutorialSeenSections("authenticated");

    expect(seen.isSeen("planner_seating")).toBe(false);
    seen.markSeen("planner_seating");
    expect(apiMocks.apiPatch).toHaveBeenCalledWith(SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_seating"],
    });
  });

  it("never lets an older replacement be the last durable write when responses arrive newest first", async () => {
    // Model of the endpoint's replace semantics: the list a request carries
    // becomes the stored list at the moment that request commits.
    const server = { seen: [] as string[] };
    const outstanding: Array<{ body: SeenBody; done: Deferred<unknown> }> = [];
    apiMocks.apiPatch.mockImplementation((_path: string, body: SeenBody) => {
      const done = deferred<unknown>();
      outstanding.push({ body, done });
      return done.promise;
    });
    const auth = useAuthStore();
    auth.profile = signedInProfile([]) as typeof auth.profile;
    const seen = useTutorialSeenSections("authenticated");

    seen.markSeen("planner_overview");
    seen.markSeen("planner_rules");

    // Commit every request that is in flight together, newest first, until
    // the client sends nothing more.
    while (outstanding.length > 0) {
      for (const call of outstanding.splice(0).reverse()) {
        server.seen = [...call.body.tutorial_seen_sections];
        call.done.resolve(profileResponse(server.seen));
        await flush();
      }
      await flush();
    }

    expect([...server.seen].sort()).toEqual(["planner_overview", "planner_rules"]);
    expect(apiMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(apiMocks.apiPatch).toHaveBeenNthCalledWith(1, SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_overview"],
    });
    expect(apiMocks.apiPatch).toHaveBeenNthCalledWith(2, SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_overview", "planner_rules"],
    });
    expect(seen.persistence.value).toBe("confirmed");
    expect(profileSeen()).toEqual(["planner_overview", "planner_rules"]);
  });

  it("keeps a section pending until an acknowledged profile list includes it", async () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile([]) as typeof auth.profile;
    // The server acknowledges the write but returns a list without the section.
    apiMocks.apiPatch.mockResolvedValueOnce(profileResponse([]));
    const seen = useTutorialSeenSections("authenticated");

    seen.markSeen("planner_overview");
    await flush();

    expect(seen.persistence.value).toBe("pending");
    expect(seen.pendingSections.value).toEqual(["planner_overview"]);
    expect(seen.isSeen("planner_overview")).toBe(true);
    expect(profileSeen()).toEqual([]);
  });

  it("reports a failed save, keeps the section pending and sends it with the next write", async () => {
    const auth = useAuthStore();
    auth.profile = signedInProfile([]) as typeof auth.profile;
    const toast = useToastStore();
    const failure = vi.spyOn(toast, "failure");
    apiMocks.apiPatch.mockRejectedValueOnce(new Error("offline"));
    const seen = useTutorialSeenSections("authenticated");

    seen.markSeen("planner_grouping");
    await flush();

    // The dismissal is suppressed for this visit but is not written as saved.
    expect(seen.isSeen("planner_grouping")).toBe(true);
    expect(seen.persistence.value).toBe("failed");
    expect(seen.pendingSections.value).toEqual(["planner_grouping"]);
    expect(profileSeen()).toEqual([]);
    expect(failure).toHaveBeenCalledTimes(1);
    expect(failure).toHaveBeenCalledWith(TUTORIAL_COPY.seenSaveFailed);
    expect(TUTORIAL_COPY.seenSaveFailed).toBe(
      "Kunde inte spara att du sett klippet. Försöker igen nästa gång.",
    );

    // Marking the same section again does not start another write.
    seen.markSeen("planner_grouping");
    expect(apiMocks.apiPatch).toHaveBeenCalledTimes(1);

    apiMocks.apiPatch.mockResolvedValueOnce(
      profileResponse(["planner_grouping", "planner_rules"]),
    );
    seen.markSeen("planner_rules");

    expect(apiMocks.apiPatch).toHaveBeenCalledTimes(2);
    expect(apiMocks.apiPatch).toHaveBeenLastCalledWith(SETTINGS_PATH, {
      tutorial_seen_sections: ["planner_grouping", "planner_rules"],
    });
    await vi.waitFor(() => expect(seen.persistence.value).toBe("confirmed"));
    expect(seen.pendingSections.value).toEqual([]);
    expect(profileSeen()).toEqual(["planner_grouping", "planner_rules"]);
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
