/**
 * Shared HuleEdu browser-session contract helpers.
 *
 * Purpose:
 *   Centralize the HuleEdu-owned browser session and CSRF endpoint contract so
 *   the SPA auth store can consume it without retaining `/api/v1/auth/me`.
 *
 * Relationships:
 *   - `stores/auth.ts` uses this module for session bootstrap and CSRF URLs.
 *   - `docs/backlog/prs/pr-0251-...` defines the cutover acceptance contract.
 */

import type { components } from "./openapi";

type ApiAiPolicy = components["schemas"]["AiPolicyResponse"];
type ApiRole = components["schemas"]["Role"];
type ApiUser = components["schemas"]["User"];
type ApiUserProfile = components["schemas"]["UserProfile"];

export type AuthUser = Pick<ApiUser, "id" | "email" | "role" | "auth_provider"> &
  Partial<Omit<ApiUser, "id" | "email" | "role" | "auth_provider">>;

export type AuthProfile = Partial<ApiUserProfile> & {
  user_id: string;
  locale: string;
};

type BrowserSessionUser = {
  user_id: string;
  email: string;
  email_verified?: boolean;
};

type BrowserSessionProfile = {
  person_name?: Record<string, string> | null;
  display_name?: string | null;
  locale?: string | null;
};

type BrowserSessionPolicy = {
  roles?: string[];
  grants?: string[];
  feature_flags?: string[];
};

type BrowserSessionState = {
  transport: "cookie";
  session_id?: string | null;
  csrf_required: boolean;
  expires_at: string | null;
};

export type BrowserSessionResponse = {
  authenticated: boolean;
  user?: BrowserSessionUser | null;
  profile?: BrowserSessionProfile | null;
  context?: Record<string, unknown> | null;
  policy?: BrowserSessionPolicy | null;
  session: BrowserSessionState;
  app_flags?: Record<string, unknown> | null;
};

export type SharedAuthSnapshot = {
  user: AuthUser | null;
  profile: AuthProfile | null;
  aiPolicy: ApiAiPolicy | null;
  grants: string[];
  featureFlags: string[];
};

export const DEFAULT_SHARED_AUTH_BASE_URL = "https://api.hule.education";
export const SHARED_AUTH_SESSION_PATH = "/v1/auth/session";
export const SHARED_AUTH_CSRF_PATH = "/v1/auth/csrf";

function normalizeBaseUrl(value: string | undefined): string {
  const rawValue = value?.trim() || DEFAULT_SHARED_AUTH_BASE_URL;
  return rawValue.endsWith("/") ? rawValue.slice(0, -1) : rawValue;
}

export function sharedAuthUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizeBaseUrl(import.meta.env.VITE_HULEEDU_AUTH_BASE_URL)}${normalizedPath}`;
}

function uniqueStrings(values: string[] | undefined): string[] {
  return Array.from(new Set(values ?? []));
}

function pickNamePart(
  personName: Record<string, string> | null | undefined,
  keys: string[],
): string | null {
  if (!personName) {
    return null;
  }
  for (const key of keys) {
    const value = personName[key]?.trim();
    if (value) {
      return value;
    }
  }
  return null;
}

function emptySnapshot(): SharedAuthSnapshot {
  return {
    user: null,
    profile: null,
    aiPolicy: null,
    grants: [],
    featureFlags: [],
  };
}

export function mapBrowserSessionToAuthSnapshot(
  payload: BrowserSessionResponse,
): SharedAuthSnapshot {
  if (!payload.authenticated || !payload.user) {
    return emptySnapshot();
  }

  const userId = payload.user.user_id;
  const personName = payload.profile?.person_name ?? null;

  return {
    user: {
      id: userId,
      email: payload.user.email,
      role: "user" satisfies ApiRole,
      auth_provider: "huleedu",
      external_id: userId,
      email_verified: payload.user.email_verified ?? false,
      is_active: true,
    },
    profile: {
      user_id: userId,
      display_name: payload.profile?.display_name ?? null,
      first_name: pickNamePart(personName, ["first_name", "given_name", "given"]),
      last_name: pickNamePart(personName, ["last_name", "family_name", "family", "surname"]),
      locale: payload.profile?.locale ?? "sv-SE",
    },
    aiPolicy: null,
    grants: uniqueStrings(payload.policy?.grants),
    featureFlags: uniqueStrings(payload.policy?.feature_flags),
  };
}
