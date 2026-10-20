/**
 * Exam workspace R9 route: held source settlement ends on the last target.
 *
 * Fail-first for TASK-SKRIPT-40-04-14, unit FF6a (ledger L13), covering the
 * design's section 5 row "Held source settlement: last target" (the R9-1
 * family beyond FF5's [Y, Z] and [Y, Z, Y] rows).
 *
 * Scenario: X holds a committing store of 7, the teacher reverts to 2, then
 * requests Y and Z before the settle is released, plus a third request that
 * lands as a microtask in the same turn the settle succeeds. The design
 * keeps one source barrier and one latest-intent slot: the final lineage and
 * address equal the last target, the source persists 2, and no obsolete
 * request opens, restores, or claims the lease for its abandoned target
 * (claims counted per lineage through the lease double).
 *
 * Expected today: FAILS. Each route request mints ownership after its own
 * await, so the first settle to finish opens Y and claims Y's lease before
 * the later requests retire it. The design moves ownership into one
 * gate-owned replacement coordinator with no await between choosing the
 * winner and installing its context.
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
const W = "00000000-0000-4000-8000-000000000004";

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

it("R9 held settle: Y then Z then a same-turn third request ends on the third target alone", async () => {
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
    if (lineageId === LINEAGE) {
      return read(lineageId);
    }
    if (lineageId === Y) {
      return Promise.resolve(reply(Y, "Exam Y"));
    }
    if (lineageId === Z) {
      return Promise.resolve(reply(Z, "Exam Z"));
    }
    return Promise.resolve(reply(W, "Exam W"));
  });
  const { editing, router } = await mountRoutedSession();
  // X commits 7, then the teacher reverts to 2 while the store is held.
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  editing.updateItemPoints("item_001", 2);
  await router.push({ query: { document: Y } });
  await settle();
  await router.push({ query: { document: Z } });
  await settle();
  // The settle succeeds in the same turn a third request lands.
  ack.resolve(stored);
  const third = router.push({ query: { document: W } });
  expect(await saving).toBe(true);
  await third;
  await settle();
  // No obsolete request may have opened or claimed its abandoned target.
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Y);
  expect(api.getExamWorkspaceDocument).not.toHaveBeenCalledWith(Z);
  expect(leaseKnobs.claims).not.toContain(Y);
  expect(leaseKnobs.claims).not.toContain(Z);
  expect(toast.failure).not.toHaveBeenCalled();
  expect({
    busy: editing.isBusy.value,
    lineage: editing.summary.value?.lineage_id,
    persisted: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    route: router.currentRoute.value.query.document,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ busy: false, lineage: W, persisted: 2, route: W, visible: 2 });
});
