/**
 * Anonymous auth-callback retry memory.
 *
 * Purpose:
 *   Remember that a browser has already retried a HuleEdu login handoff from
 *   `/auth/callback` so stale or interrupted callbacks cannot loop forever.
 *
 * Relationships:
 *   - `AuthLoginView.vue` uses this helper to distinguish first callback
 *     recovery from the explicit "log in again" fallback state.
 */

const AUTH_CALLBACK_RETRY_PREFIX = "skriptoteket.authCallbackRetry.";
const AUTH_CALLBACK_DEFAULT_NEXT = "/";

function hashNextPath(nextPath: string): string {
  let hash = 0;
  for (const character of nextPath) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return hash.toString(36);
}

function retryKey(nextPath: string | null): string {
  return `${AUTH_CALLBACK_RETRY_PREFIX}${hashNextPath(nextPath ?? AUTH_CALLBACK_DEFAULT_NEXT)}`;
}

function browserSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function hasAuthCallbackRetry(nextPath: string | null): boolean {
  return browserSessionStorage()?.getItem(retryKey(nextPath)) === "1";
}

export function rememberAuthCallbackRetry(nextPath: string | null): void {
  browserSessionStorage()?.setItem(retryKey(nextPath), "1");
}

export function clearAuthCallbackRetry(nextPath: string | null): void {
  browserSessionStorage()?.removeItem(retryKey(nextPath));
}
