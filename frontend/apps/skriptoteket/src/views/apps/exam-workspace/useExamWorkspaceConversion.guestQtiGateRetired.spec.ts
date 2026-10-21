/**
 * Guest QTI import after the sync gate retired its authority: a late parse
 * never replaces the retained draft once the lease frees again
 * (TASK-SKRIPT-40-04-21, rereview 4 F5).
 *
 * Expected behavior:
 *   Guest tab A edits retained draft C under the real sync gate and imports a
 *   QTI .zip; the parse response waits. A then loses its write authority:
 *   either tab B takes the lease over (the gate receives `leaseLost`) or the
 *   page is hidden (the gate receives `pageHidden`), and A's lease record is
 *   released. Afterwards the lease store is free again, because B released
 *   its lease, B's lease expired, or nobody claimed it. The late parse
 *   neither writes the slot nor opens anything: C, its history and its
 *   picture bytes stay, and B stores its first edit against the unchanged
 *   cursor. A positive control shows that an import whose gate authority
 *   stayed current still replaces the slot and opens the imported exam.
 *
 *   The spec runs the real conversion composable, the real sync gate and the
 *   real guest store over the in-memory draft and lease adapters; only the
 *   public parse route and the gate's document ports are doubles.
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
import { GUEST_EDIT_LEASE_TTL_MS } from "./examWorkspaceGuestEditLease";
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
import {
  useExamWorkspaceConversion,
  type ExamWorkspaceConversionBinding,
} from "./useExamWorkspaceConversion";
import {
  createGate,
  deferred,
  LINEAGE,
  succeedLoad,
  type SyncGateHarness,
} from "./useExamWorkspaceSyncGate.specSupport";

installGuestStoreObjectUrls();

const TAB_A = LEASE_TAB_ID;
const TAB_B = "20000000-0000-4000-8000-00000000000b";

type Retirement = "leaseLost" | "pageHidden";
type LeaseAfter = "released" | "expired" | "never-claimed";

function gateBinding(context: GuestStoreSetup, harness: SyncGateHarness): ExamWorkspaceConversionBinding {
  return {
    applyResponse: vi.fn(),
    beginDocumentRead: () => (response) => response,
    getFence: () => harness.gate.fence,
    isCurrent: (token) => harness.gate.fence.isCurrent(token),
    isDirty: ref(false),
    isSaving: () => false,
    serverDocument: ref<NativeExamDocument | null>(null),
    store: context.store.store,
    summary: ref(null) as Ref<ExamWorkspaceDocumentSummary | null>,
    tabId: () => TAB_A,
    workspaceDocument: ref<NativeExamDocument | null>(null),
  };
}

/** Tab A edits C under an editing gate and starts a QTI import whose parse waits. */
async function startDeferredImport(context: GuestStoreSetup) {
  const harness = createGate();
  harness.gate.openExam(LINEAGE, false);
  await succeedLoad(harness, exam());
  expect(harness.gate.phase.value).toBe("editing");
  const parse = deferred<PublicExamWorkspaceQtiImportResult>();
  context.mocks.importQti.mockReturnValueOnce(parse.promise);
  const openImported = vi.fn(async () => "installed" as const);
  const scope = effectScope();
  const conversion = scope.run(() =>
    useExamWorkspaceConversion(() => false, gateBinding(context, harness), openImported),
  );
  if (!conversion) throw new Error("expected the composable");
  const importing = conversion.importDocument(
    new File(["qti"], "Nytt_prov.zip", { type: "application/zip" }),
    null,
  );
  await flushPromises();
  // The seed read one package; this is the second parse.
  expect(context.mocks.importQti).toHaveBeenCalledTimes(2);
  return { harness, importing, openImported, parse, scope };
}

async function retireA(context: GuestStoreSetup, harness: SyncGateHarness, how: Retirement): Promise<void> {
  if (how === "leaseLost") {
    harness.gate.leaseLost();
  } else {
    harness.gate.pageHidden();
  }
  await harness.settle();
  expect(harness.gate.phase.value).toBe("readonly");
  await context.leaseStorage.release(TAB_A);
}

/** B holds the lease for a while (or never), then the lease store is free again. */
async function freeLeaseAgain(context: GuestStoreSetup, after: LeaseAfter): Promise<void> {
  if (after === "released") {
    await context.leaseStorage.claim(TAB_B, Date.now());
    await context.leaseStorage.release(TAB_B);
  } else if (after === "expired") {
    await context.leaseStorage.claim(TAB_B, Date.now() - GUEST_EDIT_LEASE_TTL_MS - 1);
  }
}

describe("guest QTI import after the sync gate retired its authority", () => {
  it.each<[Retirement, LeaseAfter]>([
    ["leaseLost", "released"],
    ["leaseLost", "expired"],
    ["pageHidden", "never-claimed"],
    ["pageHidden", "expired"],
  ])(
    "after %s with the lease %s, the late parse keeps C and opens nothing",
    async (how, after) => {
      setActivePinia(createPinia());
      const context = setupGuestStore();
      const { lineageId } = await seedRetainedPictureDraft(context, TAB_A);
      const { harness, importing, openImported, parse, scope } = await startDeferredImport(context);

      await retireA(context, harness, how);
      const tabB = openSecondTab(context);
      const loadedByB = await tabB.store.shared.getExamWorkspaceDocument(lineageId);
      await freeLeaseAgain(context, after);

      parse.resolve({ assets: {}, document: exam("Imported"), notes: [] });
      await importing;

      expect(openImported).not.toHaveBeenCalled();
      await context.leaseStorage.claim(TAB_B, Date.now());
      await expectRetainedAndNewOwnerStores(context, { store: tabB, tabId: TAB_B }, lineageId, loadedByB);
      scope.stop();
    },
  );

  it("replaces the slot and opens the import while its gate authority stays current", async () => {
    setActivePinia(createPinia());
    const context = setupGuestStore();
    const { opened } = await seedRetainedPictureDraft(context, TAB_A);
    const { importing, openImported, parse, scope } = await startDeferredImport(context);

    parse.resolve({ assets: {}, document: exam("Imported"), notes: [] });
    await importing;

    // The imported lineage replaced C: new cursor, no history, no pictures.
    const stored = await context.storage.load();
    expect(stored?.draft.cursor).not.toBe(opened.history_cursor);
    expect(stored?.draft.saved_document.title).toBe("Imported");
    expect(stored?.draft.steps).toHaveLength(0);
    expect(Object.keys(stored?.assets ?? {})).toEqual([]);
    expect(openImported).toHaveBeenCalledWith(stored?.draft.lineage_id);
    scope.stop();
  });
});
