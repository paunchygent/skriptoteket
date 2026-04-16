/**
 * Auth-entry navigation helpers.
 *
 * This module owns the page-based `/auth/login` fallback contract for
 * protected-route interruptions. It keeps the durable redirect destination in
 * the route contract while allowing direct login affordances to open the
 * HuleEdu ceremony URL without an extra app-local click. It also allows
 * Klassrumskartan's entry-origin state to remain a supplemental route-state
 * hint.
 */

import type {
  LocationQuery,
  LocationQueryRaw,
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
  RouteRecordNameGeneric,
} from "vue-router";

import {
  buildClassroomPlannerEntryTarget,
  CLASSROOM_PLANNER_APP_ID,
  readClassroomPlannerEntryOriginFromHistoryState,
  resolveClassroomPlannerEntryOriginFromRouteName,
  type ClassroomPlannerEntryOrigin,
} from "../../views/apps/classroomPlannerNavigation";

export const AUTH_LOGIN_PATH = "/auth/login";
export const AUTH_LOGIN_ROUTE_NAME = "auth-login";
export const AUTH_CALLBACK_PATH = "/auth/callback";
export const CLASSROOM_PLANNER_ENTRY_ORIGIN_QUERY_KEY = "classroomPlannerEntryOrigin";

const SIGNED_OUT_AUTH_ROUTE_NAMES = new Set<RouteRecordNameGeneric>([
  "register",
  "forgot-password",
  "reset-password",
  "verify-email",
]);
const AUTH_PROVISIONING_REQUIRED_PATH = "/auth/provisioning-required";
const AUTH_ENTRY_LOOP_PATHS = new Set([
  AUTH_LOGIN_PATH,
  AUTH_CALLBACK_PATH,
  AUTH_PROVISIONING_REQUIRED_PATH,
  "/login",
]);
const AUTH_ENTRY_PATHS = new Set([AUTH_LOGIN_PATH, AUTH_CALLBACK_PATH]);
const AUTH_LOGIN_FALLBACK: RouteLocationRaw = { name: "home" };
const CLASSROOM_PLANNER_AUTHENTICATED_PATH = `/apps/${CLASSROOM_PLANNER_APP_ID}`;
const AUTH_ENTRY_URL_BASE = "https://skriptoteket.local";

type RouteLike = {
  name?: RouteRecordNameGeneric | null | undefined;
  params?: Record<string, unknown> | undefined;
};

type AuthEntryLocation = Extract<RouteLocationRaw, object> & {
  query?: LocationQueryRaw;
  state?: {
    classroomPlannerEntryOrigin?: ClassroomPlannerEntryOrigin;
  };
};

type AuthContinuationLocation = Extract<RouteLocationRaw, object> & {
  query?: LocationQueryRaw;
};

export type AuthContinuation = {
  nextPath: string | null;
  classroomPlannerEntryOrigin: ClassroomPlannerEntryOrigin | null;
};

function isClassroomPlannerAppRoute(route: RouteLike): boolean {
  return route.name === "app-detail" && route.params?.appId === CLASSROOM_PLANNER_APP_ID;
}

export function isAuthEntryPath(path: string): boolean {
  return AUTH_ENTRY_PATHS.has(path);
}

export function sanitizeAuthNextPath(value: unknown): string | null {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return null;
  }

  try {
    const parsed = new URL(value, AUTH_ENTRY_URL_BASE);

    if (AUTH_ENTRY_LOOP_PATHS.has(parsed.pathname)) {
      return null;
    }

    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return null;
  }
}

export function sanitizeClassroomPlannerEntryOrigin(
  value: unknown,
): ClassroomPlannerEntryOrigin | null {
  return value === "dashboard" || value === "catalog" ? value : null;
}

function shouldKeepClassroomPlannerEntryOrigin(nextPath: string | null): boolean {
  if (!nextPath) {
    return false;
  }

  const parsed = new URL(nextPath, AUTH_ENTRY_URL_BASE);
  return parsed.pathname === CLASSROOM_PLANNER_AUTHENTICATED_PATH;
}

export function readAuthContinuation(
  query: LocationQuery,
  historyState?: unknown,
): AuthContinuation {
  const nextPath = sanitizeAuthNextPath(query.next);
  const queryOrigin = sanitizeClassroomPlannerEntryOrigin(
    query[CLASSROOM_PLANNER_ENTRY_ORIGIN_QUERY_KEY],
  );
  const historyOrigin = readClassroomPlannerEntryOriginFromHistoryState(historyState);

  if (!shouldKeepClassroomPlannerEntryOrigin(nextPath)) {
    return {
      nextPath,
      classroomPlannerEntryOrigin: null,
    };
  }

  return {
    nextPath,
    classroomPlannerEntryOrigin: queryOrigin ?? historyOrigin,
  };
}

export function buildAuthContinuationApiPayload(
  continuation: AuthContinuation,
): {
  next?: string;
  classroom_planner_entry_origin?: ClassroomPlannerEntryOrigin;
} {
  const payload: {
    next?: string;
    classroom_planner_entry_origin?: ClassroomPlannerEntryOrigin;
  } = {};

  if (continuation.nextPath) {
    payload.next = continuation.nextPath;
  }
  if (continuation.classroomPlannerEntryOrigin) {
    payload.classroom_planner_entry_origin = continuation.classroomPlannerEntryOrigin;
  }

  return payload;
}

