import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, apiGet } from "../api/client";
import { updateClassroomPlannerSettings } from "../api/classroomPlannerSettings";
import { useProfile } from "../composables/useProfile";
import { useClassroomPlannerSmartPreferenceLane } from "../views/apps/useClassroomPlannerSmartPreferenceLane";
import { SupersededAuthSessionError, useAuthStore } from "./auth";
import { loadAppContinuation, loadSharedCsrfToken, loadSharedSessionSnapshot } from "./authBootstrap";
import { createTestProfile, createTestUser } from "./authTestHelpers";
import { useTutorialSeenSectionsStore } from "./tutorialSeenSections";

vi.mock("../api/client", () => ({ apiFetch: vi.fn(), apiGet: vi.fn() }));
vi.mock("../api/classroomPlannerSettings", () => ({ updateClassroomPlannerSettings: vi.fn() }));
vi.mock("./authBootstrap", () => ({
  loadAppContinuation: vi.fn(), loadSharedCsrfToken: vi.fn(), loadSharedSessionSnapshot: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

function snapshotFor(id: string) {
  return {
    user: createTestUser({ id, email: `${id}@example.test` }),
    profile: createTestProfile({ user_id: id, display_name: id }),
  };
}

let auth: ReturnType<typeof useAuthStore>;
function copyAuthState(): typeof auth.$state {
  return JSON.parse(JSON.stringify(auth.$state)) as typeof auth.$state;
}
beforeEach(() => {
  vi.resetAllMocks();
  setActivePinia(createPinia());
  auth = useAuthStore();
  auth.$patch({ ...snapshotFor("teacher-a"), sharedSessionId: "session-a", bootstrapped: true });
});

describe("same-session response admission", () => {
  const saved = () => ({
    ...snapshotFor("teacher-a"),
    profile: createTestProfile({ user_id: "teacher-a", display_name: "saved profile" }),
  });

  it.each(["load", "updateProfile", "updateExamCourses"] as const)("accepts useProfile.%s without changing sessions", async (method) => {
    vi.mocked(apiGet).mockResolvedValue(saved());
    vi.mocked(apiFetch).mockResolvedValue(saved());
    const session = auth.captureSession();
    const profile = useProfile();
    if (method === "load") await profile.load();
    else if (method === "updateProfile") await profile.updateProfile({ display_name: "saved profile" });
    else await profile.updateExamCourses({ school_forms: ["gymnasiet"], course_keys: [] });
    expect(auth.profile).toEqual(saved().profile);
    expect(profile.profile.value).toEqual(saved().profile);
    expect(auth.isCurrentSession(session)).toBe(true);
  });

  it("accepts the teacher's queued Smart preference response", async () => {
    vi.mocked(updateClassroomPlannerSettings).mockResolvedValue(saved());
    const lane = useClassroomPlannerSmartPreferenceLane();
    lane.persistPreference("smart_enabled", true);
    expect(await lane.flushPendingChanges()).toEqual({ status: "saved" });
    expect(auth.profile).toEqual(saved().profile);
  });

  it("accepts and acknowledges the teacher's tutorial response", async () => {
    const response = saved();
    response.profile.classroom_planner_tutorial_seen_sections = ["planner_rules"];
    vi.mocked(updateClassroomPlannerSettings).mockResolvedValue(response);
    const seen = useTutorialSeenSectionsStore();
    seen.markSeen("planner_rules");
    await flushPromises();
    expect(auth.profile).toEqual(response.profile);
    expect(seen.persistence).toBe("confirmed");
    expect(seen.pending).toEqual([]);
    expect(seen.isSeen("planner_rules")).toBe(true);
  });

  function configureBootstrap(): void {
    auth.clear();
    auth.bootstrapped = false;
    vi.mocked(loadSharedSessionSnapshot).mockResolvedValue({
      kind: "authenticated", snapshot: {
        ...snapshotFor("teacher-a"),
        sharedSessionId: "session-a",
        grants: ["teacher-grant"], featureFlags: ["teacher-flag"],
      },
    });
    vi.mocked(loadAppContinuation).mockResolvedValue({
      kind: "ready", profile: saved().profile,
      continuation: { local_user: saved().user } as Extract<Awaited<ReturnType<typeof loadAppContinuation>>, { kind: "ready" }>["continuation"],
    });
    vi.mocked(loadSharedCsrfToken).mockResolvedValue({ kind: "ready", token: "teacher-token" });
  }

  it("completes the teacher's own bootstrap, continuation and CSRF hydration", async () => {
    configureBootstrap();
    await auth.bootstrap();
    expect(auth.user).toEqual(saved().user);
    expect(auth.profile).toEqual(saved().profile);
    expect(auth.csrfToken).toBe("teacher-token");
    expect(auth.grants).toEqual(["teacher-grant"]);
    expect(auth.featureFlags).toEqual(["teacher-flag"]);
    expect(auth.bootstrapped).toBe(true);
    expect(auth.status).toBe("ready");
  });

  it("finishes logout after its own bootstrap authenticates the teacher", async () => {
    configureBootstrap();
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
    await auth.logout();
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/v1/auth/logout"), expect.objectContaining({
      method: "POST", headers: expect.objectContaining({ "X-CSRF-Token": "teacher-token" }),
    }));
    expect(auth.user).toBeNull();
    expect(auth.profile).toBeNull();
    expect(auth.csrfToken).toBeNull();
    expect(auth.status).toBe("ready");
  });
});

