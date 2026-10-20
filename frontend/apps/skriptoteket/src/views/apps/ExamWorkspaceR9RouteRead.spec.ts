/**
 * Exam workspace R9 route: read-stage ownership.
 *
 * Fail-first for TASK-SKRIPT-40-04-14, unit FF6a (ledger L13), covering the
 * design's section 5 row "Read-stage ownership".
 *
 * Each test drives the production owners (a real memory router, the
 * production address, editing, document, gate and history); doubles cover
 * only transport, clock and server.
 *
 * (i) A retired physical GET that never answers does not block a current
 *     target: the current target completes and is editable, and the retired
 *     GET's late answer installs, projects and toasts nothing.
 * (ii) A router projection echo of the current intent starts no extra open.
 * (iii) Browser back/forward through the real memory router open exactly the
 *     current intent and leave the address on it.
 *
 * These pin the four original R8 cases' ownership, which the design reuses
 * unchanged: all three are expected to PASS today as controls the design
 * keeps.
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

function documentCalls(lineageId: string): number {
  return api.getExamWorkspaceDocument.mock.calls.filter((call: Array<unknown>) => call[0] === lineageId)
    .length;
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

it("R9 read (i): a hung retired GET does not block the current target, which completes and is editable", async () => {
  fakeServer(api, exam());
  const retired = deferred<ExamWorkspaceDocumentResponse>();
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (lineageId === Y) {
      return retired.promise;
    }
    if (lineageId === Z) {
      return Promise.resolve(reply(Z, "Exam Z"));
    }
    return read(lineageId);
  });
  const { editing, router } = await mountRoutedSession();
  await router.push({ query: { document: Y } });
  await settle();
  // The newer target completes while Y's physical GET never answers.
  await router.push({ query: { document: Z } });
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Z);
  expect(router.currentRoute.value.query.document).toBe(Z);
  expect(editing.editingLocked.value).toBe(false);
  editing.setTitle("Exam Z edited");
  expect(editing.workspaceDocument.value?.title).toBe("Exam Z edited");
  expect(documentCalls(Z)).toBe(1);
  // The retired GET's late answer installs, projects and toasts nothing.
  retired.resolve(reply(Y, "Exam Y"));
  await settle();
  expect(toast.failure).not.toHaveBeenCalled();
  expect(toast.warning).not.toHaveBeenCalled();
  expect(leaseKnobs.claims).not.toContain(Y);
  expect({
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
    title: editing.workspaceDocument.value?.title,
  }).toEqual({ lineage: Z, route: Z, title: "Exam Z edited" });
});

it("R9 read (ii): a projection echo of the current intent starts no extra open", async () => {
  fakeServer(api, exam());
  const read = api.getExamWorkspaceDocument.getMockImplementation();
  if (read === undefined) {
    throw new Error("expected the document double");
  }
  api.getExamWorkspaceDocument.mockImplementation((lineageId: string) => {
    if (lineageId === Y) {
      return Promise.resolve(reply(Y, "Exam Y"));
    }
    return read(lineageId);
  });
  const { editing, router } = await mountRoutedSession();
  await router.push({ query: { document: Y } });
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Y);
  expect(documentCalls(Y)).toBe(1);
  // Re-projecting the address the open already published is idempotent.
  await router.replace({ query: { ...router.currentRoute.value.query } });
  await settle();
  await router.push({ query: { document: Y } });
  await settle();
  expect(documentCalls(Y)).toBe(1);
  expect({
    lineage: editing.summary.value?.lineage_id,
    route: router.currentRoute.value.query.document,
  }).toEqual({ lineage: Y, route: Y });
});

it("R9 read (iii): browser back and forward open exactly the current intent", async () => {
  fakeServer(api, exam());
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
  const { editing, router } = await mountRoutedSession();
  await router.push({ query: { document: Y } });
  await settle();
  await router.push({ query: { document: Z } });
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Z);
  router.back();
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Y);
  expect(router.currentRoute.value.query.document).toBe(Y);
  expect(documentCalls(Y)).toBe(2);
  router.forward();
  await settle();
  expect(editing.summary.value?.lineage_id).toBe(Z);
  expect(router.currentRoute.value.query.document).toBe(Z);
  expect(documentCalls(Z)).toBe(2);
  expect(toast.failure).not.toHaveBeenCalled();
});
