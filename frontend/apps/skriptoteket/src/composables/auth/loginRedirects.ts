/**
 * Login redirect helpers for signed-out surfaces.
 *
 * These helpers keep the in-place login affordances aligned with the router's
 * authenticated destinations so public planner entry upgrades correctly and
 * signed-out-only auth routes do not leave users stranded after login.
 */

import type { RouteLocationRaw, RouteRecordNameGeneric } from "vue-router";

import {
  buildClassroomPlannerEntryTarget,
  CLASSROOM_PLANNER_APP_ID,
} from "../../views/apps/classroomPlannerNavigation";

type RouteLike = {
  name?: RouteRecordNameGeneric | null | undefined;
  params?: Record<string, unknown> | undefined;
};

const SIGNED_OUT_AUTH_ROUTE_NAMES = new Set<RouteRecordNameGeneric>([
  "register",
  "forgot-password",
  "reset-password",
  "verify-email",
]);

export function buildSignedOutOnlyLoginRedirect(): RouteLocationRaw {
  return { name: "home" };
}

export function buildLandingLoginRedirect(route: RouteLike): RouteLocationRaw | null {
  if (route.name === "public-app-detail") {
    const appId = typeof route.params?.appId === "string" ? route.params.appId : null;
    if (!appId) {
      return buildSignedOutOnlyLoginRedirect();
    }
    if (appId === CLASSROOM_PLANNER_APP_ID) {
      return buildClassroomPlannerEntryTarget(null);
    }
    return {
      name: "app-detail",
      params: { appId },
    };
  }

  if (route.name && SIGNED_OUT_AUTH_ROUTE_NAMES.has(route.name)) {
    return buildSignedOutOnlyLoginRedirect();
  }

  return null;
}
