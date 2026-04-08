/**
 * SPA router setup and auth guards.
 *
 * This module centralizes route protection and keeps login redirects intact for
 * Klassrumskartan so auth handoffs do not drop planner entry-origin state.
 *
 * Current main still uses the shared login modal for signed-out auth entry, but
 * the planned forward direction is the dedicated `/auth/login` handoff tracked
 * in ST-32-10 / PR-0242 rather than the old legacy `/login` semantics.
 */

import type { RouteLocationNormalizedLoaded, RouteLocationRaw } from "vue-router";
import { createRouter, createWebHistory } from "vue-router";

import { useLoginModal } from "../composables/useLoginModal";
import { useAuthStore } from "../stores/auth";
import {
  buildClassroomPlannerEntryTarget,
  CLASSROOM_PLANNER_APP_ID,
  resolveClassroomPlannerEntryOriginFromRouteName,
} from "../views/apps/classroomPlannerNavigation";
import { routes } from "./routes";

export const router = createRouter({
  history: createWebHistory("/"),
  routes,
});

const ROLE_VALUES = ["user", "contributor", "admin", "superuser"] as const;
type Role = (typeof ROLE_VALUES)[number];
const LEGACY_LOGIN_PATH = "/login";

function isRole(value: string): value is Role {
  return (ROLE_VALUES as readonly string[]).includes(value);
}

function isLegacyLoginPath(path: string): boolean {
  return path === LEGACY_LOGIN_PATH;
}

function getNextParam(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  if (!value.startsWith("/")) {
    return null;
  }
  if (value === LEGACY_LOGIN_PATH || value.startsWith(`${LEGACY_LOGIN_PATH}?`)) {
    return null;
  }
  return value;
}

function isClassroomPlannerAppRoute(route: {
  name?: RouteLocationNormalizedLoaded["name"];
  params?: RouteLocationNormalizedLoaded["params"];
}): boolean {
  return route.name === "app-detail" && route.params?.appId === CLASSROOM_PLANNER_APP_ID;
}

function buildProtectedRouteLoginRedirect(
  to: Pick<RouteLocationNormalizedLoaded, "fullPath" | "name" | "params">,
  from: Pick<RouteLocationNormalizedLoaded, "name">,
): RouteLocationRaw {
  if (isClassroomPlannerAppRoute(to)) {
    return buildClassroomPlannerEntryTarget(
      resolveClassroomPlannerEntryOriginFromRouteName(from.name),
    );
  }

  return to.fullPath;
}

router.beforeEach(async (to, from) => {
  const auth = useAuthStore();

  const requiresAuth = Boolean(to.meta.requiresAuth);
  const rawMinRole = typeof to.meta.minRole === "string" ? to.meta.minRole : null;
  const minRole = rawMinRole && isRole(rawMinRole) ? rawMinRole : null;
  const isLoginPath = isLegacyLoginPath(to.path);

  if (requiresAuth || minRole || isLoginPath) {
    await auth.bootstrap();
  }

  if (isLoginPath) {
    const nextParam = getNextParam(to.query.next);

    if (auth.isAuthenticated) {
      return nextParam ? { path: nextParam } : { path: "/" };
    }

    const loginModal = useLoginModal();
    loginModal.open(nextParam ?? undefined);
    return { path: "/" };
  }

  if ((requiresAuth || minRole) && !auth.isAuthenticated) {
    const loginModal = useLoginModal();
    loginModal.open(buildProtectedRouteLoginRedirect(to, from));
    return false;
  }

  if (minRole && !auth.hasAtLeastRole(minRole)) {
    return {
      name: "forbidden",
      query: {
        required: minRole,
        from: to.fullPath,
      },
    };
  }

  return true;
});
