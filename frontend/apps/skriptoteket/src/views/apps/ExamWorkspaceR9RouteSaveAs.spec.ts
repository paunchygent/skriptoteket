/**
 * Exam workspace R9 route: Spara som ownership.
 *
 * Fail-first for TASK-SKRIPT-40-04-14, unit FF6a (ledger L13), covering the
 * design's section 5 row "Spara som ownership".
 *
 * Each test drives the production owners (a real memory router, the
 * production address, editing, document, gate and history, plus the
 * production `editing.saveAs` flush and copy); doubles cover only transport,
 * clock and server.
 *
 * (i) During the copy's held preflight, a newer route prevents the copy
 *     POST and ultimately opens the latest route. Expected today: FAILS
 *     (the copy POST is still dispatched once the preflight flush lands).
 *     The design registers the copy's replacement intent before the first
 *     await and shares the source barrier, so a superseding route means the
 *     obsolete copy POST never runs.
 * (ii) After the copy POST was sent, a newer route wins: the late copy
 *     result neither opens nor projects the copy and does not clear the new
 *     target's busy state. Expected today: FAILS (the pending copy holds
 *     the document busy, so the newer route's open is refused and the
 *     address is restored). The design retires the copy candidate through
 *     the fence instead of refusing the route behind a busy flag.
 * (iii) An ordinary current copy success creates and opens the copy exactly
 *     once. Control the design keeps: expected to PASS today.
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

const Z = "00000000-0000-4000-8000-000000000003";
const COPY = "00000000-0000-4000-8000-000000000004";

type EditingSession = ReturnType<typeof useExamWorkspaceEditing>;
type TestRouter = ReturnType<typeof createRouter>;

const leaseKnobs: { claims: string[] } = { claims: [] };

function held(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
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

/** A Spara som answer carries the sent working copy under the new identity. */
function asCopy(sent: NativeExamDocument): ExamWorkspaceDocumentResponse {
  const copied: NativeExamDocument = { ...sent, document_id: COPY };
  const payload = response(copied, "step-0");
  return {
    ...payload,
    document: copied,
    saved_document: copied,
    summary: { ...payload.summary, lineage_id: COPY, vault_file_id: COPY },
  };
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
          claim: (lineageId: string, tabId: string) => {
            leaseKnobs.claims.push(lineageId);
            return Promise.resolve(held(tabId));
          },
          release: (lineageId: string, tabId: string) => Promise.resolve(held(tabId)),
          renew: (lineageId: string, tabId: string) => Promise.resolve(held(tabId)),
          requestTakeover: (lineageId: string, tabId: string) => Promise.resolve(held(tabId)),
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

function serveTargets(): void {
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (lineageId === LINEAGE) {
      return read(lineageId);
    }
    return Promise.resolve(reply(Z, "Exam Z"));
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  leaseKnobs.claims.length = 0;
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

it("R9 Spara som (i): a newer route during the held preflight prevents the copy POST", async () => {
  fakeServer(api, exam());
  serveTargets();
  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  const flushAck = deferred<unknown>();
  let stored: unknown = null;
  api.storeExamWorkspaceUndoStep.mockImplementationOnce((lineageId: string, request: unknown) => {
    const saving = persist(lineageId, request);
    stored = saving;
    return flushAck.promise;
  });
  api.copyExamWorkspaceDocument.mockImplementation(
    async (_lineageId: string, _name: string, sent: NativeExamDocument) => asCopy(sent),
  );
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  // The copy's source flush is held; a newer route arrives during the wait.
  const copying = editing.saveAs("Kopia");
  await settle();
  await router.push({ query: { document: Z } });
  await settle();
  flushAck.resolve(stored);
  // The obsolete copy POST never runs; the latest route opens instead.
  expect(await copying).toBe("failed");
  expect(api.copyExamWorkspaceDocument).not.toHaveBeenCalled();
  await settle();
  expect(toast.failure).not.toHaveBeenCalled();
  expect({
    busy: editing.isBusy.value,
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ busy: false, lineage: Z, route: Z, visible: 2 });
});

it("R9 Spara som (ii): after the copy POST was sent, a newer route wins over the late copy", async () => {
  fakeServer(api, exam());
  serveTargets();
  const copyResult = deferred<ExamWorkspaceDocumentResponse>();
  let sentCopy: NativeExamDocument | null = null;
  api.copyExamWorkspaceDocument.mockImplementationOnce(
    (_lineageId: string, _name: string, sent: NativeExamDocument) => {
      sentCopy = sent;
      return copyResult.promise;
    },
  );
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  const copying = editing.saveAs("Kopia");
  await settle();
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  // A newer route arrives while the copy POST is in flight.
  await router.push({ query: { document: Z } });
  await settle();
  // The late copy result neither opens nor projects the copy.
  if (sentCopy === null) {
    throw new Error("expected the copy request");
  }
  copyResult.resolve(asCopy(sentCopy));
  expect(await copying).toBe("failed");
  await settle();
  expect(toast.failure).not.toHaveBeenCalled();
  expect({
    busy: editing.isBusy.value,
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
  }).toEqual({ busy: false, lineage: Z, route: Z });
});

it("R9 Spara som (iii): an ordinary current copy success creates and opens the copy once", async () => {
  fakeServer(api, exam());
  serveTargets();
  api.copyExamWorkspaceDocument.mockImplementation(
    async (_lineageId: string, _name: string, sent: NativeExamDocument) => asCopy(sent),
  );
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  expect(await editing.saveAs("Kopia")).toBe("saved");
  await settle();
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  expect(api.copyExamWorkspaceDocument).toHaveBeenCalledWith(
    LINEAGE,
    "Kopia",
    expect.objectContaining({ title: "Original" }),
  );
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(COPY);
  expect(toast.failure).not.toHaveBeenCalled();
  expect({
    busy: editing.isBusy.value,
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ busy: false, lineage: COPY, route: COPY, visible: 7 });
});
