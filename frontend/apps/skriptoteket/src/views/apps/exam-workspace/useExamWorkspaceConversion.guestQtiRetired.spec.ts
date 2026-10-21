/**
 * Guest QTI import through the conversion intake: a disposed import's late
 * parse never replaces the retained draft (TASK-SKRIPT-40-04-21, rereview 3 F5).
 *
 * Expected behavior:
 *   Guest tab A imports a QTI .zip over its retained draft C and the parse
 *   response waits. A's workspace scope is disposed before the response
 *   arrives, while A's lease record is still live. The late result neither
 *   writes the slot nor opens anything: C, its history and its picture bytes
 *   stay, and tab B, which loaded C meanwhile, claims the lease and stores
 *   its first edit against the unchanged cursor.
 *
 *   The spec runs the real conversion composable over the real guest store
 *   and the in-memory draft and lease adapters; only the public parse route
 *   is a double.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";
import type { Ref } from "vue";

import type {
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { PublicExamWorkspaceQtiImportResult } from "../../../api/publicExamWorkspace";
import {
  exam,
  expectRetainedAndNewOwnerStores,
  installGuestStoreObjectUrls,
  LEASE_TAB_ID,
  openSecondTab,
  seedRetainedPictureDraft,
  setupGuestStore,
  type GuestStoreSetup,
} from "./examWorkspaceGuestStore.specSupport";
import { createSyncFence } from "./examWorkspaceSyncFence";
import {
  useExamWorkspaceConversion,
  type ExamWorkspaceConversionBinding,
} from "./useExamWorkspaceConversion";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

installGuestStoreObjectUrls();

const TAB_A = LEASE_TAB_ID;
const TAB_B = "20000000-0000-4000-8000-00000000000b";

function guestBinding(context: GuestStoreSetup): ExamWorkspaceConversionBinding {
  const fence = createSyncFence();
  return {
    applyResponse: vi.fn(),
    beginDocumentRead: () => (response) => response,
    getFence: () => fence,
    isCurrent: (token) => fence.isCurrent(token),
    isDirty: ref(false),
    isSaving: () => false,
    noteImportStarted: vi.fn(),
    serverDocument: ref<NativeExamDocument | null>(null),
    store: context.store.store,
    summary: ref(null) as Ref<ExamWorkspaceDocumentSummary | null>,
    tabId: () => TAB_A,
    workspaceDocument: ref<NativeExamDocument | null>(null),
  };
}

describe("guest QTI import after the workspace is disposed", () => {
  it("keeps the retained draft and opens nothing when the late parse arrives", async () => {
    setActivePinia(createPinia());
    const context = setupGuestStore();
    const { lineageId } = await seedRetainedPictureDraft(context, TAB_A);
    const parse = deferred<PublicExamWorkspaceQtiImportResult>();
    context.mocks.importQti.mockReturnValueOnce(parse.promise);
    const openImported = vi.fn(async () => "installed" as const);
    const scope = effectScope();
    const conversion = scope.run(() =>
      useExamWorkspaceConversion(() => false, guestBinding(context), openImported),
    );
    if (!conversion) throw new Error("expected the composable");

    const importing = conversion.importDocument(
      new File(["qti"], "Nytt_prov.zip", { type: "application/zip" }),
      null,
    );
    await flushPromises();
    // The seed read one package; this is the second parse.
    expect(context.mocks.importQti).toHaveBeenCalledTimes(2);

    scope.stop();
    const tabB = openSecondTab(context);
    const loadedByB = await tabB.store.shared.getExamWorkspaceDocument(lineageId);

    parse.resolve({ assets: {}, document: exam("Imported"), notes: [] });
    await importing;

    expect(openImported).not.toHaveBeenCalled();
    await context.leaseStorage.release(TAB_A);
    await context.leaseStorage.claim(TAB_B, Date.now());
    await expectRetainedAndNewOwnerStores(context, { store: tabB, tabId: TAB_B }, lineageId, loadedByB);
  });
});
