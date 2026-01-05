import type { RouteLocationNormalizedLoaded } from "vue-router";

function queryString(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.trim();
}

export function editorBaseRouteKey(route: RouteLocationNormalizedLoaded): string {
  const pathVersionId = typeof route.params.versionId === "string" ? route.params.versionId : "";
  const versionQuery = pathVersionId ? "" : queryString(route.query.version);
  return `${route.path}?version=${versionQuery}`;
}
