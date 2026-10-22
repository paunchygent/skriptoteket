/**
 * Exam workspace fenced transport (TASK-SKRIPT-40-04-14, F2).
 *
 * A store answer settled after its generation retires installs nothing and
 * reports nothing: the step list, cursor, working copy and save status stay
 * as they were, with no confirmed, failed, refused or stored report.
 */

import { flushPromises } from "@vue/test-utils";
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { exam } from "./useExamWorkspaceEditing.history.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createFencedTransport } from "./examWorkspaceFencedTransport";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { createHistoryStore } from "./useExamWorkspaceHistoryStore";

describe("the fenced transport", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("a store answer settled after a retire installs nothing and calls no status note", async () => {
    const fence = createSyncFence();
    const baseline = exam();
    const pending: NativeExamDocument = { ...baseline, title: "Pending" };
    const stored: NativeExamDocument = { ...baseline, title: "Stored" };
    let resolveAnswer: (
      value: {
        document: NativeExamDocument;
        export_blockers: [];
        history: {
          baseline_step_id: string;
          cursor: string;
          position_step_id: string;
          step_ids: string[];
        };
      },
    ) => void = () => undefined;
    const answer = new Promise<{
      document: NativeExamDocument;
      export_blockers: [];
      history: {
        baseline_step_id: string;
        cursor: string;
        position_step_id: string;
        step_ids: string[];
      };
    }>((resolve) => {
      resolveAnswer = resolve;
    });
    const storeDouble = vi.fn(() => answer);
    const shared = { ...serverExamWorkspaceStore.shared, storeExamWorkspaceUndoStep: storeDouble };
    const transport = createFencedTransport(() => fence, shared);
    const baselineId = ref<string | null>("step-0");
    const stepIds = ref<string[]>([]);
    const position = ref<string | null>("step-0");
    const stepDocument = ref<NativeExamDocument | null>(baseline);
    const ownCursor = ref<string | null>(null);
    const historyCursor = ref<string | null>("step-0");
    const workspaceDocument = ref<NativeExamDocument | null>(pending);
    const newestId = computed(() => "step-0");
    const confirmed = vi.fn();
    const noteFailed = vi.fn();
    const noteLeaseLost = vi.fn();
    const noteRefused = vi.fn();
    const noteGateStored = vi.fn();
    const noteStored = vi.fn();
    const noteExportBlockers = vi.fn();
    const onConflict = vi.fn(async () => undefined);
    const store = createHistoryStore(
      {
        historyCursor,
        isBlocked: () => false,
        isCurrent: (token) => fence.isCurrent(token),
        keptUnstored: () => false,
        lineageId: () => "lineage-1",
        newPictures: { bytesFor: () => ({}), noteSent: () => undefined },
        noteExportBlockers,
        noteGateStored,
        noteLeaseLost,
        noteStored,
        onConflict,
        tabId: () => "tab-1",
        transport,
        workspaceDocument,
      },
      { baselineId, newestId, ownCursor, position, stepDocument, stepIds },
      { confirmed, noteFailed, noteLeaseLost, noteRefused },
      {
        flushNewer: () => undefined,
        scheduleTyping: () => undefined,
      },
    );
    const token = fence.begin();
    const storing = store.store(token, false, pending);
    expect(store.storing.value).toBe(true);
    fence.retire();
    resolveAnswer({
      document: stored,
      export_blockers: [],
      history: {
        baseline_step_id: "step-0",
        cursor: "step-1",
        position_step_id: "step-1",
        step_ids: ["step-1"],
      },
    });
    await expect(storing).resolves.toBe("failed");
    expect(baselineId.value).toBe("step-0");
    expect(stepIds.value).toEqual([]);
    expect(position.value).toBe("step-0");
    expect(stepDocument.value).toEqual(baseline);
    expect(ownCursor.value).toBeNull();
    expect(historyCursor.value).toBe("step-0");
    expect(workspaceDocument.value).toEqual(pending);
    expect(confirmed).not.toHaveBeenCalled();
    expect(noteFailed).not.toHaveBeenCalled();
    expect(noteRefused).not.toHaveBeenCalled();
    expect(noteLeaseLost).not.toHaveBeenCalled();
    expect(noteGateStored).not.toHaveBeenCalled();
    expect(noteStored).not.toHaveBeenCalled();
    expect(noteExportBlockers).not.toHaveBeenCalled();
    expect(onConflict).not.toHaveBeenCalled();
    expect(store.storing.value).toBe(false);
  });

  it("a store left hanging across a retire no longer reads as storing", async () => {
    const fence = createSyncFence();
    const baseline = exam();
    const pending: NativeExamDocument = { ...baseline, title: "Pending" };
    let resolveAnswer: (value: {
      document: NativeExamDocument;
      export_blockers: [];
      history: {
        baseline_step_id: string;
        cursor: string;
        position_step_id: string;
        step_ids: string[];
      };
    }) => void = () => undefined;
    const answer = new Promise<{
      document: NativeExamDocument;
      export_blockers: [];
      history: {
        baseline_step_id: string;
        cursor: string;
        position_step_id: string;
        step_ids: string[];
      };
    }>((resolve) => {
      resolveAnswer = resolve;
    });
    const storeDouble = vi.fn(() => answer);
    const shared = { ...serverExamWorkspaceStore.shared, storeExamWorkspaceUndoStep: storeDouble };
    const transport = createFencedTransport(() => fence, shared);
    const baselineId = ref<string | null>("step-0");
    const stepIds = ref<string[]>([]);
    const position = ref<string | null>("step-0");
    const stepDocument = ref<NativeExamDocument | null>(baseline);
    const ownCursor = ref<string | null>(null);
    const historyCursor = ref<string | null>("step-0");
    const workspaceDocument = ref<NativeExamDocument | null>(pending);
    const newestId = computed(() => "step-0");
    const store = createHistoryStore(
      {
        historyCursor,
        isBlocked: () => false,
        isCurrent: (token) => fence.isCurrent(token),
        keptUnstored: () => false,
        lineageId: () => "lineage-1",
        newPictures: { bytesFor: () => ({}), noteSent: () => undefined },
        noteExportBlockers: () => undefined,
        noteGateStored: () => undefined,
        noteLeaseLost: () => undefined,
        noteStored: () => undefined,
        onConflict: () => Promise.resolve(),
        tabId: () => "tab-1",
        transport,
        workspaceDocument,
      },
      { baselineId, newestId, ownCursor, position, stepDocument, stepIds },
      {
        confirmed: () => undefined,
        noteFailed: () => undefined,
        noteLeaseLost: () => undefined,
        noteRefused: () => undefined,
      },
      {
        flushNewer: () => undefined,
        scheduleTyping: () => undefined,
      },
    );
    const token = fence.begin();
    const storing = store.store(token, false, pending);
    expect(store.storing.value).toBe(true);
    fence.retire();
    // The store never settles, yet nothing reads as storing anymore.
    await flushPromises();
    expect(store.storing.value).toBe(false);
    resolveAnswer({
      document: pending,
      export_blockers: [],
      history: {
        baseline_step_id: "step-0",
        cursor: "step-1",
        position_step_id: "step-1",
        step_ids: ["step-1"],
      },
    });
    await expect(storing).resolves.toBe("failed");
    expect(store.storing.value).toBe(false);
  });
});
