/**
 * Auth store shared CSRF tests.
 *
 * Purpose:
 *   Verify the Pinia auth store fetches and caches HuleEdu-owned shared CSRF
 *   tokens according to the browser-session contract.
 *
 * Relationships:
 *   - `auth.ts` owns the browser-visible auth state.
 *   - `auth.logout.spec.ts` verifies unsafe logout writes consume these tokens.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";
import {
  createTestUser,
  mockEmptyResponse,
  mockJsonResponse,
} from "./authTestHelpers";

describe("useAuthStore.ensureCsrfToken", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
  });

  it("returns cached token if available", async () => {
    const store = useAuthStore();
    store.user = createTestUser();
    store.csrfToken = "cached-token";

    const token = await store.ensureCsrfToken();

    expect(token).toBe("cached-token");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("returns null if no user", async () => {
    const store = useAuthStore();

    const token = await store.ensureCsrfToken();

    expect(token).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("fetches token from API if not cached", async () => {
    const store = useAuthStore();
    store.user = createTestUser();

    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "new-token" }));

    const token = await store.ensureCsrfToken();

    expect(token).toBe("new-token");
    expect(store.csrfToken).toBe("new-token");
    expect(fetch).toHaveBeenCalledWith(
      "https://api.hule.education/v1/auth/csrf",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      }),
    );
  });

  it("clears user on 401 response", async () => {
    const store = useAuthStore();
    store.user = createTestUser();

    vi.mocked(fetch).mockResolvedValueOnce(mockEmptyResponse(401));

    const token = await store.ensureCsrfToken();

    expect(token).toBeNull();
    expect(store.user).toBeNull();
    expect(store.csrfToken).toBeNull();
  });
});
