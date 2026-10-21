/**
 * Guest QTI start: a late parse never replaces the retained draft once the
 * import lost its authority (TASK-SKRIPT-40-04-21, rereview 3 F5).
 *
 * Expected behavior:
 *   Tab A imports a QTI package over its retained draft C and the public
 *   parse response waits. When another tab B holds a live edit lease by the
 *   time the parse completes, or A's import was retired meanwhile, the late
 *   result never reaches the slot: C, its history and its picture bytes
 *   stay, and B, which loaded C but has stored nothing yet, stores its first
 *   edit against the unchanged cursor. An import that keeps its authority
 *   still replaces the slot.
 *
 *   The spec runs the real guest store over the in-memory draft and lease
 *   adapters, which share one lease slot like the browser database; only the
 *   public parse route is a double.
 */

import { describe, expect, it } from "vitest";

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
} from "./examWorkspaceGuestStore.specSupport";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

installGuestStoreObjectUrls();

const TAB_A = LEASE_TAB_ID;
const TAB_B = "20000000-0000-4000-8000-00000000000b";

function zipFile(): File {
  return new File(["qti"], "Nytt_prov.zip", { type: "application/zip" });
}

function parsed(): PublicExamWorkspaceQtiImportResult {
  return { assets: {}, document: exam("Imported"), notes: [] };
}

describe("guest QTI start after the import lost its authority", () => {
  it("keeps the retained draft when tab B holds the lease by the time the parse completes", async () => {
    const context = setupGuestStore();
    const { lineageId } = await seedRetainedPictureDraft(context, TAB_A);
    const parse = deferred<PublicExamWorkspaceQtiImportResult>();
    context.mocks.importQti.mockReturnValueOnce(parse.promise);

    const importing = context.store.startFromQti(zipFile(), null, {
      isLive: () => true,
      tabId: TAB_A,
    });
    // A's heartbeat stalled past the lease lifetime: B claims the lease
    // without A answering, and loads C without storing anything yet.
    const claimed = await context.leaseStorage.claim(TAB_B, Date.now() + GUEST_EDIT_LEASE_TTL_MS + 1);
    expect(claimed.held).toBe(true);
    const tabB = openSecondTab(context);
    const loadedByB = await tabB.store.shared.getExamWorkspaceDocument(lineageId);

    parse.resolve(parsed());
    await expect(importing).rejects.toMatchObject({ code: "EDIT_LEASE_HELD" });

    await expectRetainedAndNewOwnerStores(context, { store: tabB, tabId: TAB_B }, lineageId, loadedByB);
  });

  it("keeps the retained draft when A's import is retired before the parse completes", async () => {
    const context = setupGuestStore();
    const { lineageId } = await seedRetainedPictureDraft(context, TAB_A);
    const parse = deferred<PublicExamWorkspaceQtiImportResult>();
    context.mocks.importQti.mockReturnValueOnce(parse.promise);
    let live = true;

    const importing = context.store.startFromQti(zipFile(), null, {
      isLive: () => live,
      tabId: TAB_A,
    });
    // A's workspace is disposed while A still holds a live lease, so only the
    // import's own authority can refuse; B loads C meanwhile.
    live = false;
    const tabB = openSecondTab(context);
    const loadedByB = await tabB.store.shared.getExamWorkspaceDocument(lineageId);

    parse.resolve(parsed());
    await expect(importing).rejects.toMatchObject({ code: "CONFLICT" });

    await context.leaseStorage.release(TAB_A);
    await context.leaseStorage.claim(TAB_B, Date.now());
    await expectRetainedAndNewOwnerStores(context, { store: tabB, tabId: TAB_B }, lineageId, loadedByB);
  });

  it("still replaces the slot when the import keeps its authority and lease", async () => {
    const context = setupGuestStore();
    await seedRetainedPictureDraft(context, TAB_A);
    context.mocks.importQti.mockResolvedValueOnce(parsed());

    const lineageId = await context.store.startFromQti(zipFile(), null, {
      isLive: () => true,
      tabId: TAB_A,
    });

    const stored = await context.storage.load();
    expect(stored?.draft.lineage_id).toBe(lineageId);
    expect(stored?.draft.saved_document.title).toBe("Imported");
    expect(stored?.assets).toEqual({});
  });
});
