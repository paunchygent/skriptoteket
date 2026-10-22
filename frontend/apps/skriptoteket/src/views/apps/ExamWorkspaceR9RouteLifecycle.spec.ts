/**
 * Exam workspace R9 route: lifecycle invalidation.
 *
 * Fail-first for TASK-SKRIPT-40-04-14, unit FF6a (ledger L13), covering the
 * design's section 5 row "Lifecycle invalidation".
 *
 * Each test drives the production owners (a real memory router, the
 * production address, editing, document, gate, history and lease); doubles
 * cover only transport, clock and server, with the truthful 5 s heartbeat.
 * Lease loss arrives through the production renew path, and pagehide through
 * the production window event.
 *
 * (i) Lease loss during the settle, then the retired settle completion,
 *     delivered before any fresh claim: it unlocks, installs, projects and
 *     toasts nothing; a genuine new acquisition (takeover) then reads,
 *     merges and confirms through the ordinary store.
 * (ii) Pagehide during the destination read: the retired read, delivered
 *     before any fresh claim, installs, projects, claims and toasts
 *     nothing; pushing the next target afterwards opens it with a fresh
 *     claim and leaves it editable.
 * (iii) Pagehide during a copy: the retired copy result opens and projects
 *     nothing and toasts nothing; the next target still opens afterwards.
 *
 * The retired-quiet behaviour is what the fence already guarantees for
 * reads, and the null settle already guarantees for failed departures, so
 * these are expected to PASS today as controls the design keeps. The
 * coordinator the design adds must preserve exactly this quietness while
 * also owning the address.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { defineComponent } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import { ApiError } from "../../api/client";
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
const Z = "00000000-0000-4000-8000-000000000003";
const COPY = "00000000-0000-4000-8000-000000000004";

type EditingSession = ReturnType<typeof useExamWorkspaceEditing>;
type TestRouter = ReturnType<typeof createRouter>;

const leaseKnobs: { claims: string[]; releases: string[]; renewHolder: string } = {
  claims: [],
  releases: [],
  renewHolder: "A",
};

function held(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held by another tab", status: 409 });
}

function reply(lineageId: string, title: string): ExamWorkspaceDocumentResponse {
  const document: NativeExamDocument = { ...exam(title), document_id: lineageId };
  const payload = response(document, "step-0");
  return {
    ...payload,
    summary: { ...payload.summary, lineage_id: lineageId, vault_file_id: lineageId },
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
          release: (lineageId: string, tabId: string) => {
            leaseKnobs.releases.push(lineageId);
            return Promise.resolve(held(tabId));
          },
          renew: (lineageId: string, tabId: string) => {
            // The driver reports a lost lease only when the renew is
            // refused: while another tab holds it, the server answers 409.
            if (leaseKnobs.renewHolder !== "A") {
              return Promise.reject(heldError());
            }
            return Promise.resolve(held(tabId));
          },
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

function serveTargets(extra?: (lineageId: string) => Promise<ExamWorkspaceDocumentResponse> | null): void {
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (extra !== undefined) {
      const answered = extra(lineageId);
      if (answered !== null) {
        return answered;
      }
    }
    if (lineageId === LINEAGE) {
      return read(lineageId);
    }
    if (lineageId === Y) {
      return Promise.resolve(reply(Y, "Exam Y"));
    }
    return Promise.resolve(reply(Z, "Exam Z"));
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  leaseKnobs.claims.length = 0;
  leaseKnobs.releases.length = 0;
  leaseKnobs.renewHolder = "A";
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

it("R9 lifecycle (i): lease loss during the settle retires it; takeover then reads, merges and confirms", async () => {
  const server = fakeServer(api, exam());
  serveTargets();
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
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  editing.updateItemPoints("item_001", 2);
  await router.push({ query: { document: Y } });
  await settle();
  // Another tab takes the lease; the heartbeat reports the loss.
  leaseKnobs.renewHolder = "tab-b";
  await vi.advanceTimersByTimeAsync(5000);
  await settle();
  expect(editing.editingLocked.value).toBe(true);
  // The retired settle completion, delivered before any fresh claim,
  // unlocks, installs, projects and toasts nothing.
  ack.resolve(stored);
  await saving;
  await settle();
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Y);
  expect(leaseKnobs.claims).not.toContain(Y);
  expect(toast.failure).not.toHaveBeenCalled();
  expect(toast.warning).not.toHaveBeenCalled();
  expect({
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ lineage: LINEAGE, route: LINEAGE, visible: 2 });
  // A genuine new acquisition reads, merges and confirms through the store.
  // The other tab released, so the takeover claim succeeds and the kept
  // edit is confirmed.
  leaseKnobs.renewHolder = "A";
  await editing.requestTakeover();
  await settle();
  expect(editing.editingLocked.value).toBe(false);
  expect(await editing.save()).toBe(true);
  await settle();
  await vi.advanceTimersByTimeAsync(6000);
  await settle();
  expect({
    persisted: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ persisted: 2, status: "saved", visible: 2 });
});

it("R9 lifecycle (ii): pagehide during the destination read retires it; the next target still opens", async () => {
  fakeServer(api, exam());
  const retired = deferred<ExamWorkspaceDocumentResponse>();
  serveTargets((lineageId) => (lineageId === Y ? retired.promise : null));
  const { editing, router } = await mountRoutedSession();
  await router.push({ query: { document: Y } });
  await settle();
  window.dispatchEvent(new Event("pagehide"));
  await settle();
  expect(leaseKnobs.releases).toContain(LINEAGE);
  // The retired read, delivered before any fresh claim, changes nothing.
  retired.resolve(reply(Y, "Exam Y"));
  await settle();
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Z);
  expect(leaseKnobs.claims).not.toContain(Y);
  expect(toast.failure).not.toHaveBeenCalled();
  expect(editing.summary.value?.lineage_id).toBe(LINEAGE);
  // The next target opens with a fresh claim and is editable.
  await router.push({ query: { document: Z } });
  await settle();
  await vi.advanceTimersByTimeAsync(6000);
  await settle();
  expect(leaseKnobs.claims).toContain(Z);
  expect(editing.editingLocked.value).toBe(false);
  editing.setTitle("Exam Z edited");
  expect({
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    title: editing.workspaceDocument.value?.title,
  }).toEqual({ lineage: Z, route: Z, title: "Exam Z edited" });
});

it("R9 lifecycle (iii): pagehide during a copy retires it; the late copy opens and projects nothing", async () => {
  fakeServer(api, exam());
  serveTargets();
  const copyResult = deferred<ExamWorkspaceDocumentResponse>();
  api.copyExamWorkspaceDocument.mockImplementationOnce(() => copyResult.promise);
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  const copying = editing.saveAs("Kopia");
  await settle();
  window.dispatchEvent(new Event("pagehide"));
  await settle();
  // The retired copy, delivered before any fresh claim, opens nothing.
  copyResult.resolve(reply(COPY, "Kopia"));
  expect(await copying).toBe("failed");
  await settle();
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(COPY);
  expect(toast.failure).not.toHaveBeenCalled();
  expect({
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
  }).toEqual({ lineage: LINEAGE, route: LINEAGE });
  // The next target still opens afterwards.
  await router.push({ query: { document: Z } });
  await settle();
  await vi.advanceTimersByTimeAsync(6000);
  await settle();
  expect({
    editable: editing.editingLocked.value,
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
  }).toEqual({ editable: false, lineage: Z, route: Z });
});
