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
import { fetchWithTimeout, readAuthError, readErrorMessage } from "../api/authHttp";
import { isApiError } from "../api/client";
import {
  mapBrowserSessionToAuthSnapshot,
  sharedAuthUrl,
  SHARED_AUTH_CSRF_PATH,
  SHARED_AUTH_SESSION_PATH,
  type AuthProfile,
  type BrowserSessionResponse,
  type SharedCsrfResponse,
  type SharedAuthSnapshot,
} from "../api/sharedAuth";

export type SharedSessionBootstrapResult =
  | { kind: "authenticated"; snapshot: SharedAuthSnapshot }
  | { kind: "anonymous" }
  | { kind: "error"; message: string };

export type AppContinuationResult =
  | { kind: "ready"; continuation: AppContinuationResponse; profile: AuthProfile }
  | { kind: "provisioning_required"; error: AppContinuationError }
  | { kind: "error"; error: AppContinuationError };

export type CsrfTokenResult =
  | { kind: "ready"; token: string }
  | { kind: "anonymous" }
  | { kind: "error"; message: string };

export type AppContinuationError = {
  code: string | null;
  details: unknown;
  message: string;
  reason: string | null;
  status: number | null;
};

const PROVISIONING_REQUIRED_REASONS = new Set([
  "missing_huleedu_app_projection",
  "identity_linking_required",
  "inactive_or_missing_local_user",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readReason(details: unknown): string | null {
  if (!isRecord(details)) {
    return null;
  }

  const reason = details.reason;
  return typeof reason === "string" ? reason : null;
}

async function readAppContinuationError(response: Response): Promise<AppContinuationError> {
  const error = await readAuthError(response);

  if (isApiError(error)) {
    return {
      code: error.code,
      details: error.details,
      message: error.message,
      reason: readReason(error.details),
      status: error.status,
    };
  }

  return {
    code: null,
    details: null,
    message: error.message,
    reason: null,
    status: response.status,
  };
}

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

  const error = await readAppContinuationError(response);
  if (
    error.status === 401 &&
    error.reason !== null &&
    PROVISIONING_REQUIRED_REASONS.has(error.reason)
  ) {
    return { kind: "provisioning_required", error };
  }

  return { kind: "error", error };
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
    const payload: SharedCsrfResponse = await response.json();
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
