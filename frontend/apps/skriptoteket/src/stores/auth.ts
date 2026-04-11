/**
 * SPA auth store for HuleEdu session bootstrap and local app continuation.
 *
 * This store owns the browser-visible auth snapshot, delegates browser session
 * proof to HuleEdu, and hydrates Skriptoteket-only app state through a separate
 * local continuation endpoint.
 */

import { defineStore } from "pinia";

import { fetchWithTimeout, readAuthError, readErrorMessage } from "../api/authHttp";
import type { components } from "../api/openapi";
import { type AuthProfile, type AuthUser } from "../api/sharedAuth";
import {
  loadAppContinuation as requestAppContinuation,
  loadSharedCsrfToken,
  loadSharedSessionSnapshot,
} from "./authBootstrap";

type ApiRole = components["schemas"]["Role"];
type ApiAiPolicy = components["schemas"]["AiPolicyResponse"];
type LoginResponse = components["schemas"]["LoginResponse"];
type RegisterResponse = components["schemas"]["RegisterResponse"];

type AuthStatus = "idle" | "loading" | "ready" | "error";

const ROLE_RANK: Record<ApiRole, number> = {
  user: 0,
  contributor: 1,
  admin: 2,
  superuser: 3,
};

function hasAtLeastRole(params: { actual: ApiRole; minRole: ApiRole }): boolean {
  return ROLE_RANK[params.actual] >= ROLE_RANK[params.minRole];
}

let bootstrapPromise: Promise<void> | null = null;

