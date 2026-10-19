/**
 * Guest exam workspace store: concurrent-tab conflicts.
 *
 * Expected behavior (review findings F2/F3):
 *   The cursor guard is atomic with the actual write across tabs and store
 *   instances. Two writers over the same expected cursor commit exactly one
 *   draft; the loser gets the established 409 conflict and the network result
 *   of a delayed command is discarded instead of overwriting the newer draft.
 *   A blank start that loses the slot reports the same conflict.
 */

import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import type { ExamWorkspaceGuestDraftStoragePort } from "./examWorkspaceGuestDraftStorage";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  openSecondTab,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

describe("examWorkspaceGuestStore concurrent writes", () => {
  it("commits exactly one of two same-cursor writes and reports the conflict", async () => {
    const context = setupGuestStore();
    const lineageId = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const second = openSecondTab(context);

    const write = (
      store: typeof context.store,
      title: string,
    ): Promise<{ document: NativeExamDocument }> =>
      store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: null,
        document: exam(title),
        expectedCursor: opened.history_cursor,
      });

    const outcomes = await Promise.allSettled([write(context.store, "Flik A"), write(second, "Flik B")]);

    const fulfilled = outcomes.filter(
      (outcome): outcome is PromiseFulfilledResult<{ document: NativeExamDocument }> =>
        outcome.status === "fulfilled",
    );
    const rejected = outcomes.filter(
      (outcome): outcome is PromiseRejectedResult => outcome.status === "rejected",
    );
    expect(fulfilled).toHaveLength(1);
    expect(rejected).toHaveLength(1);
    expect(rejected[0]?.reason).toBeInstanceOf(ApiError);
    expect(rejected[0]?.reason).toMatchObject({ code: "CONFLICT", status: 409 });

    const stored = await context.storage.load();
    expect(stored?.draft.steps).toHaveLength(1);
    expect(stored?.draft.steps[0]?.document.title).toBe(fulfilled[0]?.value.document.title);
  });

  it("rejects a delayed command after another write lands and keeps the newer draft", async () => {
    const context = setupGuestStore();
    const lineageId = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    let resolveCommand!: (value: { document: NativeExamDocument; export_blockers: never[] }) => void;
    const pending = new Promise<{ document: NativeExamDocument; export_blockers: never[] }>(
      (resolve) => {
        resolveCommand = resolve;
      },
    );
    context.mocks.createParent.mockReturnValueOnce(pending);
    const command = context.store.store.shared.createExamWorkspaceParent(lineageId, {
      child: newTeacherItem("item_002", 2, "free_text"),
      expected_cursor: opened.history_cursor,
      instruction: [],
      position: 0,
    });
    await vi.waitFor(() => expect(context.mocks.createParent).toHaveBeenCalledOnce());

    // Another tab commits while the network call is in flight.
    const second = openSecondTab(context);
    const newer = await second.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("Nyare"),
      expectedCursor: opened.history_cursor,
    });

    resolveCommand({ document: exam("Förlorare"), export_blockers: [] });
    const error = await command.catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect((await context.storage.load())?.draft.cursor).toBe(newer.history.cursor);
    const kept = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(kept.document.title).toBe("Nyare");
  });

  it("reports the conflict when a blank start loses the browser slot", async () => {
    const context = setupGuestStore();
    context.mocks.createBlank.mockResolvedValue({
      document: exam("Original"),
      export_blockers: [],
    });
    const losing: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: (expected) => context.storage.clearIf(expected),
      load: () => context.storage.load(),
      replaceIf: vi.fn(async () => false),
    };
    const loser = createGuestExamWorkspaceStore({
      api: context.api,
      ids: context.ids,
      onLimit: context.onLimit,
      storage: losing,
    });

    const error = await loser.startBlank().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(losing.replaceIf).toHaveBeenCalledTimes(1);
  });

  it("reports the conflict when clearing loses the browser slot", async () => {
    const context = setupGuestStore();
    await startBlank(context);
    const blocked: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: vi.fn(async () => false),
      load: () => context.storage.load(),
      replaceIf: (expected, next) => context.storage.replaceIf(expected, next),
    };
    const store = createGuestExamWorkspaceStore({
      api: context.api,
      ids: context.ids,
      onLimit: context.onLimit,
      storage: blocked,
    });

    const error = await store.clear().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(await context.storage.load()).not.toBeNull();
  });

  it("rejects a delayed save after another write lands and keeps the newer draft", async () => {
    const context = setupGuestStore();
    const lineageId = await startBlank(context, "Original");
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    const second = openSecondTab(context);

    // The second tab saves first and rotates the cursor.
    await second.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("Nyare"),
      expectedCursor: opened.history_cursor,
    });

    // This tab still stands on the old snapshot: its write loses the slot.
    const error = await context.store.store.shared
      .storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: null,
        document: exam("Äldre"),
        expectedCursor: opened.history_cursor,
      })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    const kept = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(kept.document.title).toBe("Nyare");
  });
});
