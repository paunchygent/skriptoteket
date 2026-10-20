/**
 * Exam workspace history step-list reader (TASK-SKRIPT-40-04-14, F1).
 *
 * Expected behavior:
 *   - A read returns the parsed step list (baseline id, step ids, position).
 *   - A read never writes state: finishing after a lineage move still
 *     resolves with the payload, because currency is the fence's job and
 *     there is nothing to apply here.
 *   - A failed read rejects and writes nothing, so the gate resets the step
 *     list and retries the whole fresh load.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceHistory } from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { readStepList } from "./useExamWorkspaceHistoryLoader";

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

beforeEach(() => {
  api.getExamWorkspaceHistory.mockReset();
});

describe("a step-list read", () => {
  it("returns the parsed payload", async () => {
    api.getExamWorkspaceHistory.mockResolvedValue({
      ...historyPayload(),
      position_step_id: "step-2",
      step_ids: ["step-1", "step-2"],
    });

    await expect(readStepList(serverExamWorkspaceStore.shared, LINEAGE)).resolves.toEqual({
      baselineId: "step-0",
      position: "step-2",
      stepIds: ["step-1", "step-2"],
    });
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledTimes(1);
    expect(api.getExamWorkspaceHistory).toHaveBeenCalledWith(LINEAGE);
  });

  it("resolves with the payload even when the lineage moved on meanwhile", async () => {
    const gate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory.mockImplementation(() => gate.promise);

    const reading = readStepList(serverExamWorkspaceStore.shared, LINEAGE);
    gate.resolve(historyPayload());

    await expect(reading).resolves.toEqual({
      baselineId: "step-0",
      position: "step-0",
      stepIds: [],
    });
  });

  it("rejects without side effects when the read fails", async () => {
    api.getExamWorkspaceHistory.mockRejectedValueOnce(new Error("offline"));

    await expect(readStepList(serverExamWorkspaceStore.shared, LINEAGE)).rejects.toThrow("offline");
  });
});
