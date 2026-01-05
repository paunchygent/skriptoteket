import { describe, expect, it } from "vitest";

import type { RouteLocationNormalizedLoaded } from "vue-router";

import { editorBaseRouteKey } from "./editorRouteKey";

describe("editorRouteKey", () => {
  it("ignores compare/field query changes when building the base route key", () => {
    const baseRoute = {
      path: "/admin/tools/tool-1",
      params: {},
      query: { version: "ver-base" },
    } as unknown as RouteLocationNormalizedLoaded;

    const baseKey = editorBaseRouteKey(baseRoute);

    expect(
      editorBaseRouteKey({
        ...baseRoute,
        query: { ...baseRoute.query, compare: "ver-compare", field: "tool.py" },
      } as unknown as RouteLocationNormalizedLoaded),
    ).toBe(baseKey);
  });
});
