/**
 * Guest Nytt prov: a retired creation never replaces the retained draft
 * (TASK-SKRIPT-40-04-21, review round 2 F1).
 *
 * Expected behavior:
 *   The guest slot is replaced only while the creation still holds live
 *   replacement authority. Guest tab A starts Nytt prov and its blank
 *   response is deferred. When A's creation is retired first (tab B takes
 *   over the lease and the source generation retires, or the workspace is
 *   disposed), the late blank never reaches the slot: the retained draft,
 *   its history and its picture bytes stay, the old lineage still reads, and
 *   the new owner's first edit stores against the unchanged cursor. The
 *   same holds when A's own creation is still live but B took the lease
 *   after A's lease check and before A's slot write (review rereview 3 F1):
 *   the lease decision holds at the destructive write itself.
 *
 *   The spec runs the real replacement coordinator, save composable, guest
 *   store and sync fence over the in-memory draft and lease adapters. Only
 *   the public blank route and the editing session's settle are doubles.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { computed, ref } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { PublicExamWorkspaceCommandResult } from "../../../api/publicExamWorkspace";
import { createReplacementCoordinator } from "./examWorkspaceReplacementCoordinator";
import type { ExamWorkspaceReplacementDeps } from "./examWorkspaceReplacementTypes";
import { GUEST_EDIT_LEASE_TTL_MS } from "./examWorkspaceGuestEditLease";
import {
  createInMemoryGuestEditLeaseStorage,
  type InMemoryGuestEditLeaseStorage,
} from "./examWorkspaceGuestEditLeaseMemory";
import { createSyncFence } from "./examWorkspaceSyncFence";
import {
  exam,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  liveAdmission,
  openSecondTab,
  pictureExam,
  setupGuestStore,
  type GuestStoreSetup,
} from "./examWorkspaceGuestStore.specSupport";
import { useExamWorkspaceSave } from "./useExamWorkspaceSave";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

installGuestStoreObjectUrls();

const TAB_A = LEASE_TAB_ID;
const TAB_B = "20000000-0000-4000-8000-00000000000b";
const BLANK_ID = "44444444-0000-4000-8000-000000000004";

type TabA = {
  coordinator: ReturnType<typeof createReplacementCoordinator>;
  copyBusy: { value: boolean };
  fence: ReturnType<typeof createSyncFence>;
  installed: ExamWorkspaceDocumentResponse[];
  /** The workspace scope ends, as `isDisposed` reports to the coordinator. */
  markDisposed: () => void;
};

/** Seed the slot with a picture exam plus one stored history step; A holds the lease. */
async function seedRetainedDraft(context: GuestStoreSetup): Promise<{
  lineageId: string;
  opened: ExamWorkspaceDocumentResponse;
}> {
  await context.leaseStorage.claim(TAB_A, Date.now());
  const png = new Blob(["png!"], { type: "image/png" });
  context.mocks.importQti.mockResolvedValue({
    assets: { asset_001: png },
    document: pictureExam("Keep this exam"),
    notes: [],
  });
  const lineageId = await context.store.startFromQti(
    new File(["zip"], "Prov.zip", { type: "application/zip" }),
    null,
    liveAdmission(TAB_A),
  );
  const loaded = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
  const edited: NativeExamDocument = { ...loaded.document, title: "Keep this exam, edited" };
  await context.store.store.shared.storeExamWorkspaceUndoStep(lineageId, {
    afterStepId: null,
    document: edited,
    expectedCursor: loaded.history_cursor,
    tabId: TAB_A,
    newPictures: {},
  });
  const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
  return { lineageId, opened };
}

/** Tab A's workspace: the real coordinator over the real save composable and guest store. */
function openTabA(context: GuestStoreSetup, opened: ExamWorkspaceDocumentResponse): TabA {
  const fence = createSyncFence();
  const copyBusy = ref(false);
  const summary = ref<ExamWorkspaceDocumentSummary | null>(opened.summary);
  const historyCursor = ref<string | null>(opened.history_cursor);
  const workspaceDocument = ref<NativeExamDocument | null>(opened.document);
  const save = useExamWorkspaceSave({
    copyBusy,
    getFence: () => fence,
    historyCursor,
    isBusy: computed(() => copyBusy.value),
    store: context.store.store,
    summary,
    workspaceDocument,
  });
  const installed: ExamWorkspaceDocumentResponse[] = [];
  let disposed = false;
  const deps: ExamWorkspaceReplacementDeps = {
    abandonAttempt: () => undefined,
    adoptSelectedOpening: () => undefined,
    beginCopy: () => null,
    beginNewExam: (expectedCursor, isLive) =>
      save.beginNewExam(expectedCursor, { isLive, tabId: TAB_A }),
    captureKept: () => undefined,
    claimSelectedLease: () => undefined,
    fence,
    hasActiveStore: () => false,
    hasUnconfirmed: () => false,
    installedSource: () => summary.value?.lineage_id ?? null,
    installReplacementDocument: (_token, response) => {
      installed.push(response);
    },
    isDisposed: () => disposed,
    isEditing: () => true,
    isVisibleDirty: () => false,
    notifyCopyFailed: () => undefined,
    notifyNewExamFailed: () => undefined,
    notifyRouteFailed: () => undefined,
    notifyRouteUnreadable: () => undefined,
    openRouteTarget: () => Promise.resolve("installed"),
    projectAddress: () => undefined,
    recoverRetainedSource: () => undefined,
    releaseCopyBusy: () => {
      copyBusy.value = false;
    },
    replaceCopy: (run) => run(),
    retireGeneration: () => fence.retire(),
    settleEdit: () => Promise.resolve(true),
    waitForRouterIdle: () => Promise.resolve(),
  };
  return {
    coordinator: createReplacementCoordinator(deps),
    copyBusy,
    fence,
    installed,
    markDisposed: () => {
      disposed = true;
    },
  };
}

