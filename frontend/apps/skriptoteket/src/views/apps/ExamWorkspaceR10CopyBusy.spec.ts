/**
 * Exam workspace R10 copy busy: an obsolete copy must not clear a newer copy.
 *
 * Fail-first for TASK-SKRIPT-40-04-14, rereview R10-1. Each test drives the
 * production owners (a real memory router, the production address, editing,
 * document, gate and history, plus the production editing.saveAs flush and
 * copy); doubles cover only transport, clock and server.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { defineComponent } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceAddress } from "./exam-workspace/useExamWorkspaceAddress";
import { useExamWorkspaceEditing } from "./exam-workspace/useExamWorkspaceEditing";
import { createRouteProjection } from "./exam-workspace/examWorkspaceRouteProjection";
import {
  LINEAGE,
  exam,
  fakeServer,
  response,
  stopScopes,
} from "./exam-workspace/useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./exam-workspace/useExamWorkspaceSyncGate.specSupport";

const api = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../composables/useToast", () => ({ useToast: () => toast }));

const Y = "00000000-0000-4000-8000-000000000002";
const COPY_X = "00000000-0000-4000-8000-000000000004";
const COPY_Y = "00000000-0000-4000-8000-000000000005";

type EditingSession = ReturnType<typeof useExamWorkspaceEditing>;
type TestRouter = ReturnType<typeof createRouter>;

function held(): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: "A",
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function reply(lineageId: string, title: string): ExamWorkspaceDocumentResponse {
  const document: NativeExamDocument = { ...exam(title), document_id: lineageId };
  const payload = response(document, "step-0");
  return {
    ...payload,
    summary: { ...payload.summary, lineage_id: lineageId, vault_file_id: lineageId },
  };
}

async function settle(): Promise<void> {
  for (let index = 0; index < 8; index += 1) {
    await flushPromises();
  }
}

const mountedWrappers: Array<{ unmount: () => void }> = [];

async function mountRoutedSession(): Promise<{ editing: EditingSession; router: TestRouter }> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ component: { template: "<div />" }, path: "/workspace" }],
  });
  await router.push({ path: "/workspace", query: { document: LINEAGE } });
  await router.isReady();
  let captured: EditingSession | null = null;
  const Host = defineComponent({
    setup() {
      const projection = createRouteProjection();
      const editing = useExamWorkspaceEditing(serverExamWorkspaceStore, projection, {
        server: {
          claim: () => Promise.resolve(held()),
          release: () => Promise.resolve(held()),
          renew: () => Promise.resolve(held()),
          requestTakeover: () => Promise.resolve(held()),
        },
        tabId: "A",
      });
      useExamWorkspaceAddress({
        currentAddress: editing.currentRouteAddress,
        projection,
        submitRoute: (lineageId) => {
          void editing.requestRoute(lineageId);
        },
      });
      captured = editing;
      return () => null;
    },
  });
  const wrapper = mount(Host, { global: { plugins: [router] } });
  mountedWrappers.push(wrapper);
  await settle();
  if (captured === null) {
    throw new Error("expected the routed editing session");
  }
  const editing: EditingSession = captured;
  return { editing, router };
}

beforeEach(() => {
  vi.useFakeTimers();
  for (const mock of Object.values(api)) {
    mock.mockReset();
  }
  for (const mock of Object.values(toast)) {
    mock.mockReset();
  }
});

afterEach(() => {
  for (const wrapper of mountedWrappers.splice(0)) {
    wrapper.unmount();
  }
  stopScopes();
  vi.useRealTimers();
});

it("an abandoned copy acknowledgement cannot unlock the current copy and accept typing that its response drops", async () => {
  fakeServer(api, exam());
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) =>
    lineageId === Y ? Promise.resolve(reply(Y, "Exam Y")) : read(lineageId),
  );
  const oldCopy = deferred<ExamWorkspaceDocumentResponse>();
  const currentCopy = deferred<ExamWorkspaceDocumentResponse>();
  api.copyExamWorkspaceDocument
    .mockImplementationOnce(() => oldCopy.promise)
    .mockImplementationOnce(() => currentCopy.promise);
  const { editing, router } = await mountRoutedSession();
  const first = editing.saveAs("Copy X");
  await settle();
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  await router.push({ query: { document: Y } });
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Y);
  expect(editing.editingLocked.value).toBe(false);
  const second = editing.saveAs("Copy Y");
  await settle();
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledTimes(2);
  expect(editing.isBusy.value).toBe(true);
  oldCopy.resolve(reply(COPY_X, "Copy X"));
  expect(await first).toBe("failed");
  await settle();
  const busyAfterOldAck = editing.isBusy.value;
  editing.updateItemPoints("item_001", 8);
  const acceptedPoints = editing.workspaceDocument.value?.items[0]?.points;
  currentCopy.resolve(reply(COPY_Y, "Copy Y"));
  expect(await second).toBe("saved");
  await settle();
  await vi.advanceTimersByTimeAsync(1000);
  await settle();
  expect({
    acceptedPoints,
    busyAfterOldAck,
    finalPoints: editing.workspaceDocument.value?.items[0]?.points,
    status: editing.history.saveStatus.value.state,
  }).toEqual({ acceptedPoints: 2, busyAfterOldAck: true, finalPoints: 2, status: "saved" });
});

it("an abandoned copy rejection cannot unlock the current copy and accept typing", async () => {
  fakeServer(api, exam());
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) =>
    lineageId === Y ? Promise.resolve(reply(Y, "Exam Y")) : read(lineageId),
  );
  const oldCopy = deferred<ExamWorkspaceDocumentResponse>();
  const currentCopy = deferred<ExamWorkspaceDocumentResponse>();
  api.copyExamWorkspaceDocument
    .mockImplementationOnce(() => oldCopy.promise)
    .mockImplementationOnce(() => currentCopy.promise);
  const { editing, router } = await mountRoutedSession();
  const first = editing.saveAs("Copy X");
  await settle();
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  await router.push({ query: { document: Y } });
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Y);
  const second = editing.saveAs("Copy Y");
  await settle();
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledTimes(2);
  expect(editing.isBusy.value).toBe(true);
  oldCopy.reject(new Error("network down"));
  expect(await first).toBe("failed");
  await settle();
  const busyAfterOldAck = editing.isBusy.value;
  editing.updateItemPoints("item_001", 8);
  const acceptedPoints = editing.workspaceDocument.value?.items[0]?.points;
  currentCopy.resolve(reply(COPY_Y, "Copy Y"));
  expect(await second).toBe("saved");
  await settle();
  await vi.advanceTimersByTimeAsync(1000);
  await settle();
  expect({
    acceptedPoints,
    busyAfterOldAck,
    finalPoints: editing.workspaceDocument.value?.items[0]?.points,
    status: editing.history.saveStatus.value.state,
  }).toEqual({ acceptedPoints: 2, busyAfterOldAck: true, finalPoints: 2, status: "saved" });
});
