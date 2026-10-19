/**
 * Exam workspace history step-list loader (TASK-SKRIPT-40-04-14, G1b).
 *
 * Expected behavior:
 *   - A load applies the history payload to the state and stands the editor
 *     on the given base document.
 *   - A load that finishes after the lineage moved on applies nothing.
 *   - A failed read resets the state and throws, so the gate's generation
 *     logic retries the whole fresh load.
 */

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
  reject: (reason: unknown) => void;
} {
  let resolveFn: ((value: T) => void) | null = null;
  let rejectFn: ((reason: unknown) => void) | null = null;
  const promise = new Promise<T>((resolve, reject) => {
    resolveFn = resolve;
    rejectFn = reject;
  });
  return {
    promise,
    reject: (reason: unknown) => {
      if (rejectFn !== null) {
        rejectFn(reason);
      }
    },
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
  const holder = { lineage: LINEAGE };
  const baselineId = ref<string | null>(null);
  const position = ref<string | null>(null);
  const stepDocument = shallowRef<NativeExamDocument | null>(null);
  const stepIds = ref<string[]>([]);
  const loader = createHistoryLoader(
    {
      lineageId: () => holder.lineage,
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
  return { baselineId, holder, loader, position, source, stepDocument, stepIds };
}

beforeEach(() => {
  api.getExamWorkspaceHistory.mockReset();
});

describe("a step-list load", () => {
  it("applies the history payload and stands the editor on the base document", async () => {
    const { baselineId, loader, position, source, stepDocument, stepIds } = setup();
    api.getExamWorkspaceHistory.mockResolvedValue({
      ...historyPayload(),
      position_step_id: "step-2",
      step_ids: ["step-1", "step-2"],
    });

    await loader.load(LINEAGE, source);

    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(1);
    expect(baselineId.value).toBe("step-0");
    expect(position.value).toBe("step-2");
    expect(stepIds.value).toEqual(["step-1", "step-2"]);
    expect(stepDocument.value).toBe(source);
  });

  it("applies nothing when the lineage moved on meanwhile", async () => {
    const { baselineId, holder, loader, position, source, stepDocument, stepIds } = setup();
    const gate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory.mockImplementation(() => gate.promise);

    const loading = loader.load(LINEAGE, source);
    holder.lineage = "00000000-0000-4000-8000-000000000002";
    gate.resolve(historyPayload());
    await loading;

    expect(baselineId.value).toBeNull();
    expect(position.value).toBeNull();
    expect(stepDocument.value).toBeNull();
    expect(stepIds.value).toEqual([]);
  });

  it("resets the state and throws when the read fails", async () => {
    const { baselineId, loader, position, source, stepDocument, stepIds } = setup();
    api.getExamWorkspaceHistory.mockRejectedValueOnce(new Error("offline"));

    await expect(loader.load(LINEAGE, source)).rejects.toThrow("offline");

    expect(baselineId.value).toBeNull();
    expect(position.value).toBeNull();
    expect(stepDocument.value).toBeNull();
    expect(stepIds.value).toEqual([]);
  });
});
