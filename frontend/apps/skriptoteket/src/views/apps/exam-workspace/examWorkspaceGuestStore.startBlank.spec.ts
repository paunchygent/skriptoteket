/**
 * Guest exam workspace store: Nytt prov replaces through the D9 cursor
 * (TASK-SKRIPT-40-04-21, F1 repair).
 *
 * Expected behavior:
 *   `startBlank` passes its `expectedCursor` straight to the conditional
 *   write, with no fresh slot read in between. It replaces the slot when the
 *   stored cursor equals it; when another tab stored a newer cursor first
 *   it reports the established 409 conflict and keeps the stored draft
 *   byte-for-byte; with a null cursor it refuses a non-empty slot.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import {
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  openSecondTab,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

describe("examWorkspaceGuestStore startBlank", () => {
  it("replaces the slot when the stored cursor equals the D9 cursor", async () => {
    const context = setupGuestStore();
    const first = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(first);
    context.mocks.createBlank.mockResolvedValue({
      document: { ...exam("Second"), document_id: "22222222-2222-4222-8222-222222222222" },
      export_blockers: [],
    });

    const second = await context.store.startBlank(opened.history_cursor);

    expect(second).toBe("22222222-2222-4222-8222-222222222222");
    const stored = await context.storage.load();
    expect(stored?.draft.saved_document.title).toBe("Second");
    expect(stored?.draft.cursor).not.toBe(opened.history_cursor);
  });

  it("reports the conflict and keeps the stored draft byte-for-byte when another tab stored first", async () => {
    const context = setupGuestStore();
    const first = await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(first);
    const second = openSecondTab(context);
    const newer = await second.store.shared.storeExamWorkspaceUndoStep(first, {
      afterStepId: null,
      document: exam("Nyare"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
    });
    const before = JSON.stringify(await context.storage.load());
    context.mocks.createBlank.mockResolvedValue({
      document: exam("Förlorare"),
      export_blockers: [],
    });

    const error = await context.store.startBlank(opened.history_cursor).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(JSON.stringify(await context.storage.load())).toBe(before);
    const stored = await context.storage.load();
    expect(stored?.draft.cursor).toBe(newer.history.cursor);
    expect(stored?.draft.saved_document.title).toBe("Nyare");
  });

  it("refuses a non-empty slot when the D9 cursor is null", async () => {
    const context = setupGuestStore();
    await startBlank(context);
    const before = JSON.stringify(await context.storage.load());
    context.mocks.createBlank.mockResolvedValue({
      document: exam("Förlorare"),
      export_blockers: [],
    });

    const error = await context.store.startBlank(null).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(JSON.stringify(await context.storage.load())).toBe(before);
  });
});
