/**
 * Classroom planner navigation helpers.
 *
 * This module defines the tiny router-state contract used by
 * Klassrumskartan after the landing-page cutover. The app can remember
 * whether it was entered from the dashboard or the catalog, resolve the
 * correct exit target, and intentionally fall back to the catalog when the
 * current visit is a reload or deep link with no trusted origin state.
 */

import type { RouteLocationRaw, RouteRecordNameGeneric } from "vue-router";

export const CLASSROOM_PLANNER_APP_ID = "classroom.group-seating-studio";

const CLASSROOM_PLANNER_ENTRY_ORIGIN_KEY = "classroomPlannerEntryOrigin";

export type ClassroomPlannerEntryOrigin = "dashboard" | "catalog";

function hasEntryOriginCandidate(
  historyState: object,
): historyState is Record<typeof CLASSROOM_PLANNER_ENTRY_ORIGIN_KEY, unknown> {
  return CLASSROOM_PLANNER_ENTRY_ORIGIN_KEY in historyState;
}

export function resolveClassroomPlannerEntryOriginFromRouteName(
  routeName: RouteRecordNameGeneric | null | undefined,
): ClassroomPlannerEntryOrigin | null {
  if (routeName === "home") {
    return "dashboard";
  }

  if (typeof routeName === "string" && routeName.startsWith("browse")) {
    return "catalog";
  }

  return null;
}

export function buildClassroomPlannerEntryTarget(
  origin: ClassroomPlannerEntryOrigin | null,
): RouteLocationRaw {
  if (!origin) {
    return {
      name: "app-detail",
      params: { appId: CLASSROOM_PLANNER_APP_ID },
    };
  }

  return {
    name: "app-detail",
    params: { appId: CLASSROOM_PLANNER_APP_ID },
    state: {
      [CLASSROOM_PLANNER_ENTRY_ORIGIN_KEY]: origin,
    },
  };
}

export function readClassroomPlannerEntryOriginFromHistoryState(
  historyState: unknown,
): ClassroomPlannerEntryOrigin | null {
  if (!historyState || typeof historyState !== "object") {
    return null;
  }
  if (!hasEntryOriginCandidate(historyState)) {
    return null;
  }

  const candidate = historyState[CLASSROOM_PLANNER_ENTRY_ORIGIN_KEY];
  return candidate === "dashboard" || candidate === "catalog" ? candidate : null;
}

export function resolveClassroomPlannerExitTarget(
  origin: ClassroomPlannerEntryOrigin | null,
): RouteLocationRaw {
  if (origin === "dashboard") {
    return { name: "home" };
  }

  return { name: "browse" };
}

export function isReloadNavigation(
  navigationEntries: Pick<PerformanceNavigationTiming, "type">[],
): boolean {
  return navigationEntries[0]?.type === "reload";
}
