import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";
import type { components } from "../api/openapi";

type ApiUser = components["schemas"]["User"];
type ApiUserProfile = components["schemas"]["UserProfile"];

// Test factory - creates minimal user for testing
function createTestUser(overrides: Partial<ApiUser> = {}): ApiUser {
  return {
    id: "550e8400-e29b-41d4-a716-446655440000",
    email: "test@test.com",
    role: "user",
    auth_provider: "local",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    email_verified: true,
    failed_login_attempts: 0,
    is_active: true,
    ...overrides,
  };
}

// Test factory - creates minimal profile for testing
function createTestProfile(overrides: Partial<ApiUserProfile> = {}): ApiUserProfile {
  return {
    user_id: "550e8400-e29b-41d4-a716-446655440000",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    locale: "sv-SE",
    display_name: null,
    first_name: null,
    last_name: null,
    ...overrides,
  };
}

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
  });

  describe("initial state", () => {
    it("starts with no user and idle status", () => {
      const store = useAuthStore();

      expect(store.user).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.csrfToken).toBeNull();
      expect(store.bootstrapped).toBe(false);
      expect(store.status).toBe("idle");
      expect(store.error).toBeNull();
    });
  });

  describe("getters", () => {
    describe("isAuthenticated", () => {
      it("returns false when no user", () => {
        const store = useAuthStore();
        expect(store.isAuthenticated).toBe(false);
      });

      it("returns true when user is set", () => {
        const store = useAuthStore();
        store.user = createTestUser();
        expect(store.isAuthenticated).toBe(true);
      });
    });

    describe("role", () => {
      it("returns null when no user", () => {
        const store = useAuthStore();
        expect(store.role).toBeNull();
      });

      it("returns user role when authenticated", () => {
        const store = useAuthStore();
        store.user = createTestUser({ role: "admin" });
        expect(store.role).toBe("admin");
      });
    });

    describe("hasAtLeastRole", () => {
      it("returns false when no user", () => {
        const store = useAuthStore();
        expect(store.hasAtLeastRole("user")).toBe(false);
        expect(store.hasAtLeastRole("admin")).toBe(false);
      });

      it("returns true for same role", () => {
        const store = useAuthStore();
        store.user = createTestUser({ role: "contributor" });
        expect(store.hasAtLeastRole("contributor")).toBe(true);
      });

      it("returns true for lower role", () => {
        const store = useAuthStore();
        store.user = createTestUser({ role: "admin" });
        expect(store.hasAtLeastRole("user")).toBe(true);
        expect(store.hasAtLeastRole("contributor")).toBe(true);
      });

      it("returns false for higher role", () => {
        const store = useAuthStore();
        store.user = createTestUser({ role: "user" });
        expect(store.hasAtLeastRole("contributor")).toBe(false);
        expect(store.hasAtLeastRole("admin")).toBe(false);
      });

      it("follows role hierarchy: user < contributor < admin < superuser", () => {
        const store = useAuthStore();

        // Superuser has all roles
        store.user = createTestUser({ role: "superuser" });
        expect(store.hasAtLeastRole("user")).toBe(true);
        expect(store.hasAtLeastRole("contributor")).toBe(true);
        expect(store.hasAtLeastRole("admin")).toBe(true);
        expect(store.hasAtLeastRole("superuser")).toBe(true);

        // User has only user role
        store.user = createTestUser({ role: "user" });
        expect(store.hasAtLeastRole("user")).toBe(true);
        expect(store.hasAtLeastRole("contributor")).toBe(false);
        expect(store.hasAtLeastRole("admin")).toBe(false);
        expect(store.hasAtLeastRole("superuser")).toBe(false);
      });
    });

    describe("displayName", () => {
      it("returns null when no user", () => {
        const store = useAuthStore();
        expect(store.displayName).toBeNull();
      });

      it("returns profile display_name if available", () => {
        const store = useAuthStore();
        store.user = createTestUser();
        store.profile = createTestProfile({
          display_name: "Custom Name",
          first_name: "Test",
          last_name: "User",
        });
        expect(store.displayName).toBe("Custom Name");
      });

      it("falls back to first_name if no display_name", () => {
        const store = useAuthStore();
        store.user = createTestUser();
        store.profile = createTestProfile({
          display_name: null,
          first_name: "John",
          last_name: "Doe",
        });
        expect(store.displayName).toBe("John");
      });

      it("falls back to email username if no profile", () => {
        const store = useAuthStore();
        store.user = createTestUser({ email: "john.doe@example.com" });
        expect(store.displayName).toBe("john.doe");
      });
    });
  });

  describe("clear()", () => {
    it("resets all state", () => {
      const store = useAuthStore();
      store.user = createTestUser();
      store.profile = createTestProfile({ display_name: "Test" });
      store.csrfToken = "token";
      store.status = "loading";
      store.error = "Some error";

      store.clear();

      expect(store.user).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.csrfToken).toBeNull();
      expect(store.status).toBe("ready");
      expect(store.error).toBeNull();
      expect(store.bootstrapped).toBe(true);
    });
  });

  describe("ensureCsrfToken()", () => {
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

      vi.mocked(fetch).mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve({ csrf_token: "new-token" }),
      } as Response);

      const token = await store.ensureCsrfToken();

      expect(token).toBe("new-token");
      expect(store.csrfToken).toBe("new-token");
      expect(fetch).toHaveBeenCalledWith("/api/v1/auth/csrf", {
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
    });

    it("clears user on 401 response", async () => {
      const store = useAuthStore();
      store.user = createTestUser();

      vi.mocked(fetch).mockResolvedValueOnce({
        status: 401,
      } as Response);

      const token = await store.ensureCsrfToken();

      expect(token).toBeNull();
      expect(store.user).toBeNull();
      expect(store.csrfToken).toBeNull();
    });
  });

  describe("login()", () => {
    it("sets user and profile on success", async () => {
      const store = useAuthStore();
      const mockUser = createTestUser();
      const mockProfile = createTestProfile({ display_name: "Test User" });

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: mockUser,
            profile: mockProfile,
            csrf_token: "new-csrf-token",
          }),
      } as Response);

      await store.login({ email: "test@test.com", password: "password" });

      expect(store.user).toEqual(mockUser);
      expect(store.profile).toEqual(mockProfile);
      expect(store.csrfToken).toBe("new-csrf-token");
      expect(store.status).toBe("ready");
      expect(store.bootstrapped).toBe(true);
    });

    it("throws and sets error on failure", async () => {
      const store = useAuthStore();

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        headers: new Headers({ "content-type": "application/json" }),
        json: () =>
          Promise.resolve({
            error: { code: "INVALID_CREDENTIALS", message: "Invalid email or password" },
          }),
      } as Response);

      await expect(store.login({ email: "test@test.com", password: "wrong" })).rejects.toThrow(
        "Invalid email or password"
      );

      expect(store.status).toBe("error");
      expect(store.error).toBe("Invalid email or password");
      expect(store.user).toBeNull();
    });
  });

  describe("logout()", () => {
    it("clears state on 204 response", async () => {
      const store = useAuthStore();
      store.user = createTestUser();
      store.csrfToken = "token";
      store.bootstrapped = true;

      vi.mocked(fetch).mockResolvedValueOnce({
        status: 204,
      } as Response);

      await store.logout();

      expect(store.user).toBeNull();
      expect(store.csrfToken).toBeNull();
      expect(store.status).toBe("ready");
    });

    it("clears state on 401 response (already logged out)", async () => {
      const store = useAuthStore();
      store.user = createTestUser();
      store.csrfToken = "token";
      store.bootstrapped = true;

      vi.mocked(fetch).mockResolvedValueOnce({
        status: 401,
      } as Response);

      await store.logout();

      expect(store.user).toBeNull();
      expect(store.status).toBe("ready");
    });
  });

  describe("bootstrap()", () => {
    it("fetches user info on success", async () => {
      const store = useAuthStore();
      const mockUser = createTestUser();
      const mockProfile = createTestProfile();

      vi.mocked(fetch)
        .mockResolvedValueOnce({
          status: 200,
          json: () =>
            Promise.resolve({
              user: mockUser,
              profile: mockProfile,
            }),
        } as Response)
        .mockResolvedValueOnce({
          status: 200,
          json: () => Promise.resolve({ csrf_token: "csrf-token" }),
        } as Response);

      await store.bootstrap();

      expect(store.user).toEqual(mockUser);
      expect(store.bootstrapped).toBe(true);
      expect(store.status).toBe("ready");
    });

    it("sets ready state on 401 (not logged in)", async () => {
      const store = useAuthStore();

      vi.mocked(fetch).mockResolvedValueOnce({
        status: 401,
      } as Response);

      await store.bootstrap();

      expect(store.user).toBeNull();
      expect(store.bootstrapped).toBe(true);
      expect(store.status).toBe("ready");
      expect(store.error).toBeNull();
    });

    it("skips if already bootstrapped", async () => {
      const store = useAuthStore();
      store.bootstrapped = true;

      await store.bootstrap();

      expect(fetch).not.toHaveBeenCalled();
    });

    it("sets error state on network failure", async () => {
      const store = useAuthStore();

      vi.mocked(fetch).mockRejectedValueOnce(new Error("Network error"));

      await store.bootstrap();

      expect(store.user).toBeNull();
      expect(store.bootstrapped).toBe(true);
      expect(store.status).toBe("error");
      expect(store.error).toBe("Network error");
    });
  });
});
