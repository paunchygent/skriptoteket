/**
 * Exam workspace editing session: the gate waits for the open claim (TASK-SKRIPT-40-04-14, F4).
 *
 * Expected behavior:
 *   - When the step-list read finishes before the open claim answers, the
 *     finished load keeps `loading` instead of painting `readonly`; the
 *     claim's success moves the gate to `editing` without another document
 *     read, so the open sends one document GET and never shows the lease
 *     notice.
 *   - When the open claim is refused by a live lease held by another tab,
 *     the session ends `readonly` with one load and no second read.
 *   - While holding exam A, opening exam B releases A's lease, loads B once
 *     and ends `editing` after B's claim succeeds, without ever reporting
 *     the switch reset as a lease loss.
 *
 * Transport is a named double of the server's step store; the lease server
 * is a local double whose claim the test resolves by hand. The composables
 * are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { watch } from "vue";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import {
  exam,
  fakeServer,
  inScope,
  LINEAGE,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(stopScopes);

const EXAM_B = "00000000-0000-4000-8000-000000000002";

function leaseHeldError(): ApiError {
  return new ApiError({
    code: "EDIT_LEASE_HELD",
    message: "Provet redigeras i en annan flik.",
    status: 409,
  });
}

function heldResponse(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-19T12:00:00.000Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

type PendingClaim = {
  lineageId: string;
  resolve: (value: ExamWorkspaceEditLeaseResponse) => void;
  reject: (error: unknown) => void;
};

/** A lease server whose claims the test answers by hand; releases are recorded. */
function manualLeaseServer(): {
  pending: PendingClaim[];
  releases: Array<{ lineageId: string; tabId: string }>;
  server: {
    claim: (lineageId: string, tabId: string) => Promise<ExamWorkspaceEditLeaseResponse>;
    release: (lineageId: string, tabId: string) => Promise<ExamWorkspaceEditLeaseResponse>;
    renew: (lineageId: string, tabId: string) => Promise<ExamWorkspaceEditLeaseResponse>;
    requestTakeover: (lineageId: string, tabId: string) => Promise<ExamWorkspaceEditLeaseResponse>;
  };
} {
  const pending: PendingClaim[] = [];
  const releases: Array<{ lineageId: string; tabId: string }> = [];
  return {
    pending,
    releases,
    server: {
      claim: (lineageId: string, _tabId: string) =>
        new Promise<ExamWorkspaceEditLeaseResponse>((resolve, reject) => {
          pending.push({ lineageId, reject, resolve });
        }),
      release: (lineageId: string, tabId: string) => {
        releases.push({ lineageId, tabId });
        return Promise.resolve(heldResponse(tabId));
      },
      renew: (_lineageId: string, tabId: string) => Promise.resolve(heldResponse(tabId)),
      requestTakeover: (_lineageId: string, tabId: string) => Promise.resolve(heldResponse(tabId)),
    },
  };
}

type StepHistory = {
  baseline_step_id: string;
  cursor: string;
  position_step_id: string;
  step_ids: string[];
};

/** Hold every step-list read until the test releases it, like a slow connection. */
function holdStepLists(pending: Array<(history: StepHistory) => void>): void {
  api.getExamWorkspaceHistory.mockImplementation(
    () =>
      new Promise<StepHistory>((resolve) => {
        pending.push(resolve);
      }),
  );
}

function resolveStepReads(pending: Array<(history: StepHistory) => void>): void {
  for (const resolveStep of pending.splice(0)) {
    resolveStep({ baseline_step_id: "step-0", cursor: "step-0", position_step_id: "step-0", step_ids: [] });
  }
}

function openTitle(editing: ReturnType<typeof useExamWorkspaceEditing>): string {
  const workspace = editing.workspaceDocument.value;
  if (workspace === null) {
    throw new Error("expected an open document");
  }
  return workspace.title;
}

