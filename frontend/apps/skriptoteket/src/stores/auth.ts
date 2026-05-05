/**
 * SPA auth store for HuleEdu session bootstrap and local app continuation.
 *
 * This store owns the browser-visible auth snapshot, delegates browser session
 * proof to HuleEdu, and hydrates Skriptoteket-only app state through a separate
 * local continuation endpoint.
 */

import { defineStore } from "pinia";

import { fetchWithTimeout, readErrorMessage } from "../api/authHttp";
import type { components } from "../api/openapi";
import {
  type AuthProfile,
  type AuthUser,
  sharedAuthUrl,
  SHARED_AUTH_LOGOUT_PATH,
} from "../api/sharedAuth";
import {
  type AppContinuationError,
  loadAppContinuation as requestAppContinuation,
  loadSharedCsrfToken,
  loadSharedSessionSnapshot,
} from "./authBootstrap";
import {
  LOGOUT_GENERIC_FAILURE_MESSAGE,
  LOGOUT_NETWORK_FAILURE_MESSAGE,
} from "./authUserMessages";

type ApiRole = components["schemas"]["Role"];
type ApiAiPolicy = components["schemas"]["AiPolicyResponse"];

type AuthStatus = "idle" | "loading" | "ready" | "error" | "provisioning_required";

const ROLE_RANK: Record<ApiRole, number> = {
  user: 0,
  contributor: 1,
  admin: 2,
  superuser: 3,
};

function hasAtLeastRole(params: { actual: ApiRole; minRole: ApiRole }): boolean {
  return ROLE_RANK[params.actual] >= ROLE_RANK[params.minRole];
}

function buildSharedLogoutHeaders(csrfToken: string): Record<string, string> {
  return {
    Accept: "application/json",
    "X-CSRF-Token": csrfToken,
  };
}

async function postSharedLogout(csrfToken: string): Promise<Response> {
  return fetchWithTimeout(
    sharedAuthUrl(SHARED_AUTH_LOGOUT_PATH),
    {
      method: "POST",
      credentials: "include",
      headers: buildSharedLogoutHeaders(csrfToken),
    },
    { timeoutMs: 10000, timeoutMessage: LOGOUT_NETWORK_FAILURE_MESSAGE },
  );
}

function isSharedLogoutComplete(response: Response): boolean {
  return response.ok || response.status === 401;
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
  appContinuationError: AppContinuationError | null;
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
    appContinuationError: null,
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null,
    isProvisioningRequired: (state) => state.status === "provisioning_required",
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
      this.appContinuationError = null;
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
      this.appContinuationError = null;

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
              const continuation = await this.loadAppContinuation();
              if (continuation === "provisioning_required") {
                this.status = "provisioning_required";
                return;
              }
              if (continuation === "error") {
                this.status = "error";
                return;
              }
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
            this.appContinuationError = null;
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
          this.appContinuationError = null;
        } catch (error: unknown) {
          this.user = null;
          this.profile = null;
          this.aiPolicy = null;
          this.grants = [];
          this.featureFlags = [];
          this.csrfToken = null;
          this.status = "error";
          this.error = error instanceof Error ? error.message : "Failed to bootstrap session";
          this.appContinuationError = null;
        }
      })();

      try {
        await bootstrapPromise;
      } finally {
        this.bootstrapped = true;
        bootstrapPromise = null;
      }
    },
    async loadAppContinuation(): Promise<"ready" | "error" | "provisioning_required"> {
      this.aiPolicy = null;
      this.appContinuationError = null;

      try {
        const result = await requestAppContinuation();

        if (result.kind === "ready") {
          this.user = result.continuation.local_user;
          this.aiPolicy = result.continuation.ai_policy;
          this.profile = result.profile;
          this.error = null;
          this.appContinuationError = null;
          return "ready";
        }

        this.user = null;
        this.profile = null;
        this.error = result.error.message;
        this.appContinuationError = result.error;
        if (result.kind === "provisioning_required") {
          return "provisioning_required";
        }
        return "error";
      } catch (error: unknown) {
        this.user = null;
        this.profile = null;
        this.error =
          error instanceof Error ? error.message : "Failed to load app continuation";
        this.appContinuationError = null;
        return "error";
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
    async logout(): Promise<void> {
      this.status = "loading";
      this.error = null;

      if (!this.bootstrapped) {
        await this.bootstrap();
      }

      try {
        const csrfToken = await this.ensureCsrfToken();
        if (!csrfToken) {
          if (!this.user) {
            this.clear();
            return;
          }
          throw new Error(this.error ?? "Det gick inte att hämta CSRF-token.");
        }

        const response = await postSharedLogout(csrfToken);

        if (isSharedLogoutComplete(response)) {
          this.clear();
          return;
        }

        if (response.status === 403 && this.user) {
          this.csrfToken = null;
          const refreshedToken = await this.ensureCsrfToken();
          if (refreshedToken) {
            const retry = await postSharedLogout(refreshedToken);
            if (isSharedLogoutComplete(retry)) {
              this.clear();
              return;
            }
            this.status = "error";
            this.error = await readErrorMessage(retry);
            throw new Error(this.error);
          }
        }

        this.status = "error";
        this.error = await readErrorMessage(response);
        throw new Error(this.error);
      } catch (error: unknown) {
        if (!this.error) {
          this.error = error instanceof Error ? error.message : LOGOUT_GENERIC_FAILURE_MESSAGE;
        }
        this.status = "error";
        throw error;
      }
    },
  },
});
