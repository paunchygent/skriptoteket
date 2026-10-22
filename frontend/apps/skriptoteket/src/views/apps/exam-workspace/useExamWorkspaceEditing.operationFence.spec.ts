/**
 * Exam workspace editing session: operation-fence fail-first ports
 * (TASK-SKRIPT-40-04-14, unit FF2, rereview 5).
 *
 * Ported from the reviewer's failing probes, kept scenario-for-scenario with
 * truthful names. Every test drives the public editing session
 * (`applyCommandResponse`, `openDocument`, `reloadDocument`, `retryItem`,
 * `saveAs`, `updateItemPoints`), the same seam the probes use, so the tests
 * survive the V2/V3 repairs. Each test fails at 768d8ab3 the way the
 * reviewer saw it.
 *
 * Probe source (read-only, not edited):
 *   fence-neighbours.spec.mjs, tests 3 (V2), 4 (V3 reload) and 6 (V3 save-as).
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
  ExamWorkspaceItemRetryResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import type { ExamWorkspaceEditLeaseServer } from "./examWorkspaceEditLeaseDrivers";
import {
  LINEAGE,
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

const api = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

const EXAM_B = "00000000-0000-4000-8000-000000000002";
const EXAM_C = "00000000-0000-4000-8000-000000000003";

function held(tab: string | null = "A"): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: tab,
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function reply(
  document: NativeExamDocument,
  cursor = "step-0",
  lineage: string = LINEAGE,
): ExamWorkspaceDocumentResponse {
  const payload = response(document, cursor);
  return { ...payload, summary: { ...payload.summary, lineage_id: lineage, vault_file_id: lineage } };
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function session(
  server: ExamWorkspaceEditLeaseServer,
  tabId = "A",
): ReturnType<typeof useExamWorkspaceEditing> {
  return inScope(() => useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), { server, tabId }));
}

function driverWith(flags: { offline?: boolean } = {}): ExamWorkspaceEditLeaseServer {
  return {
    claim: () => Promise.resolve(held()),
    release: () => Promise.resolve(held(null)),
    requestTakeover: () => Promise.resolve(held()),
    renew: () => {
      if (flags.offline === true) {
        return Promise.reject(new TypeError("network"));
      }
      return Promise.resolve(held());
    },
  };
}

describe("the operation fence fail-first ports", () => {
  it("an obsolete item retry must not enqueue the old snapshot into a new acquisition history", async () => {
    vi.useFakeTimers();
    const base = exam();
    const first = base.items[0];
    if (first === undefined) {
      throw new Error("expected the first item");
    }
    base.items[0] = {
      ...first,
      review: {
        confidence: 0.4,
        parse_origin: "llm_parsed",
        reasons: ["osäker tolkning"],
        state: "review_required",
      },
      retry_source: {
        chunks: [
          {
            anchor: "body:0001",
            images: [],
            kind: "question",
            marked_text: "Förklara begreppet.",
            missing_images: [],
            paragraphs: [],
            runs: [],
            text: "Förklara begreppet.",
          },
        ],
        context_chunks: [],
        key_chunks: [],
        label_kind: "free_text",
        owned_context_anchors: [],
      },
      source_anchor: "body:0001",
    };
    const server = fakeServer(api, base);
    const flags = { offline: false };
    const old = deferred<ExamWorkspaceItemRetryResponse>();
    api.retryExamWorkspaceItem.mockReturnValue(old.promise);
    const editing = session(driverWith(flags));
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    const retrying = editing.retryItem("item_001", "matching");
    await flushPromises();
    expect(api.retryExamWorkspaceItem).toHaveBeenCalledTimes(1);
    flags.offline = true;
    await vi.advanceTimersByTimeAsync(16000);
    const newer: NativeExamDocument = {
      ...cloneJson(base),
      items: base.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : cloneJson(item),
      ),
    };
    server.documents.set("step-B", newer);
    server.state.steps.push("step-B");
    server.state.cursor = "step-B";
    server.state.position = "step-B";
    api.getExamWorkspaceDocument.mockImplementation(() => {
      const current = server.documents.get(server.state.position);
      if (current === undefined) {
        return Promise.reject(new Error("expected the server copy"));
      }
      return Promise.resolve(reply(cloneJson(current), server.state.cursor));
    });
    await vi.advanceTimersByTimeAsync(4000);
    await flushPromises();
    await flushPromises();
    const reacquired = editing.workspaceDocument.value?.items[1];
    if (reacquired === undefined) {
      throw new Error("expected the reacquired second item");
    }
    expect(reacquired.points).toBe(9);
    // Only the first ensuing POST can persist. A 429 outage begins after it,
    // so a stale snapshot cannot be hidden by immediately re-storing the head.
    const writes: Array<Array<number | null>> = [];
    const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (persist === undefined) {
      throw new Error("expected the step store double");
    }
    let persisting = 1;
    api.storeExamWorkspaceUndoStep.mockImplementation(
      (
        lineageId: string,
        request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string },
      ) => {
        writes.push(request.document.items.map((item) => item.points));
        if (persisting > 0) {
          persisting -= 1;
          return persist(lineageId, request);
        }
        return Promise.reject(new ApiError({ code: "RATE_LIMITED", message: "limited", status: 429 }));
      },
    );
    const retried = base.items[0];
    if (retried === undefined) {
      throw new Error("expected the retried item");
    }
    old.resolve({ item: { ...retried, points: 33 }, lineage_id: LINEAGE });
    await retrying;
    await flushPromises();
    await flushPromises();
    const stored = server.documents.get(server.state.position)?.items[1];
    if (stored === undefined) {
      throw new Error("expected the stored second item");
    }
    expect({ storedPoints: stored.points, writes }).toEqual({ storedPoints: 9, writes: [] });
  });

  it("a reload waiting for a busy B open must not acquire a new token for its captured A lineage", async () => {
    const base = exam();
    fakeServer(api, base);
    const editing = session(driverWith());
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    const opening = deferred<ExamWorkspaceDocumentResponse>();
    api.getExamWorkspaceDocument.mockImplementation((lineageId: string) =>
      lineageId === EXAM_B
        ? opening.promise
        : Promise.resolve(reply(cloneJson(base), "step-0", LINEAGE)),
    );
    const openingB = editing.requestRoute(EXAM_B);
    await flushPromises();
    const reloadingA = editing.reloadDocument();
    opening.resolve(reply({ ...base, document_id: EXAM_B, title: "Exam B" }, "step-0", EXAM_B));
    await openingB;
    await reloadingA;
    await flushPromises();
    const summary = editing.summary.value;
    if (summary === null) {
      throw new Error("expected a summary");
    }
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect({ lineage: summary.lineage_id, title: workspace.title }).toEqual({
      lineage: EXAM_B,
      title: "Exam B",
    });
  });

  it("a save-as awaiting an old exam flush files no copy when the switch cannot settle", async () => {
    const base = exam();
    fakeServer(api, base);
    const editing = session(driverWith());
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    const old = deferred<unknown>();
    api.storeExamWorkspaceUndoStep.mockReturnValue(old.promise);
    editing.updateItemPoints("item_001", 7);
    const copiedIds: string[] = [];
    api.copyExamWorkspaceDocument.mockImplementation(
      (lineageId: string, name: string, document: NativeExamDocument) => {
        copiedIds.push(lineageId);
        // The probe files the copy under `file_name`; the typed summary
        // carries the copy name as `name`, which no assertion reads.
        const copied = reply({ ...cloneJson(document), document_id: EXAM_C }, "step-0", EXAM_C);
        return Promise.resolve({ ...copied, summary: { ...copied.summary, name } });
      },
    );
    const copying = editing.saveAs("Copy");
    await flushPromises();
    // The route request waits on the held store; failing it settles nothing,
    // so the switch opens nothing and the save-as files no copy.
    const switching = editing.requestRoute(EXAM_B);
    await flushPromises();
    old.reject(new Error("offline"));
    expect(await switching).toBe("failed");
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(await copying).toBe("failed");
    expect(copiedIds).toEqual([]);
  });
});
