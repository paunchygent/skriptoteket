/**
 * Exam workspace route boundaries: fail-first ports of the reviewer's route
 * probes (TASK-SKRIPT-40-04-14, rereview 8, cases R8-A to R8-D).
 *
 * Each case keeps the reviewer's scenario, assertion and name, driven
 * through the production owners as the probes do: a real memory router, the
 * production address, editing, document, gate and history. Doubles cover
 * only transport, clock and server. The probe source is read-only and lives
 * outside the repository:
 * `RR/scratch/2ec498b8-d165-46f0-a53c-9a9ade583ad5/route-boundaries.spec.mjs`.
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
const Z = "00000000-0000-4000-8000-000000000003";

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

function reply(lineageId: string, title = "Original"): ExamWorkspaceDocumentResponse {
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

function pointsOf(document: NativeExamDocument | null, itemId: string): number | null {
  if (document === null) {
    throw new Error("expected an open document");
  }
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
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

it("R8-A a retired slow Y read must not keep the freshly reloaded X busy", async () => {
  fakeServer(api, exam());
  const y = deferred<ExamWorkspaceDocumentResponse>();
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) =>
    lineageId === Y ? y.promise : read(lineageId),
  );
  const { editing, router } = await mountRoutedSession();
  expect(editing.editingLocked.value).toBe(false);
  await router.push({ query: { document: Y } });
  await settle();
  await router.push({ query: { document: LINEAGE } });
  await settle();
  // X's fresh read and history have completed; Y's old physical GET remains pending.
  expect(editing.editingLocked.value).toBe(false);
  editing.setTitle("New X title");
  expect({ busy: editing.isBusy.value, title: editing.workspaceDocument.value?.title }).toEqual({
    busy: false,
    title: "New X title",
  });
});

it("R8-B a failed Y route must resume X after it retired X initial history load", async () => {
  fakeServer(api, exam());
  const history = deferred<unknown>();
  const initialHistory = api.getExamWorkspaceHistory.getMockImplementation();
  if (initialHistory === undefined) {
    throw new Error("expected the history double");
  }
  api.getExamWorkspaceHistory.mockImplementationOnce(() => history.promise);
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (lineageId === Y) {
      return Promise.reject(new Error("Y unavailable"));
    }
    return Promise.resolve(reply(LINEAGE));
  });
  const { editing, router } = await mountRoutedSession();
  expect(editing.editingLocked.value).toBe(true);
  await router.push({ query: { document: Y } });
  await settle();
  history.resolve(await initialHistory());
  await settle();
  await vi.advanceTimersByTimeAsync(20000);
  await settle();
  expect(router.currentRoute.value.query.document).toBe(LINEAGE);
  expect({
    locked: editing.editingLocked.value,
    readonly: editing.leaseReadOnly.value,
    title: editing.workspaceDocument.value?.title,
  }).toEqual({ locked: false, readonly: false, title: "Original" });
});

it("R8-C an older Y completion must not cancel a newer Y request after Y to Z to Y", async () => {
  fakeServer(api, exam());
  const firstY = deferred<ExamWorkspaceDocumentResponse>();
  const secondY = deferred<ExamWorkspaceDocumentResponse>();
  const z = deferred<ExamWorkspaceDocumentResponse>();
  let calls = 0;
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (lineageId === Y) {
      calls += 1;
      return calls === 1 ? firstY.promise : secondY.promise;
    }
    if (lineageId === Z) {
      return z.promise;
    }
    return Promise.resolve(reply(LINEAGE));
  });
  const { editing, router } = await mountRoutedSession();
  await router.push({ query: { document: Y } });
  await settle();
  await router.push({ query: { document: Z } });
  await settle();
  await router.push({ query: { document: Y } });
  await settle();
  firstY.resolve(reply(Y, "Old Y"));
  await settle();
  // A stale completion must not restore X or consume the pending newer Y request.
  const routeAfterOldY = router.currentRoute.value.query.document;
  await router.push({ query: { document: LINEAGE } });
  await settle();
  secondY.resolve(reply(Y, "New Y"));
  await settle();
  expect({
    finalRoute: router.currentRoute.value.query.document,
    routeAfterOldY,
    title: editing.workspaceDocument.value?.title,
  }).toEqual({ finalRoute: LINEAGE, routeAfterOldY: Y, title: "Original" });
});

it("R8-D a retired in-flight store must still persist the final edit after a refused route", async () => {
  const server = fakeServer(api, exam());
  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  const ack = deferred<unknown>();
  let stored: unknown = null;
  api.storeExamWorkspaceUndoStep.mockImplementationOnce((lineageId: string, request: unknown) => {
    const saving = persist(lineageId, request);
    stored = saving;
    return ack.promise;
  });
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (lineageId === Y) {
      return Promise.reject(new Error("Y offline"));
    }
    return read(lineageId);
  });
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  // The teacher reverts 7 to the original 2 while the first store's acknowledgement is delayed.
  editing.updateItemPoints("item_001", 2);
  expect(editing.isDirty.value).toBe(false);
  await router.push({ query: { document: Y } });
  await settle();
  ack.resolve(stored);
  await saving;
  await settle();
  await vi.advanceTimersByTimeAsync(6000);
  await settle();
  expect(router.currentRoute.value.query.document).toBe(LINEAGE);
  expect({
    persisted: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ persisted: 2, status: "saved", visible: 2 });
});