const transitions = ["logout", "teacher change", "same teacher signs in again"] as const;
type Transition = typeof transitions[number];
function supersede(transition: Transition): void {
  if (transition === "logout") {
    auth.clear();
  } else {
    if (transition === "same teacher signs in again") auth.clear();
    auth.$patch({
      ...snapshotFor(transition === "teacher change" ? "teacher-b" : "teacher-a"),
      bootstrapped: true,
    });
    auth.profile!.display_name = "new login profile";
  }
}

// API ports are deferred, but the production composables and auth response
// writers run unchanged. Compare all auth state, not just the course preference.
describe.each(transitions)("pending profile responses after %s", (transition) => {
  it.each(["load", "updateProfile", "updateExamCourses"] as const)("ignores the real useProfile.%s response", async (method) => {
    const pending = deferred<ReturnType<typeof snapshotFor>>();
    vi.mocked(apiGet).mockReturnValue(pending.promise);
    vi.mocked(apiFetch).mockReturnValue(pending.promise);
    const profile = useProfile();
    const request = method === "load" ? profile.load()
      : method === "updateProfile" ? profile.updateProfile({ display_name: "old actor save" })
      : profile.updateExamCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] });
    supersede(transition);
    const state = copyAuthState();
    pending.resolve(snapshotFor("teacher-a"));
    await expect(request).rejects.toBeInstanceOf(SupersededAuthSessionError);
    expect(auth.$state).toEqual(state);
    expect(profile.profile.value).toBeNull();
  });

  it("ignores the classroom Smart preference response", async () => {
    const pending = deferred<ReturnType<typeof snapshotFor>>();
    vi.mocked(updateClassroomPlannerSettings).mockReturnValue(pending.promise);
    const lane = useClassroomPlannerSmartPreferenceLane();
    lane.persistPreference("smart_enabled", true);
    await flushPromises();
    expect(updateClassroomPlannerSettings).toHaveBeenCalledOnce();
    supersede(transition);
    const state = copyAuthState();
    pending.resolve(snapshotFor("teacher-a"));
    await lane.flushPendingChanges();
    expect(auth.$state).toEqual(state);
  });
});

it.each(["teacher change", "same teacher signs in again"] as const)("does not send a queued Smart write after %s", async (transition) => {
  const pending = deferred<ReturnType<typeof snapshotFor>>();
  vi.mocked(updateClassroomPlannerSettings)
    .mockReturnValueOnce(pending.promise)
    .mockResolvedValueOnce(snapshotFor("teacher-a"));
  const lane = useClassroomPlannerSmartPreferenceLane();
  lane.persistPreference("smart_enabled", true);
  lane.persistPreference("use_history", true);
  await flushPromises();
  expect(updateClassroomPlannerSettings).toHaveBeenCalledTimes(1);
  supersede(transition);
  const state = copyAuthState();
  pending.resolve(snapshotFor("teacher-a"));
  expect(await lane.flushPendingChanges()).toMatchObject({ status: "blocked" });
  expect(updateClassroomPlannerSettings).toHaveBeenCalledTimes(1);
  expect(auth.$state).toEqual(state);
});

it("does not accept a tutorial response from an earlier login of the same teacher", async () => {
  const pending = deferred<ReturnType<typeof snapshotFor>>();
  vi.mocked(updateClassroomPlannerSettings).mockReturnValue(pending.promise);
  useTutorialSeenSectionsStore().markSeen("planner_rules");
  supersede("same teacher signs in again");
  const state = copyAuthState();
  pending.resolve({
    ...snapshotFor("teacher-a"),
    profile: createTestProfile({ user_id: "teacher-a", classroom_planner_tutorial_seen_sections: ["planner_rules"] }),
  });
  await flushPromises();
  expect(auth.$state).toEqual(state);
});

