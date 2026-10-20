/**
 * Exam workspace R9 route: failed and hung source barrier.
 *
 * Fail-first for TASK-SKRIPT-40-04-14, unit FF6a (ledger L13), covering the
 * design's section 5 row "Failed and hung source barrier".
 *
 * Each test drives the production owners (a real memory router, the
 * production address, editing, document, gate and history); doubles cover
 * only transport, clock and server. The Spara som preflight runs through the
 * production `editing.saveAs` flush.
 *
 * (a) A concluded failed settle opens nothing and keeps X with its edit and
 *     address. Control the design keeps (L12/R8): expected to PASS today.
 * (b) A stale older settle failure delivered after a newer intent was
 *     admitted does not clear or retire the newer intent: the newer request
 *     still settles and opens. Control the design keeps (a null result never
 *     performs cleanup): expected to PASS today.
 * (c) A store that never answers admits newer target requests but opens
 *     none; when it is later released successfully, only the latest target
 *     opens. Expected today: FAILS (the first request's settle retires first
 *     and opens Y). The design keeps one shared source barrier and one
 *     latest-intent slot instead of one settle per request.
 * (d) The Spara som failed-preflight case: a failed source flush runs
 *     neither the copy POST nor a route open. Expected today: FAILS (the
 *     route request runs its own settle after the shared flush failed and
 *     opens Y). The design gives the copy the same source barrier as a
 *     route: when that shared flush fails, neither a copy nor a route open
 *     runs.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { defineComponent, watch } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceAddress } from "./exam-workspace/useExamWorkspaceAddress";
import { useExamWorkspaceEditing } from "./exam-workspace/useExamWorkspaceEditing";
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
vi.mock("../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

const Y = "00000000-0000-4000-8000-000000000002";
const Z = "00000000-0000-4000-8000-000000000003";

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
      const editing = useExamWorkspaceEditing(serverExamWorkspaceStore, {
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
      const address = useExamWorkspaceAddress({
        isDirty: editing.isDirty,
        noteRouteRequest: editing.noteRouteRequest,
        openDocument: editing.openDocument,
        reloadOpen: editing.reloadOpenExam,
        summary: editing.summary,
      });
      watch(
        () => editing.summary.value?.lineage_id,
        (lineageId) => address.showDocument(lineageId ?? null),
      );
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
    if (lineageId === Y) {
      return Promise.resolve(reply(Y, "Exam Y"));
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

it("R9 barrier (a): a concluded failed settle opens nothing and keeps X with its edit and address", async () => {
  fakeServer(api, exam());
  api.storeExamWorkspaceUndoStep.mockRejectedValue(new Error("offline"));
  serveTargets();
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  expect(await editing.save()).toBe(false);
  await settle();
  // The dirty guard restores the address at once; the settle itself is
  // exercised through the gate's public route-request entry.
  await router.push({ query: { document: Y } });
  await settle();
  const token = await editing.noteRouteRequest();
  await settle();
  expect(token).toBeNull();
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Y);
  expect(api.copyExamWorkspaceDocument).not.toHaveBeenCalled();
  // A failed store truthfully reports its automatic retry (the retained
  // StoreRecovery behaviour); the departure itself toasts nothing.
  expect({
    locked: editing.editingLocked.value,
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ locked: false, lineage: LINEAGE, route: LINEAGE, visible: 7 });
});

it("R9 barrier (b): a stale older settle failure does not clear the newer intent", async () => {
  fakeServer(api, exam());
  serveTargets();
  // The older attempt's transport rejects without committing: the fake
  // server must not advance, or the newer attempt would see a stale cursor.
  const ack = deferred<unknown>();
  api.storeExamWorkspaceUndoStep.mockImplementationOnce((_lineageId: string, _request: unknown) => ack.promise);
  const { editing } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  // Two intents share the held write queue; the older settle fails first.
  const older = editing.noteRouteRequest();
  const newer = editing.noteRouteRequest();
  await settle();
  ack.reject(new Error("offline"));
  await settle();
  expect(await older).toBeNull();
  const token = await newer;
  if (token === null) {
    throw new Error("expected the newer intent to survive the older failure");
  }
  // The newer intent still settles and opens under its own token; the
  // older failure keeps only its truthful retry report, never a cleanup.
  // Z installs with its own fresh content; X's edit stays stored on X.
  expect(await editing.openDocument(Z, token)).toBe("installed");
  await settle();
  expect({
    lineage: editing.summary.value?.lineage_id,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ lineage: Z, visible: 2 });
});

it("R9 barrier (c): a hung store admits newer targets but opens none until it lands on the latest", async () => {
  fakeServer(api, exam());
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
  await router.push({ query: { document: Z } });
  await settle();
  // Nothing may open while the source store never answers.
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Y);
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Z);
  expect(leaseKnobs.claims).not.toContain(Y);
  expect(leaseKnobs.claims).not.toContain(Z);
  expect(editing.summary.value?.lineage_id).toBe(LINEAGE);
  // When the store lands, only the latest target opens.
  ack.resolve(stored);
  expect(await saving).toBe(true);
  await settle();
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Y);
  expect(leaseKnobs.claims).not.toContain(Y);
  expect({
    busy: editing.isBusy.value,
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
  }).toEqual({ busy: false, lineage: Z, route: Z });
});

it("R9 barrier (d): a failed Spara som preflight runs neither the copy nor a route open", async () => {
  fakeServer(api, exam());
  serveTargets();
  api.storeExamWorkspaceUndoStep.mockRejectedValue(new Error("offline"));
  api.copyExamWorkspaceDocument.mockResolvedValue(reply("copy-lineage", "Kopia"));
  const { editing, router } = await mountRoutedSession();
  editing.updateItemPoints("item_001", 7);
  const copying = editing.saveAs("Kopia");
  await settle();
  editing.updateItemPoints("item_001", 2);
  await router.push({ query: { document: Y } });
  await settle();
  expect(await copying).toBe("failed");
  await settle();
  expect(api.copyExamWorkspaceDocument).not.toHaveBeenCalled();
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Y);
  expect(leaseKnobs.claims).not.toContain(Y);
  expect({
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ lineage: LINEAGE, route: LINEAGE, visible: 2 });
});