describe("the gate waits for the open claim", () => {
  it("reads once and never shows readonly when the step list beats the open claim", async () => {
    const baseline = exam();
    fakeServer(api, baseline);
    const lease = manualLeaseServer();
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, { server: lease.server, tabId: "tab-A" }),
    );
    const readonlySeen: boolean[] = [];
    watch(
      () => editing.leaseReadOnly.value,
      (readOnly) => {
        readonlySeen.push(readOnly);
      },
    );
    const pendingSteps: Array<(history: StepHistory) => void> = [];
    holdStepLists(pendingSteps);
    const opening = editing.openDocument(LINEAGE);
    await flushPromises();
    expect(lease.pending.map((claim) => claim.lineageId)).toEqual([LINEAGE]);

    resolveStepReads(pendingSteps);
    await flushPromises();

    const openClaim = lease.pending[0];
    if (openClaim === undefined) {
      throw new Error("expected the open claim");
    }
    openClaim.resolve(heldResponse("tab-A"));
    await flushPromises();

    expect(await opening).toBe(true);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(readonlySeen).not.toContain(true);
    expect(editing.leaseReadOnly.value).toBe(false);
    expect(editing.editingLocked.value).toBe(false);
    expect(openTitle(editing)).toBe("Original");
  });

  it("ends readonly with one load when another tab holds the live lease", async () => {
    const baseline = exam();
    fakeServer(api, baseline);
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: {
          claim: () => Promise.reject(leaseHeldError()),
          release: (_lineageId: string, tabId: string) => Promise.resolve(heldResponse(tabId)),
          renew: (_lineageId: string, tabId: string) => Promise.resolve(heldResponse(tabId)),
          requestTakeover: (_lineageId: string, tabId: string) => Promise.resolve(heldResponse(tabId)),
        },
        tabId: "tab-A",
      }),
    );
    const readonlySeen: boolean[] = [];
    watch(
      () => editing.leaseReadOnly.value,
      (readOnly) => {
        readonlySeen.push(readOnly);
      },
    );
    const pendingSteps: Array<(history: StepHistory) => void> = [];
    holdStepLists(pendingSteps);
    const opening = editing.openDocument(LINEAGE);
    await flushPromises();

    resolveStepReads(pendingSteps);
    await flushPromises();

    expect(await opening).toBe(true);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(readonlySeen).toEqual([true]);
    expect(editing.leaseReadOnly.value).toBe(true);
    expect(editing.editingLocked.value).toBe(true);
  });

  it("switches exams without a lease loss while holding the previous exam", async () => {
    const baseline = exam();
    fakeServer(api, baseline);
    const lease = manualLeaseServer();
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, { server: lease.server, tabId: "tab-A" }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();
    const claimA = lease.pending[0];
    if (claimA === undefined) {
      throw new Error("expected the open claim");
    }
    claimA.resolve(heldResponse("tab-A"));
    await flushPromises();
    expect(editing.editingLocked.value).toBe(false);

    const readonlySeen: boolean[] = [];
    watch(
      () => editing.leaseReadOnly.value,
      (readOnly) => {
        readonlySeen.push(readOnly);
      },
    );
    api.getExamWorkspaceDocument.mockClear();
    const pendingSteps: Array<(history: StepHistory) => void> = [];
    holdStepLists(pendingSteps);
    const openingB = editing.openDocument(EXAM_B);
    await flushPromises();
    expect(lease.releases).toEqual([{ lineageId: LINEAGE, tabId: "tab-A" }]);

    resolveStepReads(pendingSteps);
    await flushPromises();

    const claimB = lease.pending[lease.pending.length - 1];
    if (claimB === undefined) {
      throw new Error("expected the second exam's claim");
    }
    expect(claimB.lineageId).toBe(EXAM_B);
    claimB.resolve(heldResponse("tab-A"));
    await flushPromises();

    expect(await openingB).toBe(true);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(readonlySeen).not.toContain(true);
    expect(editing.editingLocked.value).toBe(false);
    expect(editing.leaseReadOnly.value).toBe(false);
  });
});
