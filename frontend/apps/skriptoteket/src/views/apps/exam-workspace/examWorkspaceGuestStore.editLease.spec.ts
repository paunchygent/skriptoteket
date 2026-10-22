/**
 * Guest exam workspace store: the edit lease guards every write.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour items 7 and 8, decision
 * D5, unit K8):
 *   Like the server's `require_edit_lease`, a write from a tab that does not
 *   hold a live lease reports 409 `EDIT_LEASE_HELD` and changes nothing. A
 *   tab that holds the lease, a missing lease and an expired lease all pass.
 *   A stale cursor still reports the ordinary cursor conflict first.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import {
  DOCUMENT_ID,
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  setupGuestStore,
  startBlank,
  type GuestStoreSetup,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

async function startBlankSetup(title = "Original"): Promise<GuestStoreSetup> {
  const context = setupGuestStore();
  await startBlank(context, title);
  return context;
}

const FOREIGN_TAB_ID = "other-tab";

describe("examWorkspaceGuestStore edit lease", () => {
  it("refuses a store from a tab that does not hold the live lease", async () => {
    const context = await startBlankSetup();
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    await context.leaseStorage.claim(FOREIGN_TAB_ID, Date.now());

    const error = await context.store.store.shared
      .storeExamWorkspaceUndoStep(DOCUMENT_ID, {
        afterStepId: null,
        document: exam("Främmande"),
        expectedCursor: opened.history_cursor,
        tabId: LEASE_TAB_ID,
        newPictures: {},
      })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "EDIT_LEASE_HELD", status: 409 });
    const history = await context.store.store.shared.getExamWorkspaceHistory(DOCUMENT_ID);
    expect(history.step_ids).toEqual([]);
  });

  it("stores when the tab holds the lease", async () => {
    const context = await startBlankSetup();
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    await context.leaseStorage.claim(LEASE_TAB_ID, Date.now());

    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Egen"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
      newPictures: {},
    });

    expect(step.document.title).toBe("Egen");
  });

  it("stores when no lease is recorded and when the lease has expired", async () => {
    const fresh = await startBlankSetup();
    const opened = await fresh.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const stored = await fresh.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Utan"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
      newPictures: {},
    });
    expect(stored.document.title).toBe("Utan");

    const expired = await startBlankSetup();
    const reopened = await expired.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    await expired.leaseStorage.claim(FOREIGN_TAB_ID, Date.now() - 16_000);
    const restep = await expired.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Efter"),
      expectedCursor: reopened.history_cursor,
      tabId: LEASE_TAB_ID,
      newPictures: {},
    });
    expect(restep.document.title).toBe("Efter");
  });

  it("reports the cursor conflict before checking the lease", async () => {
    const context = await startBlankSetup();
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Nyare"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
      newPictures: {},
    });
    await context.leaseStorage.claim(FOREIGN_TAB_ID, Date.now());

    const error = await context.store.store.shared
      .storeExamWorkspaceUndoStep(DOCUMENT_ID, {
        afterStepId: null,
        document: exam("Gammal"),
        expectedCursor: opened.history_cursor,
        tabId: LEASE_TAB_ID,
        newPictures: {},
      })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
  });

  it("refuses a position move and a structure command without the lease", async () => {
    const context = await startBlankSetup();
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const stored = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Steg"),
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
      newPictures: {},
    });
    await context.leaseStorage.claim(FOREIGN_TAB_ID, Date.now());

    const moveError = await context.store.store.shared
      .moveExamWorkspaceHistoryPosition(DOCUMENT_ID, {
        expectedCursor: stored.history.cursor,
        stepId: stored.history.baseline_step_id,
        tabId: LEASE_TAB_ID,
      })
      .catch((caught: unknown) => caught);
    expect(moveError).toBeInstanceOf(ApiError);
    expect(moveError).toMatchObject({ code: "EDIT_LEASE_HELD", status: 409 });

    const commandError = await context.store.store.shared
      .groupExamWorkspaceItems(DOCUMENT_ID, ["item_001"], stored.history.cursor, LEASE_TAB_ID)
      .catch((caught: unknown) => caught);
    expect(commandError).toBeInstanceOf(ApiError);
    expect(commandError).toMatchObject({ code: "EDIT_LEASE_HELD", status: 409 });
    const kept = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(kept.document.title).toBe("Steg");
  });
});
