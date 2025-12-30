import { defineStore } from "pinia";

import type { components } from "../api/openapi";

type ApiRole = components["schemas"]["Role"];
type ApiUser = components["schemas"]["User"];
type ApiUserProfile = components["schemas"]["UserProfile"];
type CsrfResponse = components["schemas"]["CsrfResponse"];
type LoginResponse = components["schemas"]["LoginResponse"];
type MeResponse = components["schemas"]["MeResponse"];
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

type ApiErrorEnvelope = {
  error?: { code?: string; message?: string };
  detail?: unknown;
};

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return response.statusText || `Request failed (${response.status})`;
  }

  const payload = (await response.json().catch(() => null)) as ApiErrorEnvelope | null;
  if (!payload || typeof payload !== "object") {
    return response.statusText || `Request failed (${response.status})`;
  }

  if (payload.error?.message) {
    return payload.error.message;
  }

  if (payload.detail) {
    return "Validation error";
  }

  return response.statusText || `Request failed (${response.status})`;
}

let bootstrapPromise: Promise<void> | null = null;

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as ApiUser | null,
    profile: null as ApiUserProfile | null,
    csrfToken: null as string | null,
    bootstrapped: false,
    status: "idle" as AuthStatus,
    error: null as string | null,
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
          const response = await fetch("/api/v1/auth/me", {
            method: "GET",
            credentials: "include",
            headers: { Accept: "application/json" },
          });

          if (response.status === 200) {
            const payload = (await response.json()) as MeResponse;
            this.user = payload.user;
            this.profile = payload.profile ?? null;

            if (!this.csrfToken) {
              await this.ensureCsrfToken();
            }

            this.status = "ready";
            this.error = null;
            return;
          }

          if (response.status === 401) {
            this.user = null;
            this.profile = null;
            this.csrfToken = null;
            this.status = "ready";
            this.error = null;
            return;
          }

          this.user = null;
          this.profile = null;
          this.csrfToken = null;
          this.status = "error";
          this.error = await readErrorMessage(response);
        } catch (error: unknown) {
          this.user = null;
          this.profile = null;
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
    async ensureCsrfToken(): Promise<string | null> {
      if (this.csrfToken) {
        return this.csrfToken;
      }

      if (!this.user) {
        return null;
      }

      try {
        const response = await fetch("/api/v1/auth/csrf", {
          method: "GET",
          credentials: "include",
          headers: { Accept: "application/json" },
        });

        if (response.status === 200) {
          const payload = (await response.json()) as CsrfResponse;
          this.csrfToken = payload.csrf_token;
          return this.csrfToken;
        }

        if (response.status === 401) {
          this.user = null;
          this.csrfToken = null;
          return null;
        }

        this.error = await readErrorMessage(response);
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
        const response = await fetch("/api/v1/auth/login", {
          method: "POST",
          credentials: "include",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email: params.email, password: params.password }),
        });

        if (!response.ok) {
          this.status = "error";
          this.error = await readErrorMessage(response);
          throw new Error(this.error);
        }

        const payload = (await response.json()) as LoginResponse;
        this.user = payload.user;
        this.profile = payload.profile ?? null;
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
    }): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        const response = await fetch("/api/v1/auth/register", {
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
          }),
        });

        if (!response.ok) {
          this.status = "error";
          this.error = await readErrorMessage(response);
          throw new Error(this.error);
        }

        const payload = (await response.json()) as RegisterResponse;
        this.user = payload.user;
        this.profile = payload.profile;
        this.csrfToken = null;
        this.bootstrapped = true;
        this.status = "ready";
        this.error = null;
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
        const response = await fetch("/api/v1/auth/logout", {
          method: "POST",
          credentials: "include",
          headers,
        });

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

          const retry = await fetch("/api/v1/auth/logout", {
            method: "POST",
            credentials: "include",
            headers: { ...headers, "X-CSRF-Token": refreshedToken },
          });

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
