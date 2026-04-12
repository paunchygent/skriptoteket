/**
 * Shared Hule Education browser-session contract helpers.
 *
 * Purpose:
 *   Centralize the Hule Education-owned browser session, CSRF, logout API
 *   endpoints, and the separate browser-navigable auth ceremony URL.
 *
 * Relationships:
 *   - `stores/auth.ts` uses this module for session bootstrap and CSRF/logout URLs.
 *   - `components/auth/AuthLoginPanel.vue` uses the ceremony helper for anchors.
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
export const DEFAULT_SHARED_AUTH_ENTRY_URL = "https://api.hule.education/auth/login";
export const SHARED_AUTH_APP = "skriptoteket";
export const SHARED_AUTH_DEFAULT_PRODUCT_IDENTITY_REALM = "skriptoteket_standalone";
export const SHARED_AUTH_CALLBACK_PATH = "/auth/callback";
export const SHARED_AUTH_SESSION_PATH = "/v1/auth/session";
export const SHARED_AUTH_CSRF_PATH = "/v1/auth/csrf";
export const SHARED_AUTH_LOGOUT_PATH = "/v1/auth/logout";
const SHARED_AUTH_LOGIN_PATH = "/auth/login";
const AUTH_ENTRY_LOOP_PATHS = new Set([
  SHARED_AUTH_LOGIN_PATH,
  SHARED_AUTH_CALLBACK_PATH,
  "/login",
]);
const CEREMONY_NEXT_URL_BASE = "https://skriptoteket.local";

export type SharedCsrfResponse = {
  csrf_token: string;
};

function normalizeBaseUrl(value: string | undefined): string {
  const rawValue = value?.trim() || DEFAULT_SHARED_AUTH_BASE_URL;
  return rawValue.endsWith("/") ? rawValue.slice(0, -1) : rawValue;
}

export function sharedAuthUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizeBaseUrl(import.meta.env.VITE_HULEEDU_AUTH_BASE_URL)}${normalizedPath}`;
}

function normalizeEntryUrl(value: string | undefined): string {
  return value?.trim() || DEFAULT_SHARED_AUTH_ENTRY_URL;
}

export type SharedAuthCeremonyParams = {
  nextPath: string | null;
  origin: string;
  productIdentityRealm?: string | null;
};

function callbackUrl(origin: string): string {
  return new URL(SHARED_AUTH_CALLBACK_PATH, origin).toString();
}

function sanitizeCeremonyNextPath(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return null;
  }

  try {
    const parsed = new URL(value, CEREMONY_NEXT_URL_BASE);
    if (AUTH_ENTRY_LOOP_PATHS.has(parsed.pathname)) {
      return null;
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return null;
  }
}

export function sharedAuthCeremonyUrl(params: SharedAuthCeremonyParams): string {
  const url = new URL(normalizeEntryUrl(import.meta.env.VITE_HULEEDU_AUTH_ENTRY_URL));
  if (!url.searchParams.has("app")) {
    url.searchParams.set("app", SHARED_AUTH_APP);
  }
  if (!url.searchParams.has("product_identity_realm")) {
    url.searchParams.set(
      "product_identity_realm",
      params.productIdentityRealm?.trim() || SHARED_AUTH_DEFAULT_PRODUCT_IDENTITY_REALM,
    );
  }
  url.searchParams.set("return_to", callbackUrl(params.origin));
  url.searchParams.delete("next");
  const nextPath = sanitizeCeremonyNextPath(params.nextPath);
  if (nextPath) {
    url.searchParams.set("next", nextPath);
  }
  return url.toString();
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
