/**
 * Help topic catalog contract tests.
 *
 * This module keeps contextual help aligned with the SPA router by failing when
 * a named route is added without an explicit help topic mapping.
 */
import type { RouteRecordRaw } from "vue-router";
import { describe, expect, it } from "vitest";

import {
  getHelpIndexItems,
  HELP_ROUTE_TOPIC_BY_ROUTE_NAME,
  resolveHelpTopic,
} from "./helpTopicCatalog";
import { routes } from "../../router/routes";

function collectRouteNames(routeRecords: readonly RouteRecordRaw[]): string[] {
  return routeRecords.flatMap((route) => {
    const current = typeof route.name === "string" ? [route.name] : [];
    return route.children ? [...current, ...collectRouteNames(route.children)] : current;
  });
}

describe("help topic catalog", () => {
  it("covers every named SPA route with a help topic", () => {
    const routeNames = collectRouteNames(routes);
    const uncovered = routeNames.filter((routeName) => !HELP_ROUTE_TOPIC_BY_ROUTE_NAME[routeName]);

    expect(uncovered).toEqual([]);
  });

  it("maps route aliases and lifecycle routes to their approved topics", () => {
    expect(resolveHelpTopic("browse")).toBe("browse_professions");
    expect(resolveHelpTopic("browse-professions")).toBe("browse_professions");
    expect(resolveHelpTopic("auth-login")).toBe("login");
    expect(resolveHelpTopic("verify-email")).toBe("auth_lifecycle");
    expect(resolveHelpTopic("auth-provisioning-required")).toBe("provisioning_required");
  });

  it("lets planner context override the generic app route", () => {
    expect(resolveHelpTopic("app-detail", "planner_rules")).toBe("planner_rules");
  });

  it("exposes role-aware index sections from the catalog", () => {
    expect(getHelpIndexItems("logged_out").map((item) => item.topic)).toEqual([
      "login",
      "auth_lifecycle",
    ]);
    expect(getHelpIndexItems("contributor").map((item) => item.topic)).toContain("editor_hub");
    expect(getHelpIndexItems("superuser").map((item) => item.topic)).toEqual(["admin_users"]);
  });
});
