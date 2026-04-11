/**
 * HuleEdu shared-session bootstrap helpers.
 *
 * Purpose:
 *   Orchestrate the two-phase browser bootstrap outside the Pinia auth store:
 *   first HuleEdu shared session, then Skriptoteket-local app continuation.
 *
 * Relationships:
 *   - `stores/auth.ts` owns browser-visible auth state and delegates network
 *     bootstrap calls here.
 *   - `api/sharedAuth.ts` and `api/appContinuation.ts` define the wire
 *     contracts consumed by this module.
 */

import {
  APP_CONTINUATION_PATH,
  type AppContinuationResponse,
} from "../api/appContinuation";
import { fetchWithTimeout, readErrorMessage } from "../api/authHttp";
import type { components } from "../api/openapi";
import {
  mapBrowserSessionToAuthSnapshot,
  sharedAuthUrl,
  SHARED_AUTH_CSRF_PATH,
  SHARED_AUTH_SESSION_PATH,
  type AuthProfile,
  type BrowserSessionResponse,
  type SharedAuthSnapshot,
} from "../api/sharedAuth";

type CsrfResponse = components["schemas"]["CsrfResponse"];

export type SharedSessionBootstrapResult =
  | { kind: "authenticated"; snapshot: SharedAuthSnapshot }
  | { kind: "anonymous" }
  | { kind: "error"; message: string };

export type AppContinuationResult =
  | { kind: "ready"; continuation: AppContinuationResponse; profile: AuthProfile }
  | { kind: "error"; message: string };

export type CsrfTokenResult =
  | { kind: "ready"; token: string }
  | { kind: "anonymous" }
  | { kind: "error"; message: string };

function mergeAppContinuationProfile(continuation: AppContinuationResponse): AuthProfile {
  return {
    ...continuation.profile,
    allow_remote_fallback: continuation.allow_remote_fallback ?? null,
    inline_completion_provider: continuation.inline_completion_provider ?? null,
  };
}

export async function loadSharedSessionSnapshot(): Promise<SharedSessionBootstrapResult> {
  const response = await fetchWithTimeout(
    sharedAuthUrl(SHARED_AUTH_SESSION_PATH),
    {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    },
    { timeoutMs: 10000, timeoutMessage: "Sessionen svarar inte. Försök igen." },
  );

  if (response.status === 200) {
    const payload: BrowserSessionResponse = await response.json();
    return {
      kind: "authenticated",
      snapshot: mapBrowserSessionToAuthSnapshot(payload),
    };
  }

  if (response.status === 401) {
    return { kind: "anonymous" };
  }

  return {
    kind: "error",
    message: await readErrorMessage(response),
  };
}

export async function loadAppContinuation(): Promise<AppContinuationResult> {
  const response = await fetchWithTimeout(
    APP_CONTINUATION_PATH,
    {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    },
    {
      timeoutMs: 10000,
      timeoutMessage: "Appens lokala inställningar svarar inte.",
    },
  );

  if (response.status === 200) {
    const continuation: AppContinuationResponse = await response.json();
    return {
      kind: "ready",
      continuation,
      profile: mergeAppContinuationProfile(continuation),
    };
  }

  return {
    kind: "error",
    message: await readErrorMessage(response),
  };
}

export async function loadSharedCsrfToken(): Promise<CsrfTokenResult> {
  const response = await fetchWithTimeout(
    sharedAuthUrl(SHARED_AUTH_CSRF_PATH),
    {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    },
    { timeoutMs: 10000, timeoutMessage: "Det gick inte att hämta CSRF-token." },
  );

  if (response.status === 200) {
    const payload: CsrfResponse = await response.json();
    return { kind: "ready", token: payload.csrf_token };
  }

  if (response.status === 401) {
    return { kind: "anonymous" };
  }

  return {
    kind: "error",
    message: await readErrorMessage(response),
  };
}