type AuthState = {
  user: AuthUser | null;
  profile: AuthProfile | null;
  aiPolicy: ApiAiPolicy | null;
  grants: string[];
  featureFlags: string[];
  csrfToken: string | null;
  bootstrapped: boolean;
  status: AuthStatus;
  error: string | null;
};

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    profile: null,
    aiPolicy: null,
    grants: [],
    featureFlags: [],
    csrfToken: null,
    bootstrapped: false,
    status: "idle",
    error: null,
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null,
    role: (state) => state.user?.role ?? null,
    hasAtLeastRole: (state) => {
      return (minRole: ApiRole): boolean => {
        if (!state.user) {
          return false;
        }
        return hasAtLeastRole({ actual: state.user.role, minRole });
      };
    },
    hasGrant: (state) => {
      return (grant: string): boolean => state.grants.includes(grant);
    },
    hasFeatureFlag: (state) => {
      return (featureFlag: string): boolean => state.featureFlags.includes(featureFlag);
    },
    displayName: (state): string | null => {
      if (!state.user) return null;
      if (state.profile?.display_name) return state.profile.display_name;
      if (state.profile?.first_name) return state.profile.first_name;
      return state.user.email.split("@")[0];
    },
  },
  actions: {
    clear(): void {
      this.user = null;
      this.profile = null;
      this.aiPolicy = null;
      this.grants = [];
      this.featureFlags = [];
      this.csrfToken = null;
      this.status = "ready";
      this.error = null;
      this.bootstrapped = true;
    },
    async bootstrap(): Promise<void> {
      if (this.bootstrapped) {
        return;
      }

      if (bootstrapPromise) {
        await bootstrapPromise;
        return;
      }

      this.status = "loading";
      this.error = null;

      bootstrapPromise = (async () => {
        try {
          const sharedSession = await loadSharedSessionSnapshot();

          if (sharedSession.kind === "authenticated") {
            const { snapshot } = sharedSession;
            this.user = null;
            this.profile = null;
            this.aiPolicy = null;
            this.grants = snapshot.grants;
            this.featureFlags = snapshot.featureFlags;

            if (snapshot.user) {
              await this.loadAppContinuation();
              if (!this.csrfToken) {
                await this.ensureCsrfToken();
              }
            }

            this.status = "ready";
            return;
          }

          if (sharedSession.kind === "anonymous") {
            this.user = null;
            this.profile = null;
            this.aiPolicy = null;
            this.grants = [];
            this.featureFlags = [];
            this.csrfToken = null;
            this.status = "ready";
            this.error = null;
            return;
          }

          this.user = null;
          this.profile = null;
          this.aiPolicy = null;
          this.grants = [];
          this.featureFlags = [];
          this.csrfToken = null;
          this.status = "error";
          this.error = sharedSession.message;
        } catch (error: unknown) {
          this.user = null;
          this.profile = null;
          this.aiPolicy = null;
          this.grants = [];
          this.featureFlags = [];
          this.csrfToken = null;
          this.status = "error";
          this.error = error instanceof Error ? error.message : "Failed to bootstrap session";
        }
      })();

      try {
        await bootstrapPromise;
      } finally {
        this.bootstrapped = true;
        bootstrapPromise = null;
      }
    },
    async loadAppContinuation(): Promise<void> {
      this.aiPolicy = null;

      try {
        const result = await requestAppContinuation();

        if (result.kind === "ready") {
          this.user = result.continuation.local_user;
          this.aiPolicy = result.continuation.ai_policy;
          this.profile = result.profile;
          this.error = null;
          return;
        }

        this.user = null;
        this.profile = null;
        this.error = result.message;
      } catch (error: unknown) {
        this.user = null;
        this.profile = null;
        this.error =
          error instanceof Error ? error.message : "Failed to load app continuation";
      }
    },
    async ensureCsrfToken(): Promise<string | null> {
      if (this.csrfToken) {
        return this.csrfToken;
      }

      if (!this.user) {
        return null;
      }

      try {
        const result = await loadSharedCsrfToken();

        if (result.kind === "ready") {
          this.csrfToken = result.token;
          return this.csrfToken;
        }

        if (result.kind === "anonymous") {
          this.user = null;
          this.grants = [];
          this.featureFlags = [];
          this.csrfToken = null;
          return null;
        }

        this.error = result.message;
        return null;
      } catch (error: unknown) {
        this.error = error instanceof Error ? error.message : "Failed to fetch CSRF token";
        return null;
      }
    },
    async login(params: { email: string; password: string }): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        const response = await fetchWithTimeout(
          "/api/v1/auth/login",
          {
            method: "POST",
            credentials: "include",
            headers: {
              Accept: "application/json",
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ email: params.email, password: params.password }),
          },
          {
            timeoutMs: 15000,
            timeoutMessage: "Inloggningen tog för lång tid. Kontrollera anslutningen och försök igen.",
          },
        );

        if (!response.ok) {
          this.status = "error";
          const error = await readAuthError(response);
          this.error = error.message;
          throw error;
        }

        const payload: LoginResponse = await response.json();
        this.user = payload.user;
        this.profile = payload.profile ?? null;
        this.aiPolicy = payload.ai_policy ?? null;
        this.grants = [];
        this.featureFlags = [];
        this.csrfToken = payload.csrf_token;
        this.bootstrapped = true;
        this.status = "ready";
        this.error = null;
      } catch (error: unknown) {
        if (!this.error) {
          this.error = error instanceof Error ? error.message : "Login failed";
        }
        this.status = "error";
        throw error;
      }
    },
    async register(params: {
      email: string;
      password: string;
      firstName: string;
      lastName: string;
      next?: string;
      classroom_planner_entry_origin?: "dashboard" | "catalog";
    }): Promise<RegisterResponse> {
      this.status = "loading";
      this.error = null;

      try {
        const response = await fetchWithTimeout(
          "/api/v1/auth/register",
          {
            method: "POST",
            credentials: "include",
            headers: {
              Accept: "application/json",
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email: params.email,
              password: params.password,
              first_name: params.firstName,
              last_name: params.lastName,
              next: params.next,
              classroom_planner_entry_origin: params.classroom_planner_entry_origin,
            }),
          },
          { timeoutMs: 20000, timeoutMessage: "Registreringen tog för lång tid. Försök igen." },
        );

        if (!response.ok) {
          this.status = "error";
          this.error = await readErrorMessage(response);
          throw new Error(this.error);
        }

        const payload = await response.json() as RegisterResponse;
        this.user = null;
        this.profile = null;
        this.aiPolicy = null;
        this.grants = [];
        this.featureFlags = [];
        this.csrfToken = null;
        this.bootstrapped = true;
        this.status = "ready";
        this.error = null;
        return payload;
      } catch (error: unknown) {
        if (!this.error) {
          this.error = error instanceof Error ? error.message : "Registration failed";
        }
        this.status = "error";
        throw error;
      }
    },
    async logout(): Promise<void> {
      this.status = "loading";
      this.error = null;

      if (!this.bootstrapped) {
        await this.bootstrap();
      }

      const csrfToken = await this.ensureCsrfToken();
      const headers: Record<string, string> = { Accept: "application/json" };
      if (csrfToken) {
        headers["X-CSRF-Token"] = csrfToken;
      }

      try {
        const response = await fetchWithTimeout(
          "/api/v1/auth/logout",
          {
            method: "POST",
            credentials: "include",
            headers,
          },
          { timeoutMs: 10000, timeoutMessage: "Utloggningen tog för lång tid. Försök igen." },
        );

        if (response.status === 204 || response.status === 401) {
          this.clear();
          return;
        }

        if (response.status === 403 && this.user) {
          this.csrfToken = null;
          const refreshedToken = await this.ensureCsrfToken();
          if (!refreshedToken) {
            this.status = "error";
            this.error = await readErrorMessage(response);
            throw new Error(this.error);
          }

          const retry = await fetchWithTimeout(
            "/api/v1/auth/logout",
            {
              method: "POST",
              credentials: "include",
              headers: { ...headers, "X-CSRF-Token": refreshedToken },
            },
            { timeoutMs: 10000, timeoutMessage: "Utloggningen tog för lång tid. Försök igen." },
          );

          if (retry.status === 204 || retry.status === 401) {
            this.clear();
            return;
          }
        }

        this.status = "error";
        this.error = await readErrorMessage(response);
        throw new Error(this.error);
      } catch (error: unknown) {
        if (!this.error) {
          this.error = error instanceof Error ? error.message : "Logout failed";
        }
        this.status = "error";
        throw error;
      }
    },
  },
});