function buildAuthContinuationQuery(
  continuation: {
    nextPath?: unknown;
    classroomPlannerEntryOrigin?: unknown;
  },
): LocationQueryRaw | undefined {
  const nextQuery: LocationQueryRaw = {};
  const sanitizedNextPath = sanitizeAuthNextPath(continuation.nextPath);
  const sanitizedOrigin = sanitizeClassroomPlannerEntryOrigin(
    continuation.classroomPlannerEntryOrigin,
  );

  if (sanitizedNextPath) {
    nextQuery.next = sanitizedNextPath;
  }
  if (sanitizedOrigin && shouldKeepClassroomPlannerEntryOrigin(sanitizedNextPath)) {
    nextQuery[CLASSROOM_PLANNER_ENTRY_ORIGIN_QUERY_KEY] = sanitizedOrigin;
  }

  if (Object.keys(nextQuery).length === 0) {
    return undefined;
  }

  return nextQuery;
}

export function buildAuthContinuationLocation(
  location: AuthContinuationLocation,
  continuation: {
    nextPath?: unknown;
    classroomPlannerEntryOrigin?: unknown;
  },
): RouteLocationRaw {
  const nextQuery = buildAuthContinuationQuery(continuation);
  const { query: _existingQuery, ...baseLocation } = location;

  if (!nextQuery) {
    return baseLocation;
  }

  return {
    ...baseLocation,
    query: nextQuery,
  };
}

export function buildAuthLoginLocation(params?: {
  nextPath?: string | null;
  classroomPlannerEntryOrigin?: ClassroomPlannerEntryOrigin | null;
}): RouteLocationRaw {
  const location: AuthEntryLocation = {
    name: AUTH_LOGIN_ROUTE_NAME,
  };

  if (params?.classroomPlannerEntryOrigin) {
    location.state = {
      classroomPlannerEntryOrigin: params.classroomPlannerEntryOrigin,
    };
  }

  return buildAuthContinuationLocation(location, {
    nextPath: params?.nextPath,
    classroomPlannerEntryOrigin: params?.classroomPlannerEntryOrigin,
  });
}

export function buildSignedOutOnlyAuthEntryLocation(
  continuation: Partial<AuthContinuation> = {},
): RouteLocationRaw {
  return buildAuthLoginLocation({
    nextPath: sanitizeAuthNextPath(continuation.nextPath) ?? "/",
    classroomPlannerEntryOrigin: sanitizeClassroomPlannerEntryOrigin(
      continuation.classroomPlannerEntryOrigin,
    ),
  });
}

export function resolveLandingAuthContinuation(route: RouteLike): AuthContinuation {
  if (route.name === "public-app-detail") {
    const appId = typeof route.params?.appId === "string" ? route.params.appId : null;

    if (!appId) {
      return { nextPath: "/", classroomPlannerEntryOrigin: null };
    }

    return { nextPath: `/apps/${appId}`, classroomPlannerEntryOrigin: null };
  }

  if (route.name && SIGNED_OUT_AUTH_ROUTE_NAMES.has(route.name)) {
    return { nextPath: "/", classroomPlannerEntryOrigin: null };
  }

  return { nextPath: "/", classroomPlannerEntryOrigin: null };
}

export function buildLandingAuthEntryLocation(route: RouteLike): RouteLocationRaw {
  return buildSignedOutOnlyAuthEntryLocation(resolveLandingAuthContinuation(route));
}

export function buildProtectedAuthEntryLocationFromNavigation(
  to: Pick<RouteLocationNormalizedLoaded, "fullPath" | "name" | "params">,
  from: Pick<RouteLocationNormalizedLoaded, "name">,
): RouteLocationRaw {
  if (isClassroomPlannerAppRoute(to)) {
    return buildAuthLoginLocation({
      nextPath: CLASSROOM_PLANNER_AUTHENTICATED_PATH,
      classroomPlannerEntryOrigin: resolveClassroomPlannerEntryOriginFromRouteName(from.name),
    });
  }

  return buildAuthLoginLocation({ nextPath: to.fullPath });
}

export function buildProtectedAuthEntryLocationFromCurrentRoute(
  route: Pick<RouteLocationNormalizedLoaded, "fullPath" | "name" | "params">,
  historyState: unknown,
): RouteLocationRaw {
  if (isClassroomPlannerAppRoute(route)) {
    return buildAuthLoginLocation({
      nextPath: CLASSROOM_PLANNER_AUTHENTICATED_PATH,
      classroomPlannerEntryOrigin: readClassroomPlannerEntryOriginFromHistoryState(historyState),
    });
  }

  return buildAuthLoginLocation({ nextPath: route.fullPath });
}

export function resolveAuthLoginSuccessLocation(
  continuation: Partial<AuthContinuation>,
  historyState: unknown,
): RouteLocationRaw {
  const sanitizedNextPath = sanitizeAuthNextPath(continuation.nextPath);
  const preservedOrigin =
    sanitizeClassroomPlannerEntryOrigin(continuation.classroomPlannerEntryOrigin) ??
    readClassroomPlannerEntryOriginFromHistoryState(historyState);

  if (!sanitizedNextPath) {
    return AUTH_LOGIN_FALLBACK;
  }

  const parsed = new URL(sanitizedNextPath, AUTH_ENTRY_URL_BASE);

  if (parsed.pathname === CLASSROOM_PLANNER_AUTHENTICATED_PATH && !parsed.search && !parsed.hash) {
    return buildClassroomPlannerEntryTarget(preservedOrigin);
  }

  return sanitizedNextPath;
}

export function resolveProvisioningRequiredExitPath(query: LocationQuery): string {
  return sanitizeAuthNextPath(query.from) ?? "/";
}
