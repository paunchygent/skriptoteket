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