function blankResponse(): PublicExamWorkspaceCommandResult {
  return {
    document: { ...exam(""), document_id: BLANK_ID },
    export_blockers: [],
  };
}

/** The retained draft is intact: lineage, cursor, history and picture bytes. */
async function expectRetainedDraft(
  context: GuestStoreSetup,
  lineageId: string,
  opened: ExamWorkspaceDocumentResponse,
): Promise<void> {
  const stored = await context.storage.load();
  expect(stored?.draft.lineage_id).toBe(lineageId);
  expect(stored?.draft.cursor).toBe(opened.history_cursor);
  expect(stored?.draft.saved_document.title).toBe("Keep this exam, edited");
  expect(stored?.draft.steps).toHaveLength(1);
  expect(Object.keys(stored?.assets ?? {})).toEqual(["asset_001"]);
}

describe("guest Nytt prov after its creation is retired", () => {
  it("keeps the retained draft when tab B takes over before the blank arrives", async () => {
    const context = setupGuestStore();
    const { lineageId, opened } = await seedRetainedDraft(context);
    const tabA = openTabA(context, opened);
    const blank = deferred<PublicExamWorkspaceCommandResult>();
    context.mocks.createBlank.mockReturnValue(blank.promise);

    const outcome = tabA.coordinator.submitNewExam(opened.history_cursor);
    await flushPromises();
    expect(context.mocks.createBlank).toHaveBeenCalledTimes(1);
    expect(tabA.copyBusy.value).toBe(true);

    // Tab B asks, A yields its lease, B claims it; A's gate retires the
    // source generation and tells the coordinator, exactly as leaseLost does.
    await context.leaseStorage.requestTakeover(TAB_B, Date.now());
    await context.leaseStorage.release(TAB_A);
    const claimed = await context.leaseStorage.claim(TAB_B, Date.now());
    expect(claimed.held).toBe(true);
    tabA.fence.retire();
    tabA.coordinator.notifySourceRetired();
    await expect(outcome).resolves.toBe("failed");
    expect(tabA.copyBusy.value).toBe(false);

    // B loads the original at the unchanged cursor; nothing new is stored yet.
    const tabB = openSecondTab(context);
    const loadedByB = await tabB.store.shared.getExamWorkspaceDocument(lineageId);
    expect(loadedByB.history_cursor).toBe(opened.history_cursor);

    blank.resolve(blankResponse());
    await flushPromises();

    expect(tabA.installed).toEqual([]);
    await expectRetainedDraft(context, lineageId, opened);
    const reread = await tabB.store.shared.getExamWorkspaceDocument(lineageId);
    expect(reread.document.title).toBe("Keep this exam, edited");
    const step = await tabB.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: loadedByB.history_cursor,
      document: { ...loadedByB.document, title: "B's first edit" },
      expectedCursor: loadedByB.history_cursor,
      tabId: TAB_B,
      newPictures: {},
    });
    const stored = await context.storage.load();
    expect(stored?.draft.lineage_id).toBe(lineageId);
    expect(stored?.draft.cursor).toBe(step.history.cursor);
    expect(stored?.draft.saved_document.title).toBe("B's first edit");
    expect(Object.keys(stored?.assets ?? {})).toEqual(["asset_001"]);
  });

  it("keeps the retained draft when the workspace is disposed before the blank arrives", async () => {
    const context = setupGuestStore();
    const { lineageId, opened } = await seedRetainedDraft(context);
    const tabA = openTabA(context, opened);
    const blank = deferred<PublicExamWorkspaceCommandResult>();
    context.mocks.createBlank.mockReturnValue(blank.promise);

    const outcome = tabA.coordinator.submitNewExam(opened.history_cursor);
    await flushPromises();
    expect(context.mocks.createBlank).toHaveBeenCalledTimes(1);

    // Disposal terminates the creation without bumping the fence and while
    // A still holds the lease: only the creation's own authority can refuse.
    tabA.markDisposed();
    tabA.coordinator.dispose();
    await expect(outcome).resolves.toBe("failed");

    blank.resolve(blankResponse());
    await flushPromises();

    expect(tabA.installed).toEqual([]);
    await expectRetainedDraft(context, lineageId, opened);
    const reread = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(reread.history_cursor).toBe(opened.history_cursor);
  });

  it("keeps the retained draft when the page is hidden before the blank arrives", async () => {
    const context = setupGuestStore();
    const { lineageId, opened } = await seedRetainedDraft(context);
    const tabA = openTabA(context, opened);
    const blank = deferred<PublicExamWorkspaceCommandResult>();
    context.mocks.createBlank.mockReturnValue(blank.promise);

    const outcome = tabA.coordinator.submitNewExam(opened.history_cursor);
    await flushPromises();
    expect(context.mocks.createBlank).toHaveBeenCalledTimes(1);

    // pagehide retires the generation and terminates silently; A still
    // holds the lease, so only the creation's own authority can refuse.
    tabA.fence.retire();
    tabA.coordinator.notifyPageHidden();
    await expect(outcome).resolves.toBe("failed");

    blank.resolve(blankResponse());
    await flushPromises();

    expect(tabA.installed).toEqual([]);
    await expectRetainedDraft(context, lineageId, opened);
  });

  it("keeps the retained draft when tab B takes the lease after A's lease check, before A's slot write", async () => {
    // The lease slot pauses after it answers A's lease check: in that window
    // B claims A's stalled lease and loads the original, while A has not yet
    // seen the loss, so A's creation is still live.
    const lease = createInMemoryGuestEditLeaseStorage();
    let afterLeaseRead: (() => Promise<void>) | null = null;
    const leaseStorage: InMemoryGuestEditLeaseStorage = {
      ...lease,
      async load() {
        const snapshot = await lease.load();
        const pause = afterLeaseRead;
        afterLeaseRead = null;
        if (pause !== null) {
          await pause();
        }
        return snapshot;
      },
    };
    const context = setupGuestStore({ leaseStorage });
    const { lineageId, opened } = await seedRetainedDraft(context);
    const tabA = openTabA(context, opened);
    const tabB = openSecondTab(context);
    const blank = deferred<PublicExamWorkspaceCommandResult>();
    context.mocks.createBlank.mockReturnValue(blank.promise);

    const outcome = tabA.coordinator.submitNewExam(opened.history_cursor);
    await flushPromises();
    expect(context.mocks.createBlank).toHaveBeenCalledTimes(1);

    let loadedByB: ExamWorkspaceDocumentResponse | null = null;
    afterLeaseRead = async () => {
      // A's heartbeat stalled past the lease lifetime, so B's claim succeeds
      // without A answering a takeover; A's fence and selection stay current.
      const claimed = await lease.claim(TAB_B, Date.now() + GUEST_EDIT_LEASE_TTL_MS + 1);
      expect(claimed.held).toBe(true);
      loadedByB = await tabB.store.shared.getExamWorkspaceDocument(lineageId);
    };
    blank.resolve(blankResponse());
    await expect(outcome).resolves.toBe("failed");

    expect(loadedByB).not.toBeNull();
    const loaded = loadedByB as unknown as ExamWorkspaceDocumentResponse;
    expect(loaded.history_cursor).toBe(opened.history_cursor);
    expect(tabA.installed).toEqual([]);
    await expectRetainedDraft(context, lineageId, opened);
    const step = await tabB.store.shared.storeExamWorkspaceUndoStep(lineageId, {
      afterStepId: loaded.history_cursor,
      document: { ...loaded.document, title: "B's first edit" },
      expectedCursor: loaded.history_cursor,
      tabId: TAB_B,
      newPictures: {},
    });
    const stored = await context.storage.load();
    expect(stored?.draft.lineage_id).toBe(lineageId);
    expect(stored?.draft.cursor).toBe(step.history.cursor);
    expect(stored?.draft.saved_document.title).toBe("B's first edit");
    expect(Object.keys(stored?.assets ?? {})).toEqual(["asset_001"]);
  });

  it("still replaces the slot when the creation keeps its authority until the blank arrives", async () => {
    const context = setupGuestStore();
    const { opened } = await seedRetainedDraft(context);
    const tabA = openTabA(context, opened);
    const blank = deferred<PublicExamWorkspaceCommandResult>();
    context.mocks.createBlank.mockReturnValue(blank.promise);

    const outcome = tabA.coordinator.submitNewExam(opened.history_cursor);
    await flushPromises();
    blank.resolve(blankResponse());

    await expect(outcome).resolves.toBe("created");
    const stored = await context.storage.load();
    expect(stored?.draft.lineage_id).toBe(BLANK_ID);
    expect(stored?.assets).toEqual({});
    expect(tabA.installed.map((response) => response.summary.lineage_id)).toEqual([BLANK_ID]);
  });
});
