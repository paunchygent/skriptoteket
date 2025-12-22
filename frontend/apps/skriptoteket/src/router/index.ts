import { createRouter, createWebHistory } from "vue-router";

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

function getNextParam(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  if (!value.startsWith("/")) {
    return null;
  }
  if (value.startsWith("/login")) {
    return null;
  }
  return value;
}

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  const requiresAuth = Boolean(to.meta.requiresAuth);
  const rawMinRole = typeof to.meta.minRole === "string" ? to.meta.minRole : null;
  const minRole = rawMinRole && isRole(rawMinRole) ? rawMinRole : null;

  if (requiresAuth || minRole || to.name === "login") {
    await auth.bootstrap();
  }

  if (to.name === "login" && auth.isAuthenticated) {
    const nextParam = getNextParam(to.query.next);
    return nextParam ? { path: nextParam } : { path: "/" };
  }

  if ((requiresAuth || minRole) && !auth.isAuthenticated) {
    return {
      name: "login",
      query: { next: to.fullPath },
    };
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
