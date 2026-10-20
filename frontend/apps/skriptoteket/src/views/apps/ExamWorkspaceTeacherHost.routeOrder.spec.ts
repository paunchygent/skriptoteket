/**
 * Signed-in exam workspace host route order (TASK-SKRIPT-41-02-05, U9b, R8).
 *
 * Expected behavior:
 *   After a successful first handoff the workspace mounts only once the route
 *   points at the handed-off document, so the real address/document boundary
 *   opens the handed-off exam and never the previous `?document=` exam. A
 *   failed or empty handoff, or a throwing start() or router.replace, still
 *   always renders the workspace.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { createMemoryHistory, createRouter, type Router } from "vue-router";

import type { ExamWorkspaceDocumentResponse } from "../../api/examWorkspace";
import ExamWorkspaceTeacherHost from "./ExamWorkspaceTeacherHost.vue";
import type { StoredGuestDraft } from "./exam-workspace/examWorkspaceGuestDraftStorage";
import {
  guestDocumentResponse,
  type ExamWorkspaceGuestDraft,
} from "./exam-workspace/examWorkspaceGuestDraft";
import { seedGuestHandoffHarness } from "./exam-workspace/useExamWorkspaceGuestHandoff.specSupport";

const NEW_LINEAGE_ID = "20000000-0000-4000-8000-000000000002";
const OLD_LINEAGE_ID = "30000000-0000-4000-8000-000000000003";

const probe = vi.hoisted((): {
  stored: StoredGuestDraft | null;
  get: Mock<(lineageId: string) => Promise<ExamWorkspaceDocumentResponse>>;
  imported: Mock<() => Promise<ExamWorkspaceDocumentResponse>>;
  opened: string | null;
} => ({
  get: vi.fn<(lineageId: string) => Promise<ExamWorkspaceDocumentResponse>>(),
  imported: vi.fn<() => Promise<ExamWorkspaceDocumentResponse>>(),
  opened: null,
  stored: null,
}));

const controllerHooks = vi.hoisted((): {
  startOverride: null | (() => Promise<string | null>);
} => ({ startOverride: null }));

vi.mock("./exam-workspace/examWorkspaceGuestDraftStorage", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./exam-workspace/examWorkspaceGuestDraftStorage")>()),
  createExamWorkspaceGuestDraftStorage: () => ({
    clearIf: (cursor: string) => {
      if (probe.stored?.draft.cursor !== cursor) {
        return Promise.resolve(false);
      }
      probe.stored = null;
      return Promise.resolve(true);
    },
    load: () => Promise.resolve(probe.stored),
  }),
}));

vi.mock("../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/examWorkspace")>()),
  importExamWorkspaceGuestDraft: probe.imported,
}));

vi.mock("./exam-workspace/useExamWorkspaceGuestHandoffController", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("./exam-workspace/useExamWorkspaceGuestHandoffController")>();
  return {
    ...actual,
    useExamWorkspaceGuestHandoffController: (
      ...args: Parameters<typeof actual.useExamWorkspaceGuestHandoffController>
    ) => {
      const controller = actual.useExamWorkspaceGuestHandoffController(...args);
      if (controllerHooks.startOverride !== null) {
        const start = controllerHooks.startOverride;
        return { ...controller, start };
      }
      return controller;
    },
  };
});

// Keep the actual address and document owners, replacing the remaining visual tree only.
vi.mock("./ExamWorkspaceView.vue", async () => {
  const { watch } = await import("vue");
  const { useExamWorkspaceDocument } = await import(
    "./exam-workspace/useExamWorkspaceDocument"
  );
  const { useExamWorkspaceAddress } = await import("./exam-workspace/useExamWorkspaceAddress");
  const { serverExamWorkspaceStore } = await import("./exam-workspace/examWorkspaceStore");
  return {
    default: {
      name: "ProbeWorkspaceView",
      setup() {
        const doc = useExamWorkspaceDocument({
          store: {
            ...serverExamWorkspaceStore,
            shared: {
              ...serverExamWorkspaceStore.shared,
              getExamWorkspaceDocument: probe.get,
            },
          },
        });
        useExamWorkspaceAddress(doc);
        watch(doc.summary, (value) => {
          probe.opened = value?.lineage_id ?? null;
        });
        return {};
      },
      template: '<div data-test="probe-view" />',
    },
  };
});

function withLineage(
  draft: ExamWorkspaceGuestDraft,
  lineageId: string,
): ExamWorkspaceDocumentResponse {
  const base = guestDocumentResponse(draft);
  return { ...base, summary: { ...base.summary, lineage_id: lineageId } };
}

async function mountAtDocument(documentId: string): Promise<Router> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ component: { template: "<div />" }, path: "/workspace" }],
  });
  await router.push({ path: "/workspace", query: { document: documentId } });
  await router.isReady();
  return router;
}

async function settle(): Promise<void> {
  for (let index = 0; index < 8; index += 1) {
    await flushPromises();
  }
}

describe("ExamWorkspaceTeacherHost route order", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    probe.get.mockReset();
    probe.imported.mockReset();
    probe.opened = null;
    probe.stored = null;
    controllerHooks.startOverride = null;
    Object.defineProperty(navigator, "locks", {
      configurable: true,
      value: {
        request: async (_name: string, _opts: unknown, callback: () => Promise<unknown>) =>
          await callback(),
      },
    });
  });

  it("a successful first handoff opens only the handed-off document", async () => {
    const harness = await seedGuestHandoffHarness();
    probe.stored = await harness.storage.load();
    if (probe.stored === null) {
      throw new Error("expected the harness draft to seat");
    }
    const newResult = withLineage(harness.draft, NEW_LINEAGE_ID);
    const oldResult = withLineage(harness.draft, OLD_LINEAGE_ID);
    probe.get.mockImplementation((lineageId: string) =>
      Promise.resolve(lineageId === NEW_LINEAGE_ID ? newResult : oldResult),
    );
    probe.imported.mockResolvedValue(newResult);
    const router = await mountAtDocument(OLD_LINEAGE_ID);
    const wrapper = mount(ExamWorkspaceTeacherHost, { global: { plugins: [router] } });
    try {
      await settle();
      expect(probe.imported).toHaveBeenCalledTimes(1);
      expect(router.currentRoute.value.query.document).toBe(NEW_LINEAGE_ID);
      expect(probe.get.mock.calls.map((call) => call[0])).toEqual([NEW_LINEAGE_ID]);
      expect(probe.opened).toBe(NEW_LINEAGE_ID);
      expect(wrapper.find('[data-test="probe-view"]').exists()).toBe(true);
    } finally {
      wrapper.unmount();
    }
  });

  it("an empty handoff still opens the previous document", async () => {
    const harness = await seedGuestHandoffHarness();
    const oldResult = withLineage(harness.draft, OLD_LINEAGE_ID);
    probe.stored = null;
    probe.get.mockResolvedValue(oldResult);
    const router = await mountAtDocument(OLD_LINEAGE_ID);
    const replaceSpy = vi.spyOn(router, "replace");
    const wrapper = mount(ExamWorkspaceTeacherHost, { global: { plugins: [router] } });
    try {
      await settle();
      expect(probe.imported).not.toHaveBeenCalled();
      expect(replaceSpy).not.toHaveBeenCalled();
      expect(probe.get.mock.calls.map((call) => call[0])).toEqual([OLD_LINEAGE_ID]);
      expect(probe.opened).toBe(OLD_LINEAGE_ID);
      expect(wrapper.find('[data-test="probe-view"]').exists()).toBe(true);
    } finally {
      wrapper.unmount();
    }
  });

  it("a failing route replace still renders the workspace", async () => {
    const harness = await seedGuestHandoffHarness();
    probe.stored = await harness.storage.load();
    if (probe.stored === null) {
      throw new Error("expected the harness draft to seat");
    }
    const newResult = withLineage(harness.draft, NEW_LINEAGE_ID);
    const oldResult = withLineage(harness.draft, OLD_LINEAGE_ID);
    probe.get.mockImplementation((lineageId: string) =>
      Promise.resolve(lineageId === NEW_LINEAGE_ID ? newResult : oldResult),
    );
    probe.imported.mockResolvedValue(newResult);
    const router = await mountAtDocument(OLD_LINEAGE_ID);
    vi.spyOn(router, "replace").mockRejectedValueOnce(new Error("navigeringen misslyckades"));
    const onError = vi.fn();
    const wrapper = mount(ExamWorkspaceTeacherHost, {
      global: { config: { errorHandler: onError }, plugins: [router] },
    });
    try {
      await settle();
      expect(probe.imported).toHaveBeenCalledTimes(1);
      expect(wrapper.find('[data-test="probe-view"]').exists()).toBe(true);
      expect(probe.opened).toBe(OLD_LINEAGE_ID);
    } finally {
      wrapper.unmount();
    }
  });

  it("a throwing handoff start still renders the workspace", async () => {
    const harness = await seedGuestHandoffHarness();
    const oldResult = withLineage(harness.draft, OLD_LINEAGE_ID);
    probe.get.mockResolvedValue(oldResult);
    controllerHooks.startOverride = () => Promise.reject(new Error("handoff start crashed"));
    const router = await mountAtDocument(OLD_LINEAGE_ID);
    const onError = vi.fn();
    const wrapper = mount(ExamWorkspaceTeacherHost, {
      global: { config: { errorHandler: onError }, plugins: [router] },
    });
    try {
      await settle();
      expect(wrapper.find('[data-test="probe-view"]').exists()).toBe(true);
      expect(probe.opened).toBe(OLD_LINEAGE_ID);
    } finally {
      wrapper.unmount();
    }
  });
});
