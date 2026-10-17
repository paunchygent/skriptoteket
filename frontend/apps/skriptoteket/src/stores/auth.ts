/** Owns the browser auth snapshot and admission of asynchronous session responses. */
import { defineStore } from "pinia";
import { computed, reactive, shallowRef, toRefs, watch } from "vue";

import { fetchWithTimeout, readErrorMessage } from "../api/authHttp";
import type { components } from "../api/openapi";
import {
  type AuthProfile,
  type AuthUser,
  type SharedAuthSnapshot,
  sharedAuthUrl,
  requestWithCsrfRecovery,
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
/** A store-owned session lifetime, not merely a teacher ID. */
export type AuthSession = symbol;
type ContinuationStatus = "ready" | "error" | "provisioning_required" | "superseded";
type ContinuationOutcome = { status: ContinuationStatus; session: AuthSession | null };
export class SupersededAuthSessionError extends Error {
  constructor() {
    super("Sessionen har ändrats. Svaret tillhör en tidigare inloggning.");
    this.name = "SupersededAuthSessionError";
  }
}
const ROLE_RANK: Record<ApiRole, number> = {
  user: 0,
  contributor: 1,
  admin: 2,
  superuser: 3,
};
type AuthState = {
  sharedSessionId: string | null;
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
function anonymousState(): AuthState {
  return {
    sharedSessionId: null,
    user: null,
    profile: null,
    aiPolicy: null,
    grants: [],
    featureFlags: [],
    csrfToken: null,
    bootstrapped: true,
    status: "ready",
    error: null,
    appContinuationError: null,
  };
}
async function postSharedLogout(csrfToken: string): Promise<Response> {
  return fetchWithTimeout(
    sharedAuthUrl(SHARED_AUTH_LOGOUT_PATH),
    {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json", "X-CSRF-Token": csrfToken },
    },
    { timeoutMs: 10000, timeoutMessage: LOGOUT_NETWORK_FAILURE_MESSAGE },
  );
}
function isSharedLogoutComplete(response: Response): boolean {
  return response.ok || response.status === 401;
}

export const useAuthStore = defineStore("auth", () => {
  const state = reactive<AuthState>({ ...anonymousState(), bootstrapped: false, status: "idle" });
  // This token is runtime lifecycle state, not a persisted browser/session ID.
  const session = shallowRef<AuthSession>(Symbol("auth session"));
  let bootstrapPromise: Promise<AuthSession | null> | null = null;
  watch(() => state.user?.id ?? null, () => {
    // Retire every cached value before publishing the new lifetime. The
    // admitted response can then populate only the fields it actually owns.
    const next = anonymousState();
    Object.assign(state, {
      sharedSessionId: next.sharedSessionId,
      profile: next.profile,
      aiPolicy: next.aiPolicy,
      grants: next.grants,
      featureFlags: next.featureFlags,
      csrfToken: next.csrfToken,
      status: next.status,
      error: next.error,
      appContinuationError: next.appContinuationError,
    });
    session.value = Symbol("auth session");
  }, { flush: "sync" });

  function captureSession(): AuthSession {
    return session.value;
  }
  function isCurrentSession(requestSession: AuthSession): boolean {
    return requestSession === session.value;
  }
  function requireCurrentSession(requestSession: AuthSession): void {
    if (!isCurrentSession(requestSession)) throw new SupersededAuthSessionError();
  }
  /** Private writer; only bootstrap may use it to admit a non-null identity. */
  function applyState(requestSession: AuthSession, patch: Partial<AuthState>): boolean {
    if (!isCurrentSession(requestSession)) return false;
    const clearsAnonymous = patch.user === null && state.user === null;
    // Identity admission retires the former lifetime before applying its new
    // fields, regardless of the response object's property insertion order.
    if (patch.user !== undefined) state.user = patch.user;
    Object.assign(state, patch);
    // Clearing an already anonymous session must also end pending bootstrap
    // work, but only publish that lifetime after its cached fields are cleared.
    if (clearsAnonymous) session.value = Symbol("auth session");
    return true;
  }
  /** Ordinary responses can update the admitted identity, never replace it. */
  function applyResponse(requestSession: AuthSession, patch: Partial<AuthState>): boolean {
    if (!isCurrentSession(requestSession)) return false;
    if (patch.user && patch.user.id !== state.user?.id) {
      clear(requestSession);
      state.bootstrapped = false;
      return false;
    }
    return applyState(requestSession, patch);
  }
  function clear(requestSession: AuthSession = captureSession()): void {
    applyState(requestSession, anonymousState());
  }

  /** A read may discover another identity; only authoritative bootstrap admits it. */
  async function applyReadResponse(
    requestSession: AuthSession,
    patch: Partial<AuthState>,
  ): Promise<AuthSession | null> {
    if (!isCurrentSession(requestSession)) return null;
    if (applyResponse(requestSession, patch)) return requestSession;
    const admittedSession = await bootstrapSession();
    if (admittedSession === null || !isCurrentSession(admittedSession) ||
      !state.sharedSessionId || !patch.user || state.user?.id !== patch.user.id) return null;
    return applyResponse(admittedSession, patch) ? admittedSession : null;
  }

  async function continueSession(
    requestSession: AuthSession,
    admittedSnapshot?: SharedAuthSnapshot,
  ): Promise<ContinuationOutcome> {
    if (!isCurrentSession(requestSession)) return { status: "superseded", session: null };
    state.aiPolicy = null;
    state.appContinuationError = null;
    try {
      const result = await requestAppContinuation();
      if (result.kind === "ready") {
        const write = admittedSnapshot ? applyState : applyResponse;
        if (!write(requestSession, {
          ...(admittedSnapshot ? {
            sharedSessionId: admittedSnapshot.sharedSessionId,
            grants: admittedSnapshot.grants,
            featureFlags: admittedSnapshot.featureFlags,
          } : {}),
          user: result.continuation.local_user,
          profile: result.profile,
          aiPolicy: result.continuation.ai_policy,
          error: null,
          appContinuationError: null,
          status: "ready",
        })) return { status: "superseded", session: null };
        return { status: "ready", session: captureSession() };
      }
      if (!applyResponse(requestSession, {
        user: null,
        profile: null,
        error: result.error.message,
        appContinuationError: result.error,
        status: result.kind === "provisioning_required" ? "provisioning_required" : "error",
      })) return { status: "superseded", session: null };
      return { status: result.kind, session: captureSession() };
    } catch (error: unknown) {
      if (!applyResponse(requestSession, {
        user: null,
        profile: null,
        error: error instanceof Error ? error.message : "Failed to load app continuation",
        appContinuationError: null,
        status: "error",
      })) return { status: "superseded", session: null };
      return { status: "error", session: captureSession() };
    }
  }

  async function loadAppContinuation(): Promise<ContinuationStatus> {
    return (await continueSession(captureSession())).status;
  }

  async function ensureCsrfToken(
    requestSession: AuthSession = captureSession(),
  ): Promise<string | null> {
    if (!isCurrentSession(requestSession)) return null;
    if (state.csrfToken) return state.csrfToken;
    if (!state.user || !state.sharedSessionId) return null;
    const sharedSessionId = state.sharedSessionId;
    try {
      const result = await loadSharedCsrfToken();
      if (!isCurrentSession(requestSession)) return null;
      if (result.kind === "ready") {
        // Every candidate token belongs to the shared cookie, not necessarily
        // this tab. Establish continuity before caching it or dispatching work.
        const current = await loadSharedSessionSnapshot();
        if (!isCurrentSession(requestSession)) return null;
        if (current.kind === "error") {
          applyResponse(requestSession, { error: current.message });
          return null;
        }
        if (current.kind !== "authenticated" || current.snapshot.sharedSessionId !== sharedSessionId) {
          clear(requestSession);
          return null;
        }
        return applyResponse(requestSession, { csrfToken: result.token }) ? result.token : null;
      }
      if (result.kind === "anonymous") {
        applyResponse(requestSession, anonymousState());
        return null;
      }
      applyResponse(requestSession, { error: result.message });
    } catch (error: unknown) {
      applyResponse(requestSession, {
        error: error instanceof Error ? error.message : "Failed to fetch CSRF token",
      });
    }
    return null;
  }

  function requestWithCsrf(
    requestSession: AuthSession,
    send: (token: string | null) => Promise<Response>,
  ): Promise<Response> {
    return requestWithCsrfRecovery({
      requireCurrent: () => requireCurrentSession(requestSession),
      ensureToken: () => ensureCsrfToken(requestSession),
      recoverToken: () => ensureCsrfToken(requestSession),
      invalidateToken: (rejectedToken) => {
        requireCurrentSession(requestSession);
        if (state.csrfToken === rejectedToken) state.csrfToken = null;
      },
      send,
    });
  }

  async function bootstrapSession(): Promise<AuthSession | null> {
    if (bootstrapPromise) return bootstrapPromise;
    if (state.bootstrapped) return captureSession();
    const requestSession = captureSession();
    state.status = "loading";
    state.error = null;
    state.appContinuationError = null;
    bootstrapPromise = (async () => {
      try {
        const sharedSession = await loadSharedSessionSnapshot();
        if (sharedSession.kind === "authenticated") {
          const { snapshot } = sharedSession;
          if (!applyResponse(requestSession, { bootstrapped: true })) return null;
          if (snapshot.user) {
            const continuation = await continueSession(requestSession, snapshot);
            const admittedSession = continuation.session;
            if (admittedSession === null || !isCurrentSession(admittedSession)) return null;
            if (continuation.status === "ready") {
              await ensureCsrfToken(admittedSession);
            }
            return isCurrentSession(admittedSession) ? admittedSession : null;
          }
          applyResponse(requestSession, anonymousState());
          return null;
        }
        if (sharedSession.kind === "anonymous") {
          applyResponse(requestSession, anonymousState());
          return null;
        }
        applyResponse(requestSession, {
          ...anonymousState(),
          status: "error",
          error: sharedSession.message,
        });
      } catch (error: unknown) {
        applyResponse(requestSession, {
          ...anonymousState(),
          status: "error",
          error: error instanceof Error ? error.message : "Failed to bootstrap session",
        });
      }
      return null;
    })();
    try {
      return await bootstrapPromise;
    } finally {
      bootstrapPromise = null;
    }
  }

  async function bootstrap(): Promise<void> {
    await bootstrapSession();
  }

  async function logout(): Promise<void> {
    state.status = "loading";
    state.error = null;
    let requestSession = captureSession();
    if (!state.bootstrapped) {
      const admittedSession = await bootstrapSession();
      if (admittedSession === null) return;
      requestSession = admittedSession;
    }
    if (!isCurrentSession(requestSession)) return;
    try {
      const csrfToken = await ensureCsrfToken(requestSession);
      if (!isCurrentSession(requestSession)) return;
      if (!csrfToken) {
        if (!state.user) {
          applyResponse(requestSession, anonymousState());
          return;
        }
        throw new Error(state.error ?? "Det gick inte att hämta CSRF-token.");
      }
      const response = await requestWithCsrf(requestSession, (token) => postSharedLogout(token ?? ""));
      if (!isCurrentSession(requestSession)) return;
      if (isSharedLogoutComplete(response)) {
        applyResponse(requestSession, anonymousState());
        return;
      }
      throw new Error(await readErrorMessage(response));
    } catch (error: unknown) {
      if (!isCurrentSession(requestSession)) return;
      applyResponse(requestSession, {
        error: state.error ?? (error instanceof Error ? error.message : LOGOUT_GENERIC_FAILURE_MESSAGE),
        status: "error",
      });
      throw error;
    }
  }

  return {
    ...toRefs(state),
    actorSession: computed(() => session.value),
    isAuthenticated: computed(() => state.user !== null),
    isProvisioningRequired: computed(() => state.status === "provisioning_required"),
    role: computed(() => state.user?.role ?? null),
    hasAtLeastRole: (minRole: ApiRole): boolean =>
      state.user !== null && ROLE_RANK[state.user.role] >= ROLE_RANK[minRole],
    hasGrant: (grant: string): boolean => state.grants.includes(grant),
    hasFeatureFlag: (flag: string): boolean => state.featureFlags.includes(flag),
    displayName: computed(() => state.user
      ? state.profile?.display_name || state.profile?.first_name || state.user.email.split("@")[0]
      : null),
    captureSession,
    isCurrentSession,
    requireCurrentSession,
    applyResponse,
    applyReadResponse,
    clear,
    bootstrap,
    loadAppContinuation,
    ensureCsrfToken,
    requestWithCsrf,
    logout,
  };
});
