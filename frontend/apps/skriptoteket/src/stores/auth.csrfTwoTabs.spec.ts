import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { apiFetch } from "../api/client";
import { useAuthStore } from "./auth";
import { createTestProfile, createTestUser, mockJsonResponse, mockSharedSessionResponse } from "./authTestHelpers";

let sharedSession: string;
let csrfCounter: number;
let csrfCalls: number;
let forbiddenCount: number;
let writes: string[];

function readCsrfCookie(): string | null {
  const part = document.cookie
    .split(";")
    .map((segment) => segment.trim())
    .find((segment) => segment.startsWith("huleedu_csrf="));
  if (!part) return null;
  const value = part.slice("huleedu_csrf=".length);
  return value ? value : null;
}

beforeEach(() => {
  setActivePinia(createPinia());
  sharedSession = "session-a";
  csrfCounter = 0;
  csrfCalls = 0;
  forbiddenCount = 0;
  writes = [];
  document.cookie = "huleedu_csrf=login-token; path=/";
  vi.mocked(fetch).mockReset().mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/auth/session")) return mockSharedSessionResponse(sharedSession);
    if (url.endsWith("/auth/csrf")) {
      csrfCounter += 1;
      csrfCalls += 1;
      const token = `token-${csrfCounter}`;
      document.cookie = `huleedu_csrf=${token}; path=/`;
      return mockJsonResponse({ csrf_token: token });
    }
    if (url.endsWith("/profile/app-continuation")) return mockJsonResponse({
      local_user: createTestUser({ id: sharedSession }), profile: createTestProfile(),
    });
    if (init?.method === "PUT" || init?.method === "POST") {
      if (new Headers(init.headers).get("X-CSRF-Token") !== readCsrfCookie()) {
        forbiddenCount += 1;
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

afterEach(() => {
  document.cookie = "huleedu_csrf=; max-age=0; path=/";
});

it("two tabs holding exam locks renew on the first try without rotating the shared token", async () => {
  const piniaA = createPinia();
  setActivePinia(piniaA);
  await useAuthStore().bootstrap();
  const piniaB = createPinia();
  setActivePinia(piniaB);
  await useAuthStore().bootstrap();
  for (let round = 0; round < 4; round += 1) {
    setActivePinia(piniaA);
    await apiFetch("/api/v1/lock/renew", { method: "POST", body: {} });
    setActivePinia(piniaB);
    await apiFetch("/api/v1/lock/renew", { method: "POST", body: {} });
  }
  expect(forbiddenCount).toBe(0);
  expect(writes).toHaveLength(8);
  expect(csrfCalls).toBe(0);
});

it("a tab with no readable cookie acquires a token on its first write", async () => {
  document.cookie = "huleedu_csrf=; max-age=0; path=/";
  setActivePinia(createPinia());
  await useAuthStore().bootstrap();
  await apiFetch("/api/v1/lock/renew", { method: "POST", body: {} });
  expect(writes).toHaveLength(1);
  expect(csrfCalls).toBe(1);
});

it("an outdated tab does not dispatch a write after the shared session changes", async () => {
  setActivePinia(createPinia());
  const tabA = useAuthStore();
  await tabA.bootstrap();
  const sessionA = tabA.captureSession();
  await apiFetch("/api/v1/write", { method: "PUT", body: { title: "A draft" }, session: sessionA });
  expect(writes).toEqual(["session-a"]);
  sharedSession = "session-b";
  document.cookie = "huleedu_csrf=token-b; path=/";
  await expect(apiFetch("/api/v1/write", { method: "PUT", body: { title: "A draft" }, session: sessionA }))
    .rejects.toThrow();
  expect(writes).toEqual(["session-a"]);
  expect(tabA.isCurrentSession(sessionA)).toBe(false);
  expect(tabA.user).toBeNull();
  expect(tabA.sharedSessionId).toBeNull();
  expect(tabA.csrfToken).toBeNull();
});
