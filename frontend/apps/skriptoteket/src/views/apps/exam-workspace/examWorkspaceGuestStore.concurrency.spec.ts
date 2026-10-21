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
import { newGuestDraft } from "./examWorkspaceGuestDraft";
import type { ExamWorkspaceGuestDraftStoragePort } from "./examWorkspaceGuestDraftStorage";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  liveAdmission,
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
        tabId: LEASE_TAB_ID,
        newPictures: {},
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
      tab_id: LEASE_TAB_ID,
    });
    await vi.waitFor(() => expect(context.mocks.createParent).toHaveBeenCalledOnce());

    // Another tab commits while the network call is in flight.
    const second = openSecondTab(context);
    const newer = await second.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: null,
      document: exam("Nyare"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
      newPictures: {},
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
      replaceIf: (expected, next) => context.storage.replaceIf(expected, next),
      replaceSlotIf: vi.fn(async () => "conflict" as const),
    };
    const loser = createGuestExamWorkspaceStore({
      api: context.api,
      ids: context.ids,
      onLimit: context.onLimit,
      storage: losing,
    });

    const error = await loser.startBlank(null, liveAdmission()).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(losing.replaceSlotIf).toHaveBeenCalledTimes(1);
  });

  it("reports the conflict and keeps the newer draft when another tab writes during a blank start", async () => {
    const context = setupGuestStore();
    const old = newGuestDraft(
      { ...exam("Draft A"), document_id: "11111111-1111-4111-8111-111111111111" },
      context.ids,
      ["note A"],
    );
    expect(await context.storage.replaceIf(null, { assets: {}, draft: old })).toBe(true);
    let releaseBlank!: (value: { document: NativeExamDocument; export_blockers: never[] }) => void;
    const pending = new Promise<{ document: NativeExamDocument; export_blockers: never[] }>(
      (resolve) => {
        releaseBlank = resolve;
      },
    );
    context.mocks.createBlank.mockReturnValueOnce(pending);
    const starting = context.store.startBlank(old.cursor, liveAdmission());
    await vi.waitFor(() => expect(context.mocks.createBlank).toHaveBeenCalledOnce());

    // Another tab replaces the slot while the public blank route is in flight.
    const newer = newGuestDraft(
      { ...exam("Newer other-tab draft"), document_id: "22222222-2222-4222-8222-222222222222" },
      context.ids,
      ["newer note"],
    );
    expect(await context.storage.replaceIf(old.cursor, { assets: {}, draft: newer })).toBe(true);
    releaseBlank({
      document: { ...exam("Stale blank completion"), document_id: "33333333-3333-4333-8333-333333333333" },
      export_blockers: [],
    });
    const error = await starting.catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    const stored = await context.storage.load();
    expect(stored?.draft.cursor).toBe(newer.cursor);
    expect(stored?.draft.saved_document.title).toBe("Newer other-tab draft");
    expect(stored?.draft.notes).toEqual(["newer note"]);
  });

  it("reports the conflict when clearing loses the browser slot", async () => {
    const context = setupGuestStore();
    await startBlank(context);
    const blocked: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: vi.fn(async () => false),
      load: () => context.storage.load(),
      replaceIf: (expected, next) => context.storage.replaceIf(expected, next),
      replaceSlotIf: (expected, next, admission) =>
        context.storage.replaceSlotIf(expected, next, admission),
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
      tabId: LEASE_TAB_ID,
      newPictures: {},
    });

    // This tab still stands on the old snapshot: its write loses the slot.
    const error = await context.store.store.shared
      .storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: null,
        document: exam("Äldre"),
        expectedCursor: opened.history_cursor,
        tabId: LEASE_TAB_ID,
        newPictures: {},
      })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    const kept = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(kept.document.title).toBe("Nyare");
  });
});