const continuationError = { code: null, details: null, message: "old actor failure", reason: null, status: 401 };
const continuationResults = ["ready", "error", "provisioning_required", "rejected"] as const;
describe.each(transitions)("pending auth continuation after %s", (transition) => {
  it.each(continuationResults)("ignores %s result", async (kind) => {
    const pending = deferred<Awaited<ReturnType<typeof loadAppContinuation>>>();
    vi.mocked(loadAppContinuation).mockReturnValue(pending.promise);
    const request = auth.loadAppContinuation();
    supersede(transition);
    const state = copyAuthState();
    if (kind === "rejected") pending.reject(new Error("old actor network failure"));
    else if (kind === "ready") pending.resolve({
      kind, profile: snapshotFor("teacher-a").profile,
      continuation: { local_user: snapshotFor("teacher-a").user } as Extract<Awaited<ReturnType<typeof loadAppContinuation>>, { kind: "ready" }>["continuation"],
    });
    else pending.resolve({ kind, error: continuationError });
    await request.catch(() => undefined);
    expect(auth.$state).toEqual(state);
  });
});

describe.each(transitions)("pending shared bootstrap after %s", (transition) => {
  it.each(["authenticated", "anonymous", "error", "rejected"] as const)("ignores %s result", async (kind) => {
    const pending = deferred<Awaited<ReturnType<typeof loadSharedSessionSnapshot>>>();
    vi.mocked(loadSharedSessionSnapshot).mockReturnValue(pending.promise);
    vi.mocked(loadAppContinuation).mockResolvedValue({ kind: "error", error: continuationError });
    auth.bootstrapped = false;
    const request = auth.bootstrap();
    supersede(transition);
    // A replacement bootstrap may already be running, even after logout.
    // The obsolete anonymous result cannot overwrite that current status.
    auth.status = "loading";
    const state = copyAuthState();
    if (kind === "rejected") pending.reject(new Error("old bootstrap failure"));
    else if (kind === "authenticated") pending.resolve({
      kind, snapshot: { ...snapshotFor("teacher-a"), grants: ["old-grant"], featureFlags: ["old-flag"] } as Extract<Awaited<ReturnType<typeof loadSharedSessionSnapshot>>, { kind: "authenticated" }>["snapshot"],
    });
    else if (kind === "error") pending.resolve({ kind, message: "old session failure" });
    else pending.resolve({ kind });
    await request.catch(() => undefined);
    expect(auth.$state).toEqual(state);
  });
});

describe.each(["teacher change", "same teacher signs in again"] as const)("pending logout after %s", (transition) => {
  it("does not clear the replacement session when the logout response arrives", async () => {
    const pending = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pending.promise);
    auth.csrfToken = "old-token";
    const request = auth.logout();
    await flushPromises();
    supersede(transition);
    const state = copyAuthState();
    pending.resolve(new Response(null, { status: 204 }));
    await request.catch(() => undefined);
    expect(auth.$state).toEqual(state);
  });

  it("does not adopt the replacement actor after waiting for bootstrap", async () => {
    const pending = deferred<Awaited<ReturnType<typeof loadSharedSessionSnapshot>>>();
    vi.mocked(loadSharedSessionSnapshot).mockReturnValue(pending.promise);
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
    auth.bootstrapped = false;
    const request = auth.logout();
    supersede(transition);
    auth.csrfToken = "new-token";
    const state = copyAuthState();
    pending.resolve({ kind: "anonymous" });
    await request.catch(() => undefined);
    expect(fetch).not.toHaveBeenCalled();
    expect(auth.$state).toEqual(state);
  });
});

// An anonymous CSRF response clears user state; it must not clear the next
// actor. A token from an earlier request must not leak into a later session.
describe.each(["teacher change", "same teacher signs in again"] as const)("pending CSRF after %s", (transition) => {
  it.each(["anonymous", "ready", "error", "rejected"] as const)("ignores %s result", async (kind) => {
    const pending = deferred<Awaited<ReturnType<typeof loadSharedCsrfToken>>>();
    vi.mocked(loadSharedCsrfToken).mockReturnValue(pending.promise);
    const request = auth.ensureCsrfToken();
    supersede(transition);
    const state = copyAuthState();
    if (kind === "rejected") pending.reject(new Error("old csrf failure"));
    else if (kind === "ready") pending.resolve({ kind, token: "old-token" });
    else if (kind === "error") pending.resolve({ kind, message: "old csrf failure" });
    else pending.resolve({ kind });
    await request.catch(() => undefined);
    expect(auth.$state).toEqual(state);
  });
});
