/**
 * Auth store shared logout tests.
 *
 * Purpose:
 *   Verify Skriptoteket logout follows the HuleEdu-owned browser-session
 *   contract for unsafe writes, including CSRF header submission and stale-token
 *   recovery.
 *
 * Relationships:
 *   - `auth.ts` owns the logout action called by the authenticated app shell.
 *   - `auth.csrf.spec.ts` covers shared CSRF token retrieval in isolation.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";
import {
  createTestUser,
  mockEmptyResponse,
  mockJsonResponse,
} from "./authTestHelpers";

describe("useAuthStore.logout", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
  });

  it("clears state on successful HuleEdu logout response", async () => {
    const store = useAuthStore();
    store.user = createTestUser();
    store.csrfToken = "token";
    store.bootstrapped = true;

    vi.mocked(fetch).mockResolvedValueOnce(
      mockJsonResponse({ message: "Logout successful" }),
    );

    await store.logout();

    expect(store.user).toBeNull();
    expect(store.csrfToken).toBeNull();
    expect(store.status).toBe("ready");
    expect(fetch).toHaveBeenCalledWith(
      "https://api.hule.education/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": "token",
        },
      }),
    );
  });

  it("clears state on 401 response when already logged out", async () => {
    const store = useAuthStore();
    store.user = createTestUser();
    store.csrfToken = "token";
    store.bootstrapped = true;

    vi.mocked(fetch).mockResolvedValueOnce(mockEmptyResponse(401));

    await store.logout();

    expect(store.user).toBeNull();
    expect(store.status).toBe("ready");
  });

  it("fetches shared CSRF before logout when no token is cached", async () => {
    const store = useAuthStore();
    store.user = createTestUser();
    store.bootstrapped = true;

    vi.mocked(fetch)
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh-token" }))
      .mockResolvedValueOnce(mockEmptyResponse(204));

    await store.logout();

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "https://api.hule.education/v1/auth/csrf",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "https://api.hule.education/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": "fresh-token",
        },
      }),
    );
    expect(store.user).toBeNull();
    expect(store.csrfToken).toBeNull();
  });

  it("refreshes stale CSRF and retries logout once after a 403", async () => {
    const store = useAuthStore();
    store.user = createTestUser();
    store.csrfToken = "stale-token";
    store.bootstrapped = true;

    vi.mocked(fetch)
      .mockResolvedValueOnce(mockEmptyResponse(403))
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh-token" }))
      .mockResolvedValueOnce(mockEmptyResponse(204));

    await store.logout();

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "https://api.hule.education/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": "stale-token",
        },
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "https://api.hule.education/v1/auth/csrf",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      3,
      "https://api.hule.education/v1/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "X-CSRF-Token": "fresh-token",
        },
      }),
    );
    expect(store.user).toBeNull();
    expect(store.csrfToken).toBeNull();
  });
});
