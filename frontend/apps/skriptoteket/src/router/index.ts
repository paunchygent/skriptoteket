/**
 * SPA router setup and auth guards.
 *
 * This module centralizes protected-route interruption and signed-out auth
 * entry through the dedicated `/auth/login` page contract so auth handoffs do
 * not drop Klassrumskartan's supplemental planner entry-origin state.
 */

import { createRouter, createWebHistory } from "vue-router";

import {
  buildAuthLoginLocation,
  buildProtectedAuthEntryLocationFromNavigation,
  isAuthEntryPath,
  readAuthContinuation,
  resolveAuthLoginSuccessLocation,
  resolveProvisioningRequiredExitPath,
} from "../composables/auth/authEntryNavigation";
import { useAuthStore } from "../stores/auth";
import { routes } from "./routes";

export const router = createRouter({
  history: createWebHistory("/"),
  routes,
});

const ROLE_VALUES = ["user", "contributor", "admin", "superuser"] as const;
type Role = (typeof ROLE_VALUES)[number];

function isRole(value: string): value is Role {
  return (ROLE_VALUES as readonly string[]).includes(value);
}

router.beforeEach(async (to, from) => {
  const auth = useAuthStore();

  const requiresAuth = Boolean(to.meta.requiresAuth);
  const rawMinRole = typeof to.meta.minRole === "string" ? to.meta.minRole : null;
  const minRole = rawMinRole && isRole(rawMinRole) ? rawMinRole : null;
  const isAuthEntryRoute = isAuthEntryPath(to.path);
  const isProvisioningRequiredPath = to.name === "auth-provisioning-required";

  if (requiresAuth || minRole || isAuthEntryRoute || isProvisioningRequiredPath) {
    await auth.bootstrap();
  }

  if (auth.isProvisioningRequired) {
    if (isProvisioningRequiredPath) {
      return true;
    }

    return {
      name: "auth-provisioning-required",
      query: { from: to.fullPath },
    };
  }

  if (isProvisioningRequiredPath) {
    const nextPath = resolveProvisioningRequiredExitPath(to.query);

    if (!auth.isAuthenticated) {
      return buildAuthLoginLocation({ nextPath });
    }

    return nextPath;
  }

  if (isAuthEntryRoute && auth.isAuthenticated) {
    return resolveAuthLoginSuccessLocation(
      readAuthContinuation(to.query, window.history.state),
      window.history.state,
    );
  }

  if ((requiresAuth || minRole) && !auth.isAuthenticated) {
    return buildProtectedAuthEntryLocationFromNavigation(to, from);
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
