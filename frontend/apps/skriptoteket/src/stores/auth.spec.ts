/**
 * Auth store bootstrap and state tests.
 *
 * Purpose:
 *   Verify Pinia auth-store state transitions, getters, and HuleEdu app
 *   continuation bootstrap behavior.
 *
 * Relationships:
 *   - `auth.csrf.spec.ts` covers shared CSRF token caching.
 *   - `auth.logout.spec.ts` covers shared HuleEdu logout behavior.
 */

import { afterEach, describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";
import { DEFAULT_PROTECTED_API_BASE_URL } from "../api/protectedApiBase";
import {
  createTestProfile,
  createTestUser,
  mockJsonResponse,
  TEST_AI_POLICY,
} from "./authTestHelpers";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
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
      expect(store.appContinuationError).toBeNull();
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
      store.appContinuationError = {
        code: "APP_CONTINUATION_FAILED",
        details: null,
        message: "Some error",
        reason: null,
        status: 503,
      };

      store.clear();

      expect(store.user).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.csrfToken).toBeNull();
      expect(store.status).toBe("ready");
      expect(store.error).toBeNull();
      expect(store.appContinuationError).toBeNull();
      expect(store.bootstrapped).toBe(true);
    });
  });

  describe("bootstrap()", () => {
    it("uses app-local continuation for local user id and RBAC on success", async () => {
      const store = useAuthStore();
      const huleEduUserId = "huleedu-provider-subject";
      const mockUser = createTestUser({
        role: "contributor",
        auth_provider: "huleedu",
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

    it("routes app-continuation through the configured protected API edge", async () => {
      vi.stubEnv("VITE_HULEEDU_PROTECTED_API_BASE_URL", DEFAULT_PROTECTED_API_BASE_URL);
      const store = useAuthStore();
      const mockUser = createTestUser({
        role: "contributor",
        auth_provider: "huleedu",
      });
      const mockProfile = createTestProfile({ user_id: mockUser.id });

      vi.mocked(fetch)
        .mockResolvedValueOnce(
          mockJsonResponse({
            authenticated: true,
            user: {
              user_id: "huleedu-provider-subject",
              email: mockUser.email,
              email_verified: true,
            },
            profile: { display_name: mockProfile.display_name, locale: mockProfile.locale },
            policy: {
              roles: ["teacher"],
              grants: [],
              feature_flags: [],
            },
            session: {
              transport: "cookie",
              csrf_required: true,
              expires_at: "2026-04-11T12:00:00Z",
            },
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

      expect(fetch).toHaveBeenNthCalledWith(
        2,
        `${DEFAULT_PROTECTED_API_BASE_URL}/v1/profile/app-continuation`,
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
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
      expect(store.status).toBe("error");
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it("preserves missing-projection app-continuation errors for deliberate routing", async () => {
      const store = useAuthStore();
      const huleEduUserId = "huleedu-unprovisioned-subject";

      vi.mocked(fetch)
        .mockResolvedValueOnce(
          mockJsonResponse({
            authenticated: true,
            user: {
              user_id: huleEduUserId,
              email: "teacher@example.test",
              email_verified: true,
            },
            profile: { display_name: "Teacher", locale: "sv-SE" },
            policy: { roles: ["teacher"], grants: [], feature_flags: [] },
            session: {
              transport: "cookie",
              csrf_required: true,
              expires_at: "2026-04-11T12:00:00Z",
            },
          }),
        )
        .mockResolvedValueOnce(
          mockJsonResponse(
            {
              error: {
                code: "UNAUTHORIZED",
                message: "Skriptoteket-kontot är inte aktiverat.",
                details: {
                  reason: "missing_huleedu_app_projection",
                  subject: huleEduUserId,
                },
              },
            },
            401,
            "Unauthorized",
          ),
        );

      await store.bootstrap();

      expect(store.user).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.aiPolicy).toBeNull();
      expect(store.status).toBe("provisioning_required");
      expect(store.isProvisioningRequired).toBe(true);
      expect(store.error).toBe("Skriptoteket-kontot är inte aktiverat.");
      expect(store.appContinuationError).toEqual(
        expect.objectContaining({
          code: "UNAUTHORIZED",
          status: 401,
          reason: "missing_huleedu_app_projection",
        }),
      );
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it("keeps invalid product context as a generic auth error", async () => {
      const store = useAuthStore();

      vi.mocked(fetch)
        .mockResolvedValueOnce(
          mockJsonResponse({
            authenticated: true,
            user: {
              user_id: "huleedu-wrong-context-subject",
              email: "teacher@example.test",
              email_verified: true,
            },
            profile: { display_name: "Teacher", locale: "sv-SE" },
            policy: { roles: ["teacher"], grants: [], feature_flags: [] },
            session: {
              transport: "cookie",
              csrf_required: true,
              expires_at: "2026-04-11T12:00:00Z",
            },
          }),
        )
        .mockResolvedValueOnce(
          mockJsonResponse(
            {
              error: {
                code: "UNAUTHORIZED",
                message: "Inloggningen kunde inte slutföras.",
                details: {
                  reason: "invalid_huleedu_product_context",
                  field: "active_product_identity_realm",
                },
              },
            },
            401,
            "Unauthorized",
          ),
        );

      await store.bootstrap();

      expect(store.user).toBeNull();
      expect(store.profile).toBeNull();
      expect(store.aiPolicy).toBeNull();
      expect(store.status).toBe("error");
      expect(store.isProvisioningRequired).toBe(false);
      expect(store.error).toBe("Inloggningen kunde inte slutföras.");
      expect(store.appContinuationError).toEqual(
        expect.objectContaining({
          code: "UNAUTHORIZED",
          status: 401,
          reason: "invalid_huleedu_product_context",
        }),
      );
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
