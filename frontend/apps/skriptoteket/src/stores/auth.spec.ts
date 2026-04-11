import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";
import type { components } from "../api/openapi";

type ApiUser = components["schemas"]["User"];
type ApiUserProfile = components["schemas"]["UserProfile"];

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

const TEST_AI_POLICY = {
  remote_providers_enabled: true,
  completion_external_available: true,
  completion_local_available: true,
};

function mockJsonResponse(
  payload: unknown,
  status = 200,
  statusText?: string,
): Response {
  return new Response(JSON.stringify(payload), {
    status,
    statusText,
    headers: { "content-type": "application/json" },
  });
}

function mockEmptyResponse(status: number, statusText?: string): Response {
  return new Response(null, { status, statusText });
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

      vi.mocked(fetch).mockResolvedValueOnce(
        mockJsonResponse({ csrf_token: "new-token" }),
      );

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

  describe("login()", () => {
    it("sets user and profile on success", async () => {
      const store = useAuthStore();
      const mockUser = createTestUser();
      const mockProfile = createTestProfile({ display_name: "Test User" });

      vi.mocked(fetch).mockResolvedValueOnce(
        mockJsonResponse({
          user: mockUser,
          profile: mockProfile,
          csrf_token: "new-csrf-token",
        }),
      );

      await store.login({ email: "test@test.com", password: "password" });

      expect(store.user).toEqual(mockUser);
      expect(store.profile).toEqual(mockProfile);
      expect(store.csrfToken).toBe("new-csrf-token");
      expect(store.status).toBe("ready");
      expect(store.bootstrapped).toBe(true);
    });

    it("throws and sets error on failure", async () => {
      const store = useAuthStore();

      vi.mocked(fetch).mockResolvedValueOnce(
        mockJsonResponse(
          {
            error: { code: "INVALID_CREDENTIALS", message: "Invalid email or password" },
          },
          401,
          "Unauthorized",
        ),
      );

      await expect(store.login({ email: "test@test.com", password: "wrong" })).rejects.toThrow(
        "Invalid email or password"
      );

      expect(store.status).toBe("error");
      expect(store.error).toBe("Invalid email or password");
      expect(store.user).toBeNull();
    });

    it("preserves api error codes for unverified email login failures", async () => {
      const store = useAuthStore();

      vi.mocked(fetch).mockResolvedValueOnce(
        mockJsonResponse(
          {
            error: {
              code: "EMAIL_NOT_VERIFIED",
              message: "Verifiera din e-postadress innan du loggar in",
            },
            correlation_id: "corr-123",
          },
          401,
          "Unauthorized",
        ),
      );

      await expect(store.login({ email: "test@test.com", password: "password" })).rejects.toEqual(
        expect.objectContaining({
          code: "EMAIL_NOT_VERIFIED",
          message: "Verifiera din e-postadress innan du loggar in",
          correlationId: "corr-123",
          status: 401,
        }),
      );

      expect(store.status).toBe("error");
      expect(store.error).toBe("Verifiera din e-postadress innan du loggar in");
    });
  });

  describe("register()", () => {
    it("keeps the client unauthenticated after successful registration", async () => {
      const store = useAuthStore();
      const mockUser = createTestUser({ email_verified: false });
      const mockProfile = createTestProfile({ first_name: "Test" });

      vi.mocked(fetch).mockResolvedValueOnce(
        mockJsonResponse({
          user: mockUser,
          profile: mockProfile,
          message: "Konto skapat! Kontrollera din e-post för att verifiera kontot.",
        }),
      );

      const result = await store.register({
        email: "test@test.com",
        password: "password-123",
        firstName: "Test",
        lastName: "User",
      });

      expect(result.message).toBe("Konto skapat! Kontrollera din e-post för att verifiera kontot.");
      expect(store.user).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.csrfToken).toBeNull();
      expect(store.isAuthenticated).toBe(false);
      expect(store.status).toBe("ready");
      expect(store.bootstrapped).toBe(true);
    });
  });

  describe("logout()", () => {
    it("clears state on 204 response", async () => {
      const store = useAuthStore();
      store.user = createTestUser();
      store.csrfToken = "token";
      store.bootstrapped = true;

      vi.mocked(fetch).mockResolvedValueOnce(mockEmptyResponse(204));

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

      vi.mocked(fetch).mockResolvedValueOnce(mockEmptyResponse(401));

      await store.logout();

      expect(store.user).toBeNull();
      expect(store.status).toBe("ready");
    });
  });

  describe("bootstrap()", () => {
    it("uses app-local continuation for local user id and RBAC on success", async () => {
      const store = useAuthStore();
      const huleEduUserId = "huleedu-provider-subject";
      const mockUser = createTestUser({
        role: "contributor",
        auth_provider: "huleedu",
        external_id: huleEduUserId,
      });
      const mockProfile = createTestProfile({ user_id: mockUser.id });

      vi.mocked(fetch)
        .mockResolvedValueOnce(
          mockJsonResponse({
            authenticated: true,
            user: { user_id: huleEduUserId, email: mockUser.email, email_verified: true },
            profile: { display_name: mockProfile.display_name, locale: mockProfile.locale },
            policy: {
              roles: ["teacher", "external-admin"],
              grants: ["tools:run"],
              feature_flags: ["inline-completion"],
            },
            session: { transport: "cookie", csrf_required: true, expires_at: "2026-04-11T12:00:00Z" },
          }),
        )
        .mockResolvedValueOnce(
          mockJsonResponse({
            local_user: mockUser,
            profile: mockProfile,
            ai_policy: TEST_AI_POLICY,
            allow_remote_fallback: true,
            inline_completion_provider: "external",
          }),
        )
        .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "csrf-token" }));

      await store.bootstrap();

      expect(store.user).toEqual(
        expect.objectContaining({
          id: mockUser.id,
          email: mockUser.email,
          role: mockUser.role,
          auth_provider: "huleedu",
          external_id: huleEduUserId,
        }),
      );
      expect(store.user?.id).not.toBe(huleEduUserId);
      expect(store.hasAtLeastRole("contributor")).toBe(true);
      expect(store.grants).toEqual(["tools:run"]);
      expect(store.featureFlags).toEqual(["inline-completion"]);
      expect(store.aiPolicy).toEqual(TEST_AI_POLICY);
      expect(store.profile).toEqual(
        expect.objectContaining({
          user_id: mockUser.id,
          allow_remote_fallback: true,
          inline_completion_provider: "external",
        }),
      );
      expect(fetch).toHaveBeenNthCalledWith(
        1,
        "https://api.hule.education/v1/auth/session",
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
      expect(fetch).toHaveBeenNthCalledWith(
        2,
        "/api/v1/profile/app-continuation",
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
      expect(fetch).toHaveBeenNthCalledWith(
        3,
        "https://api.hule.education/v1/auth/csrf",
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
      expect(store.bootstrapped).toBe(true);
      expect(store.status).toBe("ready");
    });

    it("sets ready state when not logged in", async () => {
      const store = useAuthStore();

      vi.mocked(fetch).mockResolvedValueOnce(
        mockJsonResponse({
          authenticated: false,
          user: null,
          profile: null,
          policy: {
            roles: [],
            grants: [],
            feature_flags: [],
          },
          session: {
            transport: "cookie",
            csrf_required: true,
            expires_at: null,
          },
        }),
      );

      await store.bootstrap();

      expect(store.user).toBeNull();
      expect(fetch).toHaveBeenCalledTimes(1);
      expect(store.bootstrapped).toBe(true);
      expect(store.status).toBe("ready");
      expect(store.error).toBeNull();
    });

    it("keeps remote AI failed closed when app-local continuation fails", async () => {
      const store = useAuthStore();
      const mockUser = createTestUser();

      vi.mocked(fetch)
        .mockResolvedValueOnce(
          mockJsonResponse({
            authenticated: true,
            user: { user_id: mockUser.id, email: mockUser.email, email_verified: true },
            profile: { display_name: null, locale: "sv-SE" },
            policy: { roles: [mockUser.role], grants: [], feature_flags: [] },
            session: { transport: "cookie", csrf_required: true, expires_at: "2026-04-11T12:00:00Z" },
          }),
        )
        .mockResolvedValueOnce(
          mockJsonResponse(
            { error: { code: "APP_CONTINUATION_FAILED", message: "Local app state unavailable" } },
            503,
            "Service Unavailable",
          ),
        );

      await store.bootstrap();

      expect(store.user).toBeNull();
      expect(store.aiPolicy).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.error).toBe("Local app state unavailable");
      expect(store.status).toBe("ready");
      expect(fetch).toHaveBeenCalledTimes(2);
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
