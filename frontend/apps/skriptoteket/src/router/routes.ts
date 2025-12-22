import type { RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("../views/HomeView.vue"),
  },
  {
    path: "/forbidden",
    name: "forbidden",
    component: () => import("../views/ForbiddenView.vue"),
  },
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
  },
  {
    path: "/browse",
    name: "browse",
    component: () => import("../views/BrowseProfessionsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/browse/:profession",
    name: "browse-categories",
    component: () => import("../views/BrowseCategoriesView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/browse/:profession/:category",
    name: "browse-tools",
    component: () => import("../views/BrowseToolsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/tools/:slug/run",
    name: "tool-run",
    component: () => import("../views/ToolRunFormView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/tools/:slug/runs/:runId",
    name: "tool-result",
    component: () => import("../views/ToolRunResultView.vue"),
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
];
