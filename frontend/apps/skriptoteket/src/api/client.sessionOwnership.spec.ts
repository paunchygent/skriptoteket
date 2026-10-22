import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProfile } from "../composables/useProfile";
import { SupersededAuthSessionError, useAuthStore } from "../stores/auth";
import { createTestProfile, createTestUser, mockJsonResponse, mockSharedSessionResponse } from "../stores/authTestHelpers";
import { apiFetch, apiFetchBlob, apiFetchBlobResponse } from "./client";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

function admitTeacher(id: string, csrfToken: string | null = `${id}-csrf`) {
  const auth = useAuthStore();
  auth.clear();
  auth.$patch({
    user: createTestUser({ id, email: `${id}@example.test` }),
    profile: createTestProfile({
      user_id: id, display_name: id,
      exam_courses: { school_forms: ["grundskolan"], course_keys: [`${id}-course`] },
    }),
    sharedSessionId: `${id}-session`, csrfToken,
    grants: [`${id}-grant`], featureFlags: [`${id}-flag`],
    bootstrapped: true,
  });
  return auth;
}

function copyState() {
  return JSON.parse(JSON.stringify(useAuthStore().$state));
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  admitTeacher("teacher-a");
});

const clients = [
  { name: "JSON", request: apiFetch },
  { name: "blob", request: apiFetchBlob },
  { name: "blob response", request: apiFetchBlobResponse },
];

describe.each(clients)("$name request session ownership", ({ request }) => {
  it("still expires the originating session on its own 401 (positive control)", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ detail: "Session expired" }, 401));
    await expect(request("/api/v1/protected")).rejects.toThrow();
    const auth = useAuthStore();
    expect(auth.user).toBeNull();
    expect(auth.profile).toBeNull();
    expect(auth.csrfToken).toBeNull();
    expect(auth.grants).toEqual([]);
    expect(auth.featureFlags).toEqual([]);
  });

  it("does not expire B when A's delayed 401 arrives", async () => {
    const pending = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pending.promise);
    const result = request("/api/v1/protected").catch((error: unknown) => error);
    expect(fetch).toHaveBeenCalledOnce();
    const auth = admitTeacher("teacher-b");
    const expected = copyState();
    pending.resolve(mockJsonResponse({ detail: "A expired" }, 401));
    await result;
    expect(auth.$state).toEqual(expected);
  });

  it("never dispatches A's body with B's credentials after delayed CSRF hydration", async () => {
    const auth = admitTeacher("teacher-a", null);
    const csrf = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(csrf.promise)
      .mockResolvedValue(mockJsonResponse({ result: "must not dispatch" }));
    const result = request("/api/v1/protected", {
      method: "PATCH", body: { course_keys: ["A-only-course"] },
    }).catch((error: unknown) => error);
    expect(fetch).toHaveBeenCalledOnce();
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/auth/csrf");
    admitTeacher("teacher-b");
    const expected = copyState();
    csrf.resolve(mockJsonResponse({ csrf_token: "teacher-a-csrf" }));
    const outcome = await result;
    expect(fetch).toHaveBeenCalledOnce();
    expect(outcome).toBeInstanceOf(SupersededAuthSessionError);
    expect(auth.$state).toEqual(expected);
  });
});

