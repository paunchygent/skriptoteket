/**
 * Exam workspace route settle order: fail-first ports of the reviewer's R9-1
 * probes (TASK-SKRIPT-40-04-14, rereview 9, rows [Y, Z] and [Y, Z, Y]).
 *
 * Each case keeps the reviewer's scenario, assertion and name, driven through
 * the production owners as the probes do: a real memory router, the
 * production address, editing, document, gate and history. Doubles cover only
 * transport, clock and server. The probe source is read-only and lives
 * outside the repository:
 * `RR/scratch/3e452c40-125d-4406-940a-ed0effc63ed6/route-boundaries.spec.mjs`.
 *
 * The [Y, Z] row must fail before the repair (the first request's settle
 * opens Y after the later Z request took authority); the [Y, Z, Y] row passes
 * before and after (the newest request already targets Y again).
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
vi.mock("../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

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

it.each([[Y, Z], [Y, Z, Y]])(
  "R9 request sequence %j still follows the newest request across a held settle",
  async (...targets: string[]) => {
    fakeServer(api, exam());
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
      return Promise.resolve(reply(lineageId, lineageId === Y ? "Exam Y" : "Exam Z"));
    });
    const { editing, router } = await mountRoutedSession();
    editing.updateItemPoints("item_001", 7);
    const saving = editing.save();
    await settle();
    editing.updateItemPoints("item_001", 2);
    for (const target of targets) {
      await router.push({ query: { document: target } });
      await settle();
    }
    ack.resolve(stored);
    await saving;
    await settle();
    const final = targets[targets.length - 1];
    if (final === undefined) {
      throw new Error("expected a requested route");
    }
    expect({
      busy: editing.isBusy.value,
      lineage: editing.summary.value?.lineage_id,
      route: router.currentRoute.value.query.document,
    }).toEqual({ busy: false, lineage: final, route: final });
  },
);
