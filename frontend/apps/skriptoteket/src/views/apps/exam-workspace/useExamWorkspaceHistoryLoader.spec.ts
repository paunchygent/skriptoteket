/**
 * Exam workspace history step-list loader: overlapping loads join.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14, lead review RK5 of RK4 at 1001aad6):
 *   - Two loads for the same lineage and the same server document share the
 *     in-flight read: one history GET, and both resolve true.
 *   - A load for a newer server document or a different lineage still
 *     supersedes the older one, which resolves false.
 */

import { flushPromises } from "@vue/test-utils";
import { ref, shallowRef } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceHistory, NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createHistoryLoader } from "./useExamWorkspaceHistoryLoader";

const api = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));

const LINEAGE = "00000000-0000-4000-8000-000000000001";

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
} {
  let resolveFn: ((value: T) => void) | null = null;
  const promise = new Promise<T>((resolve) => {
    resolveFn = resolve;
  });
  return {
    promise,
    resolve: (value: T) => {
      if (resolveFn !== null) {
        resolveFn(value);
      }
    },
  };
}

function historyPayload(): ExamWorkspaceHistory {
  return {
    baseline_step_id: "step-0",
    cursor: "step-0",
    position_step_id: "step-0",
    step_ids: [],
  };
}

function setup() {
  const source = buildParentDocument();
  const serverDocument = shallowRef<NativeExamDocument | null>(source);
  const holder = { lineage: LINEAGE };
  const baselineId = ref<string | null>(null);
  const position = ref<string | null>(null);
  const stepDocument = shallowRef<NativeExamDocument | null>(null);
  const stepIds = ref<string[]>([]);
  const loader = createHistoryLoader(
    {
      lineageId: () => holder.lineage,
      serverDocument,
      shared: serverExamWorkspaceStore.shared,
    },
    { baselineId, position, stepDocument, stepIds },
    () => {
      baselineId.value = null;
      position.value = null;
      stepDocument.value = null;
      stepIds.value = [];
    },
  );
  return { holder, loader, serverDocument, source };
}

beforeEach(() => {
  api.getExamWorkspaceHistory.mockReset();
});

describe("overlapping loads for the same lineage and server document", () => {
  it("shares one history GET and both resolve true when started back to back", async () => {
    const { loader } = setup();
    const gate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory.mockImplementation(() => gate.promise);

    const first = loader.load(LINEAGE);
    const second = loader.load(LINEAGE);
    await flushPromises();
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(1);

    gate.resolve(historyPayload());
    expect(await first).toBe(true);
    expect(await second).toBe(true);
  });

  it("shares one history GET when the second load starts a tick later", async () => {
    const { loader } = setup();
    const gate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory.mockImplementation(() => gate.promise);

    const first = loader.load(LINEAGE);
    await flushPromises();
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(1);
    const second = loader.load(LINEAGE);
    await flushPromises();
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(1);

    gate.resolve(historyPayload());
    expect(await first).toBe(true);
    expect(await second).toBe(true);
  });
});

describe("a load for a newer server document or a different lineage", () => {
  it("supersedes the older load when the server document changed", async () => {
    const { loader, serverDocument, source } = setup();
    const firstGate = deferred<ExamWorkspaceHistory>();
    const secondGate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory
      .mockImplementationOnce(() => firstGate.promise)
      .mockImplementationOnce(() => secondGate.promise);

    const first = loader.load(LINEAGE);
    serverDocument.value = { ...source, title: "newer" };
    const second = loader.load(LINEAGE);
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(2);

    firstGate.resolve(historyPayload());
    secondGate.resolve(historyPayload());
    expect(await first).toBe(false);
    expect(await second).toBe(true);
  });

  it("supersedes the older load on a lineage change", async () => {
    const { holder, loader } = setup();
    const firstGate = deferred<ExamWorkspaceHistory>();
    const secondGate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory
      .mockImplementationOnce(() => firstGate.promise)
      .mockImplementationOnce(() => secondGate.promise);

    const first = loader.load(LINEAGE);
    holder.lineage = "00000000-0000-4000-8000-000000000002";
    const second = loader.load(holder.lineage);
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(2);

    firstGate.resolve(historyPayload());
    secondGate.resolve(historyPayload());
    expect(await first).toBe(false);
    expect(await second).toBe(true);
  });
});
