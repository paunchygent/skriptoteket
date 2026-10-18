import { describe, expect, it, vi } from "vitest";
import type { Component } from "vue";

import { resolveCuratedAppHostView } from "./curatedAppHostRegistry";

const examWorkspaceTeacherHost = vi.hoisted(() => ({ name: "ExamWorkspaceTeacherHostStub" }));
const examConverterPublicView = vi.hoisted(() => ({ name: "ExamConverterPublicViewStub" }));

vi.mock("vue", async (importOriginal) => ({
  ...(await importOriginal<typeof import("vue")>()),
  defineAsyncComponent: (loader: () => Promise<{ default: Component }>) => ({ loader }),
}));
vi.mock("./apps/ExamWorkspaceTeacherHost.vue", () => ({ default: examWorkspaceTeacherHost }));
vi.mock("./apps/ExamConverterPublicView.vue", () => ({ default: examConverterPublicView }));

async function loadedHost(appId: string, hostMode: "authenticated" | "public") {
  const resolution = resolveCuratedAppHostView(appId, hostMode);
  expect(resolution).not.toBeNull();
  const host = resolution?.component as { loader: () => Promise<{ default: Component }> };
  return (await host.loader()).default;
}

describe("curated app host registry", () => {
  it("opens the exam workspace from the signed-in Conversion Hub catalog entry", async () => {
    expect(await loadedHost("documents.conversion_hub", "authenticated")).toBe(
      examWorkspaceTeacherHost,
    );
  });

  it("keeps the public guest exam converter on its public host", async () => {
    expect(await loadedHost("documents.conversion_hub", "public")).toBe(examConverterPublicView);
  });
});
