/**
 * SPA route-map recovery tests.
 *
 * These tests lock the explicit malformed public-route recovery seam and the
 * generic catch-all behavior so the canonical public app route keeps its
 * existing contract.
 */

import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import { routes } from "./routes";

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes,
  });
}

function resolveMatchedProps(path: string) {
  const router = createTestRouter();
  const resolved = router.resolve(path);
  const props = resolved.matched.at(-1)?.props.default;

  if (typeof props !== "function") {
    return null;
  }

  return (props as (route: unknown) => unknown)(resolved);
}

describe("routes", () => {
  it("keeps the canonical public curated-app route intact", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/public/apps/classroom.group-seating-studio");

    expect(resolved.name).toBe("public-app-detail");
    expect(resolved.params.appId).toBe("classroom.group-seating-studio");
  });

  it("freezes the scoped public Exam Converter route namespace", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/public/apps/documents.conversion_hub/exam-converter");

    expect(resolved.name).toBe("public-app-capability-detail");
    expect(resolved.params.appId).toBe("documents.conversion_hub");
    expect(resolved.params.publicCapabilitySlug).toBe("exam-converter");
  });

  it("adds the authenticated Exam Converter UI-inspection fixture route for test/dev", () => {
    const router = createTestRouter();

    const resolved = router.resolve(
      "/apps/documents.conversion_hub/exam-converter/ui-fixtures/complete-qti-blocked",
    );

    expect(resolved.name).toBe("exam-converter-ui-inspection-fixture");
    expect(resolved.params.fixtureId).toBe("complete-qti-blocked");
    expect(resolved.meta.requiresAuth).toBe(true);
  });

  it("resolves malformed public app links to the dedicated recovery route", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/public/classroom.group-seating-studio");

    expect(resolved.name).toBe("public-app-route-recovery");
    expect(resolved.params.appId).toBe("classroom.group-seating-studio");
  });

  it("treats /public/apps as reserved recovery input instead of building /public/apps/apps", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/public/apps");

    expect(resolved.name).toBe("public-app-route-recovery");
    expect(resolved.params.appId).toBe("apps");
    expect(resolveMatchedProps("/public/apps")).toEqual(
      expect.objectContaining({
        missingAppsPrefix: true,
        missingAppsPrefixAppId: null,
      }),
    );
  });

  it("resolves unrelated unmatched urls to the generic catch-all route", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/definitely-not-a-route");

    expect(resolved.name).toBe("not-found");
  });

  it("keeps old account lifecycle URLs as deliberate handoff routes", () => {
    const router = createTestRouter();

    expect(router.resolve("/register").name).toBe("register");
    expect(router.resolve("/forgot-password").name).toBe("forgot-password");
    expect(router.resolve("/reset-password?token=reset-token").name).toBe("reset-password");
    expect(router.resolve("/verify-email?token=verify-token").name).toBe("verify-email");
  });
});
