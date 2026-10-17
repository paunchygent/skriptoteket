import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";

import { apiFetch } from "../api/client";
import { useProfile } from "../composables/useProfile";
import { SupersededAuthSessionError, useAuthStore } from "./auth";
import { createTestProfile, createTestUser, mockJsonResponse, mockSharedSessionResponse } from "./authTestHelpers";

let sharedSession: string;
let sharedToken: string;
let writes: string[];

beforeEach(() => {
  setActivePinia(createPinia());
  sharedSession = "session-a";
  sharedToken = "token-a";
  writes = [];
  vi.mocked(fetch).mockReset().mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/auth/session")) return mockSharedSessionResponse(sharedSession);
    if (url.endsWith("/auth/csrf")) return mockJsonResponse({ csrf_token: sharedToken });
    if (url.endsWith("/profile/app-continuation")) return mockJsonResponse({
      local_user: createTestUser({ id: sharedSession }), profile: createTestProfile(), ai_policy: null,
    });
    if (init?.method === "PUT" || init?.method === "POST") {
      if (new Headers(init.headers).get("X-CSRF-Token") !== sharedToken) {
        return mockJsonResponse({ error: {
          code: "AUTHORIZATION_ERROR", message: "CSRF token required for browser session write",
        } }, 403);
      }
      writes.push(sharedSession);
      return mockJsonResponse({ writtenAs: sharedSession });
    }
    throw new Error(`Unexpected request ${url}`);
  });
});

it("retires A after a refused recovery and blocks the identical A-bound write on its next attempt", async () => {
  const auth = useAuthStore();
  await auth.bootstrap();
  const sessionA = auth.captureSession();
  sharedSession = "session-b";
  sharedToken = "token-b";
  const write = () => apiFetch("/api/v1/write", { method: "PUT", body: { title: "A draft" }, session: sessionA });

  await expect(write()).rejects.toThrow();
  await expect(write()).rejects.toBeInstanceOf(SupersededAuthSessionError);
  expect(writes).toEqual([]);
  expect(auth.isCurrentSession(sessionA)).toBe(false);
  expect(auth.user).toBeNull();
  expect(auth.sharedSessionId).toBeNull();
  expect(auth.csrfToken).toBeNull();
});

it.each(["write", "logout"])("checks continuity on uncached initial acquisition for %s", async (operation) => {
  const auth = useAuthStore();
  await auth.bootstrap();
  const sessionA = auth.captureSession();
  auth.csrfToken = null;
  sharedSession = "session-b";
  sharedToken = "token-b";

  if (operation === "logout") await auth.logout();
  else await expect(apiFetch("/api/v1/write", { method: "PUT", body: { title: "A draft" }, session: sessionA })).rejects.toThrow();
  expect(writes).toEqual([]);
  expect(auth.isCurrentSession(sessionA)).toBe(false);
  expect(auth.user).toBeNull();
  expect(auth.csrfToken).toBeNull();
});

it("refuses to admit a changed identity from a mutation response", async () => {
  const auth = useAuthStore();
  await auth.bootstrap();
  const sessionA = auth.captureSession();
  vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({
    user: createTestUser({ id: "session-b" }), profile: createTestProfile({ user_id: "session-b" }),
  }));
  await expect(useProfile().updateExamCourses({ school_forms: ["gymnasiet"], course_keys: [] }))
    .rejects.toBeInstanceOf(SupersededAuthSessionError);
  expect(auth.isCurrentSession(sessionA)).toBe(false);
  expect(auth.user).toBeNull();
  expect(auth.sharedSessionId).toBeNull();
  expect(auth.csrfToken).toBeNull();
});

it("rejects a changed-identity profile read when authoritative bootstrap names a different user", async () => {
  const auth = useAuthStore();
  await auth.bootstrap();
  sharedSession = "session-c";
  sharedToken = "token-c";
  vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({
    user: createTestUser({ id: "session-b" }), profile: createTestProfile({ user_id: "session-b" }),
  }));
  const profile = useProfile();
  await expect(profile.load()).rejects.toBeInstanceOf(SupersededAuthSessionError);
  expect(profile.profile.value).toBeNull();
  expect(auth.user?.id).toBe("session-c");
  expect(auth.sharedSessionId).toBe("session-c");
  expect(auth.csrfToken).toBe("token-c");
});

it("admits B on a fresh tab load after replacement", async () => {
  await useAuthStore().bootstrap();
  sharedSession = "session-b";
  sharedToken = "token-b";
  setActivePinia(createPinia());
  const freshTab = useAuthStore();
  await freshTab.bootstrap();
  expect(freshTab.user?.id).toBe("session-b");
  expect(freshTab.sharedSessionId).toBe("session-b");
  expect(freshTab.csrfToken).toBe("token-b");
  await apiFetch("/api/v1/write", { method: "PUT", body: { title: "B draft" }, session: freshTab.captureSession() });
  expect(writes).toEqual(["session-b"]);
});

it("recovers a same-session rotation once and keeps the admitted lifetime", async () => {
  const auth = useAuthStore();
  await auth.bootstrap();
  const sessionA = auth.captureSession();
  sharedToken = "rotated-a";
  vi.mocked(fetch).mockClear();
  await apiFetch("/api/v1/write", { method: "PUT", body: { title: "A draft" }, session: sessionA });
  expect(writes).toEqual(["session-a"]);
  expect(auth.isCurrentSession(sessionA)).toBe(true);
  expect(auth.csrfToken).toBe("rotated-a");
  expect(vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(2);
});
