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

  it("redirects the old signed-in Exam Converter URL to the exam workspace", async () => {
    const router = createTestRouter();

    expect(router.hasRoute("exam-converter-authenticated")).toBe(false);

    await router.push("/apps/exam-converter");
    const current = router.currentRoute.value;

    expect(current.name).toBe("exam-workspace");
    expect(current.path).toBe("/apps/exam-workspace");
  });

  it("mounts the transcript host directly on Audio Transcription", async () => {
    const router = createTestRouter();

    const resolved = router.resolve("/apps/audio-transcription");

    expect(resolved.name).toBe("audio-transcription-authenticated");
    expect(resolved.meta.requiresAuth).toBe(true);
    expect(resolved.meta.unavailableAppTitle).toBeUndefined();
    const loader = resolved.matched.at(-1)?.components?.default;
    expect(typeof loader).toBe("function");
    const loaded = await (loader as () => Promise<{ default: { __file?: string } }>)();
    expect(loaded.default.__file).toContain("ConversionHubTranscriptHost.vue");
  });

  it("adds the route-visible authenticated Document Converter app before the generic app host", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/apps/document-converter");
    const documentRouteIndex = routes.findIndex(
      (route) => route.path === "/apps/document-converter",
    );
    const genericAppRouteIndex = routes.findIndex((route) => route.path === "/apps/:appId");

    expect(resolved.name).toBe("document-converter-authenticated");
    expect(resolved.meta.requiresAuth).toBe(true);
    expect(documentRouteIndex).toBeGreaterThanOrEqual(0);
    expect(documentRouteIndex).toBeLessThan(genericAppRouteIndex);
    expect(String(routes[documentRouteIndex]?.component)).toContain(
      "DocumentConverterView.vue",
    );
  });

  it("adds the route-visible authenticated exam workspace before the generic app host", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/apps/exam-workspace");
    const workspaceRouteIndex = routes.findIndex(
      (route) => route.path === "/apps/exam-workspace",
    );
    const genericAppRouteIndex = routes.findIndex((route) => route.path === "/apps/:appId");

    expect(resolved.name).toBe("exam-workspace");
    expect(resolved.meta.requiresAuth).toBe(true);
    expect(workspaceRouteIndex).toBeGreaterThanOrEqual(0);
    expect(workspaceRouteIndex).toBeLessThan(genericAppRouteIndex);
    expect(String(routes[workspaceRouteIndex]?.component)).toContain("ExamWorkspaceTeacherHost.vue");
  });

  it("lets every authenticated role open the suggestion form", () => {
    const router = createTestRouter();

    const resolved = router.resolve("/suggestions/new");

    expect(resolved.name).toBe("suggestion-new");
    expect(resolved.meta.requiresAuth).toBe(true);
    expect(resolved.meta.minRole).toBeUndefined();
  });

  it("has no Exam Converter UI-inspection fixture route", () => {
    const router = createTestRouter();

    const resolved = router.resolve(
      "/apps/documents.conversion_hub/exam-converter/ui-fixtures/complete-qti-blocked",
    );

    expect(resolved.name).not.toBe("exam-converter-ui-inspection-fixture");
    expect(router.hasRoute("exam-converter-ui-inspection-fixture")).toBe(false);
    expect(resolved.params.fixtureId).toBeUndefined();
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
