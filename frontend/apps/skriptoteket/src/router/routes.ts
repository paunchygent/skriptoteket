import type { RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("../views/HomeView.vue"),
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../views/RegisterView.vue"),
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
    component: () => import("../views/AppDetailView.vue"),
    meta: { requiresAuth: true },
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
    path: "/my-tools",
    name: "my-tools",
    component: () => import("../views/MyToolsView.vue"),
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
];
