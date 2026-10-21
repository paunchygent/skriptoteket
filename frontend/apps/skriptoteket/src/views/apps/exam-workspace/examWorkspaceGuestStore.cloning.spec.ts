/**
 * Guest exam workspace store: reactive documents are stored as plain snapshots.
 *
 * Expected behavior:
 *   The editor hands the store Vue reactive values: the autosave passes the
 *   working-copy ref's value to `storeExamWorkspaceUndoStep`. The store
 *   persists those writes through the cloning in-memory port, which fails
 *   the way IndexedDB does when a reactive value reaches it. A reactive
 *   autosave and a position move both succeed, a reload returns the edited
 *   content, and mutating the reactive source after the write does not
 *   change what a reload returns.
 */

import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import {
  createExamWorkspaceGuestDraftStorage,
  createInMemoryExamWorkspaceGuestDraftStorage,
} from "./examWorkspaceGuestDraftStorage";
import {
  DOCUMENT_ID,
  createGuestPublicApiMocks,
  createIds,
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  type GuestStoreSetup,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

type CloningStoreSetup = {
  mocks: GuestStoreSetup["mocks"];
  store: GuestStoreSetup["store"];
};

/** The production route: the store writes through the factory, not the raw port. */
function setupCloningStore(): CloningStoreSetup {
  const publicMocks = createGuestPublicApiMocks();
  const storage = createExamWorkspaceGuestDraftStorage({
    port: createInMemoryExamWorkspaceGuestDraftStorage(),
  });
  const store = createGuestExamWorkspaceStore({
    api: publicMocks,
    ids: createIds(),
    onLimit: vi.fn(),
    storage,
  });
  return {
    mocks: {
      addChild: publicMocks.addPublicExamWorkspaceChild,
      catalog: publicMocks.getPublicExamCourseCatalog,
      changeType: publicMocks.changePublicExamWorkspaceItemType,
      createBlank: publicMocks.createPublicExamWorkspaceBlank,
      createEmptyPart: publicMocks.createEmptyPublicExamWorkspacePart,
      createParent: publicMocks.createPublicExamWorkspaceParent,
      deleteChild: publicMocks.deletePublicExamWorkspaceChild,
      deleteParent: publicMocks.deletePublicExamWorkspaceParent,
      exportChecklist: publicMocks.getPublicExamWorkspaceExportChecklist,
      exportDownload: publicMocks.downloadPublicExamWorkspaceExport,
      groupItems: publicMocks.groupPublicExamWorkspaceItems,
      importQti: publicMocks.importPublicExamWorkspaceQti,
      misspellings: publicMocks.requestPublicExamWorkspaceAnswerMisspellings,
      moveItem: publicMocks.movePublicExamWorkspaceItem,
      reorderChildren: publicMocks.reorderPublicExamWorkspaceChildren,
    },
    store,
  };
}

async function startBlank(context: CloningStoreSetup): Promise<void> {
  context.mocks.createBlank.mockResolvedValue({
    document: exam("Original"),
    export_blockers: [],
  });
  await context.store.startBlank(null);
}

describe("examWorkspaceGuestStore reactive snapshots", () => {
  it("stores a reactive autosave document and reloads the edited content", async () => {
    const context = setupCloningStore();
    await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    const edited = ref(exam("Redigerad"));
    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: edited.value,
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
    });

    expect(step.document.title).toBe("Redigerad");
    const reloaded = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(reloaded.document.title).toBe("Redigerad");
  });

  it("stores a reactive autosave payload and moves the position back to the baseline", async () => {
    const context = setupCloningStore();
    await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const history = await context.store.store.shared.getExamWorkspaceHistory(DOCUMENT_ID);

    const edited = ref(exam("Sparad"));
    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: edited.value,
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
    });

    expect(step.document.title).toBe("Sparad");
    const undone = await context.store.moveToHistoryStep(DOCUMENT_ID, {
      expectedCursor: step.history.cursor,
      tabId: LEASE_TAB_ID,
      stepId: history.baseline_step_id,
    });
    expect(undone.history.position_step_id).toBe(history.baseline_step_id);
    const reloaded = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(reloaded.saved_document.title).toBe("Original");
    expect(reloaded.saved_document.revision).toBe(3);
  });

  it("keeps the stored draft when the reactive source is mutated after the write", async () => {
    const context = setupCloningStore();
    await startBlank(context);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    const edited = ref(exam("Redigerad"));
    await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: edited.value,
      expectedCursor: opened.history_cursor,
      tabId: LEASE_TAB_ID,
    });
    edited.value.title = "Changed afterwards";

    const reloaded = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    expect(reloaded.document.title).toBe("Redigerad");
  });
});
