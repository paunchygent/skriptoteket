import type { RouteRecordRaw } from "vue-router";

const RESERVED_PUBLIC_ROUTE_SEGMENTS = new Set(["apps"]);

function getMissingAppsPrefixAppId(appId: unknown): string | null {
  if (typeof appId !== "string") {
    return null;
  }

  return RESERVED_PUBLIC_ROUTE_SEGMENTS.has(appId) ? null : appId;
}

export const routes: RouteRecordRaw[] = [
  {
    path: "/auth/login",
    name: "auth-login",
    component: () => import("../views/AuthLoginView.vue"),
  },
  {
    path: "/auth/callback",
    name: "auth-callback",
    component: () => import("../views/AuthLoginView.vue"),
  },
  {
    path: "/auth/provisioning-required",
    name: "auth-provisioning-required",
    component: () => import("../views/AuthProvisioningRequiredView.vue"),
  },
  {
    path: "/",
    name: "home",
    component: () => import("../views/HomeView.vue"),
  },
  {
    path: "/forgot-password",
    name: "forgot-password",
    component: () => import("../views/AuthRetiredView.vue"),
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../views/AuthRetiredView.vue"),
  },
  {
    path: "/reset-password",
    name: "reset-password",
    component: () => import("../views/AuthRetiredView.vue"),
  },
  {
    path: "/verify-email",
    name: "verify-email",
    component: () => import("../views/AuthRetiredView.vue"),
  },
  {
    path: "/profile",
    name: "profile",
    component: () => import("../views/ProfileView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/forbidden",
    name: "forbidden",
    component: () => import("../views/ForbiddenView.vue"),
  },
  {
    path: "/browse",
    name: "browse",
    component: () => import("../views/BrowseFlatView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/browse/professions",
    name: "browse-professions",
    component: () => import("../views/BrowseProfessionsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/browse/professions/:profession",
    name: "browse-categories",
    component: () => import("../views/BrowseCategoriesView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/browse/professions/:profession/:category",
    name: "browse-tools",
    component: () => import("../views/BrowseToolsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/apps/:appId",
    name: "app-detail",
    component: () => import("../views/AppHostView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/public/apps/:appId",
    name: "public-app-detail",
    component: () => import("../views/PublicAppHostView.vue"),
  },
  {
    path: "/public/:appId",
    name: "public-app-route-recovery",
    component: () => import("../views/RouteRecoveryView.vue"),
    props: (route) => ({
      missingAppsPrefixAppId: getMissingAppsPrefixAppId(route.params.appId),
      missingAppsPrefix: route.path === "/public/apps",
    }),
  },
  {
    path: "/tools/:slug/run",
    name: "tool-run",
    component: () => import("../views/ToolRunView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/my-runs",
    name: "my-runs",
    component: () => import("../views/MyRunsListView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/my-runs/:runId",
    name: "my-runs-detail",
    component: () => import("../views/MyRunsDetailView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/vault",
    name: "vault",
    component: () => import("../views/VaultView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/my-tools",
    name: "my-tools",
    component: () => import("../views/MyToolsView.vue"),
    meta: { requiresAuth: true, minRole: "contributor" },
  },
  {
    path: "/editor",
    name: "editor-hub",
    component: () => import("../views/editor/EditorHubView.vue"),
    meta: { requiresAuth: true, minRole: "contributor" },
  },
  {
    path: "/admin/tools",
    name: "admin-tools",
    component: () => import("../views/admin/AdminToolsView.vue"),
    meta: { requiresAuth: true, minRole: "admin" },
  },
  {
    path: "/admin/users",
    name: "admin-users",
    component: () => import("../views/admin/AdminUsersView.vue"),
    meta: { requiresAuth: true, minRole: "superuser" },
  },
  {
    path: "/admin/users/:userId",
    name: "admin-user-detail",
    component: () => import("../views/admin/AdminUserDetailView.vue"),
    meta: { requiresAuth: true, minRole: "superuser" },
  },
  {
    path: "/admin/tools/:toolId",
    name: "admin-tool-editor",
    component: () => import("../views/admin/ScriptEditorView.vue"),
    meta: { requiresAuth: true, minRole: "contributor", pageTransition: false },
  },
  {
    path: "/admin/tool-versions/:versionId",
    name: "admin-tool-version-editor",
    component: () => import("../views/admin/ScriptEditorView.vue"),
    meta: { requiresAuth: true, minRole: "contributor", pageTransition: false },
  },
  {
    path: "/suggestions/new",
    name: "suggestion-new",
    component: () => import("../views/SuggestionNewView.vue"),
    meta: { requiresAuth: true, minRole: "contributor" },
  },
  {
    path: "/admin/suggestions",
    name: "admin-suggestions",
    component: () => import("../views/admin/AdminSuggestionsListView.vue"),
    meta: { requiresAuth: true, minRole: "admin" },
  },
  {
    path: "/admin/suggestions/:id",
    name: "admin-suggestion-detail",
    component: () => import("../views/admin/AdminSuggestionDetailView.vue"),
    meta: { requiresAuth: true, minRole: "admin" },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("../views/RouteRecoveryView.vue"),
  },
];