describe("real useProfile.updateExamCourses through the real API client", () => {
  it("invalidates A's cached session values when profile load admits B without clear, then hydrates and saves as B", async () => {
    const auth = useAuthStore();
    const oldSession = auth.captureSession();
    const teacherB = createTestUser({ id: "teacher-b" });
    const profileB = createTestProfile({ user_id: "teacher-b" });
    const savedProfile = createTestProfile({ user_id: "teacher-b", exam_courses: {
      school_forms: ["gymnasiet"], course_keys: ["SVESVE01"],
    } });
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes("/auth/session")) return mockSharedSessionResponse("teacher-b-session");
      if (String(input).includes("/profile/app-continuation")) return mockJsonResponse({
        local_user: teacherB, profile: profileB,
      });
      if (String(input).includes("/auth/csrf")) return mockJsonResponse({ csrf_token: "b-only-csrf" });
      if (String(input).includes("/profile/exam-courses")) return mockJsonResponse({ user: teacherB, profile: savedProfile });
      return mockJsonResponse({ user: teacherB, profile: profileB });
    });
    const profile = useProfile();
    await profile.load();
    expect(auth.isCurrentSession(oldSession)).toBe(false);
    expect(auth.sharedSessionId).toBe("teacher-b-session");
    expect(auth.csrfToken).toBe("b-only-csrf");
    expect(auth.grants).toEqual([]);
    expect(auth.featureFlags).toEqual([]);
    await profile.updateExamCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] });
    expect(fetch).toHaveBeenCalledTimes(6);
    const save = vi.mocked(fetch).mock.calls.find(([url]) => String(url).includes("/profile/exam-courses"));
    expect(new Headers(save?.[1]?.headers).get("X-CSRF-Token")).toBe("b-only-csrf");
    expect(auth.csrfToken).toBe("b-only-csrf");
    expect(auth.user).toEqual(teacherB);
    expect(auth.profile).toEqual(savedProfile);
    expect(profile.profile.value).toEqual(savedProfile);
  });
  it("admits B's profile regardless of response property order when the identity changes", async () => {
    const auth = useAuthStore();
    const teacherB = createTestUser({ id: "teacher-b" });
    const profileB = createTestProfile({ user_id: "teacher-b", display_name: "B's admitted profile" });
    // JSON object field order is not an identity or session-lifetime contract.
    vi.mocked(fetch).mockImplementation(async (input) => {
      if (String(input).includes("/auth/session")) return mockSharedSessionResponse("teacher-b-session");
      if (String(input).includes("/profile/app-continuation")) return mockJsonResponse({
        local_user: teacherB, profile: profileB,
      });
      if (String(input).includes("/auth/csrf")) return mockJsonResponse({ csrf_token: "b-only-csrf" });
      return mockJsonResponse({ profile: profileB, user: teacherB });
    });
    const profile = useProfile();
    await profile.load();
    expect(auth.user).toEqual(teacherB);
    expect(auth.profile).toEqual(profileB);
    expect(profile.profile.value).toEqual(profileB);
    expect(auth.sharedSessionId).toBe("teacher-b-session");
    expect(auth.csrfToken).toBe("b-only-csrf");
    expect(auth.grants).toEqual([]);
    expect(auth.featureFlags).toEqual([]);
  });

  it("hydrates CSRF and admits its own course PATCH without ending the session (positive control)", async () => {
    const auth = admitTeacher("teacher-a", null);
    const session = auth.captureSession();
    const savedProfile = createTestProfile({ user_id: "teacher-a", exam_courses: {
      school_forms: ["gymnasiet"], course_keys: ["SVESVE01"],
    } });
    const saved = { user: auth.user, profile: savedProfile };
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "teacher-a-hydrated" }))
      .mockResolvedValueOnce(mockSharedSessionResponse("teacher-a-session"))
      .mockResolvedValueOnce(mockJsonResponse(saved));
    const profile = useProfile();
    expect(await profile.updateExamCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] }))
      .toEqual(saved);
    expect(fetch).toHaveBeenCalledTimes(3);
    const [url, options] = vi.mocked(fetch).mock.calls[2];
    expect(url).toContain("/profile/exam-courses");
    expect(options).toMatchObject({ method: "PATCH", credentials: "include",
      body: JSON.stringify({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] }),
    });
    expect(new Headers(options?.headers).get("X-CSRF-Token")).toBe("teacher-a-hydrated");
    expect(auth.profile).toEqual(savedProfile);
    expect(profile.profile.value).toEqual(savedProfile);
    expect(auth.isCurrentSession(session)).toBe(true);
  });

  it("leaves B's complete snapshot and course preferences intact after A's PATCH returns 401", async () => {
    const pending = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pending.promise);
    const profile = useProfile();
    const result = profile.updateExamCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] })
      .catch((error: unknown) => error);
    await flushPromises();
    expect(fetch).toHaveBeenCalledOnce();
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/profile/exam-courses");
    const auth = admitTeacher("teacher-b");
    const expected = copyState();
    pending.resolve(mockJsonResponse({ detail: "A expired" }, 401));
    await result;
    expect(auth.$state).toEqual(expected);
    expect(profile.profile.value).toBeNull();
  });

  it("never PATCHes A's course list after B is admitted during the real CSRF fetch", async () => {
    const auth = admitTeacher("teacher-a", null);
    const csrf = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(csrf.promise)
      .mockResolvedValue(mockJsonResponse({ user: auth.user, profile: auth.profile }));
    const profile = useProfile();
    const result = profile.updateExamCourses({ school_forms: ["gymnasiet"], course_keys: ["SVESVE01"] })
      .catch((error: unknown) => error);
    expect(fetch).toHaveBeenCalledOnce();
    expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/auth/csrf");
    admitTeacher("teacher-b", null);
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "teacher-b-hydrated" }))
      .mockResolvedValueOnce(mockSharedSessionResponse("teacher-b-session"));
    expect(await auth.ensureCsrfToken()).toBe("teacher-b-hydrated");
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(vi.mocked(fetch).mock.calls[1][0]).toContain("/auth/csrf");
    const expected = copyState();
    csrf.resolve(mockJsonResponse({ csrf_token: "teacher-a-csrf" }));
    expect(await result).toBeInstanceOf(SupersededAuthSessionError);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(auth.$state).toEqual(expected);
    expect(profile.profile.value).toBeNull();
  });
});
