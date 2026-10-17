/**
 * Auth store local state and getter tests.
 *
 * Purpose:
 *   Verify initial Pinia auth-store state, role/display getters, and clearing
 *   local authentication state without network operations.
 *
 * Relationships:
 *   - `auth.bootstrap.spec.ts` covers shared-session and app-continuation bootstrap.
 *   - `auth.csrf.spec.ts` covers shared CSRF token caching.
 *   - `auth.logout.spec.ts` covers shared HuleEdu logout behavior.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "./auth";
import { createTestProfile, createTestUser } from "./authTestHelpers";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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

});
