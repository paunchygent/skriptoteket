/**
 * Exam workspace guest draft browser storage.
 *
 * Expected behavior:
 *   One current draft round-trips through the port with its picture blobs.
 *   `replaceIf` stores only when the stored cursor still equals the expected
 *   one (or when nothing is stored and the expectation is null), so a second
 *   tab's write reports false instead of silently overwriting the winner.
 *   `clearIf` deletes only the snapshot it names, so a newer draft survives.
 *   The factory uses an injected port instead of opening IndexedDB.
 */

import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  newGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  createExamWorkspaceGuestDraftStorage,
  createIndexedDbGuestEditLeaseStorage,
  createInMemoryExamWorkspaceGuestDraftStorage,
  EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME,
  EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION,
  EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY,
  EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME,
  EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY,
  EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME,
  type ExamWorkspaceGuestDraftStoragePort,
  type StoredGuestDraft,
} from "./examWorkspaceGuestDraftStorage";

const NOW = "2026-10-18T10:00:00.000Z";

/** Any current-schema document; scenarios override only the title. */
function exam(title = "Original"): NativeExamDocument {
  return { ...buildParentDocument(), title };
}

function createIds(): ExamWorkspaceGuestDraftIdSource {
  let counter = 0;
  return {
    now: () => NOW,
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

function storedDraft(title = "Original"): StoredGuestDraft {
  const png = new Blob(["png-bytes"], { type: "image/png" });
  return {
    assets: { asset_001: png },
    draft: newGuestDraft(exam(title), createIds(), []),
  };
}

describe("examWorkspaceGuestDraftStorage", () => {
  it("names its own database, stores and single record keys", () => {
    expect(EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME).toBe("skriptoteket_exam_workspace_guest");
    expect(EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION).toBe(2);
    expect(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME).toBe("drafts");
    expect(EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY).toBe("current");
    expect(EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME).not.toBe("skriptoteket_curated_apps");
    expect(EXAM_WORKSPACE_GUEST_EDIT_LEASE_STORE_NAME).toBe("edit_lease");
    expect(EXAM_WORKSPACE_GUEST_EDIT_LEASE_RECORD_KEY).toBe("current");
  });

  it("creates the IndexedDB lease port without opening the database", () => {
    const storage = createIndexedDbGuestEditLeaseStorage();

    expect(typeof storage.load).toBe("function");
    expect(typeof storage.save).toBe("function");
  });

  it("round-trips the draft and its picture blobs through replaceIf on an empty slot", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const stored = storedDraft();

    expect(await storage.replaceIf(null, stored)).toBe(true);
    const loaded = await storage.load();

    expect(loaded).toEqual(stored);
    expect(loaded?.draft.cursor).toBe(stored.draft.cursor);
    expect(loaded?.assets["asset_001"]).toBe(stored.assets["asset_001"]);
    expect(loaded?.assets["asset_001"]?.size).toBe(9);
    expect(loaded?.assets["asset_001"]?.type).toBe("image/png");
  });

  it("refuses a replaceIf whose expected cursor no longer owns the slot", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const first = storedDraft("Första");
    const second = storedDraft("Andra");
    expect(await storage.replaceIf(null, first)).toBe(true);

    expect(await storage.replaceIf(null, second)).toBe(false);
    expect(await storage.replaceIf("99999999-9999-4999-8999-999999999999", second)).toBe(false);

    expect((await storage.load())?.draft.saved_document.title).toBe("Första");
  });

  it("replaces the stored draft only for the winning expected cursor", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const first = storedDraft("Första");
    expect(await storage.replaceIf(null, first)).toBe(true);

    const ids = createIds();
    const outcome = storeGuestUndoStep(
      first.draft,
      { afterStepId: null, document: exam("Andra"), expectedCursor: first.draft.cursor },
      ids,
    );
    if (outcome.kind !== "ok") {
      throw new Error(`expected a stored step, got ${outcome.kind}`);
    }
    const second: StoredGuestDraft = { assets: {}, draft: outcome.draft };

    expect(await storage.replaceIf(first.draft.cursor, second)).toBe(true);
    expect((await storage.load())?.draft.saved_document.title).toBe("Andra");
    expect((await storage.load())?.draft.cursor).toBe(outcome.draft.cursor);
  });

  it("clears only the snapshot clearIf names and keeps a newer draft", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const stored = storedDraft();
    expect(await storage.replaceIf(null, stored)).toBe(true);

    expect(await storage.clearIf("99999999-9999-4999-8999-999999999999")).toBe(false);
    expect(await storage.load()).toEqual(stored);

    expect(await storage.clearIf(stored.draft.cursor)).toBe(true);
    expect(await storage.load()).toBeNull();
  });

  it("keeps a newer draft when clearIf still names the old snapshot", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const old = storedDraft("Gammal");
    expect(await storage.replaceIf(null, old)).toBe(true);

    const ids = createIds();
    const outcome = storeGuestUndoStep(
      old.draft,
      { afterStepId: null, document: exam("Ny"), expectedCursor: old.draft.cursor },
      ids,
    );
    if (outcome.kind !== "ok") {
      throw new Error(`expected a stored step, got ${outcome.kind}`);
    }
    expect(await storage.replaceIf(old.draft.cursor, { assets: {}, draft: outcome.draft })).toBe(
      true,
    );

    expect(await storage.clearIf(old.draft.cursor)).toBe(false);
    expect((await storage.load())?.draft.cursor).toBe(outcome.draft.cursor);
  });

  it("stores a reactive draft document through the factory and loads plain equal content", async () => {
    const storage = createExamWorkspaceGuestDraftStorage({
      port: createInMemoryExamWorkspaceGuestDraftStorage(),
    });
    const edited = ref(exam("Reaktiv"));
    const draft = newGuestDraft(edited.value, createIds(), []);

    expect(await storage.replaceIf(null, { assets: {}, draft })).toBe(true);

    const loaded = await storage.load();
    expect(loaded?.draft.saved_document).toEqual(exam("Reaktiv"));
    expect(loaded?.draft.saved_document).not.toBe(edited.value);
    expect(loaded?.draft.saved_document.items).not.toBe(edited.value.items);
  });

  it("uses the injected port instead of opening IndexedDB", async () => {
    const port: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: vi.fn<ExamWorkspaceGuestDraftStoragePort["clearIf"]>(async () => true),
      load: vi.fn<ExamWorkspaceGuestDraftStoragePort["load"]>(async () => null),
      replaceIf: vi.fn<ExamWorkspaceGuestDraftStoragePort["replaceIf"]>(async () => true),
    };
    const storage = createExamWorkspaceGuestDraftStorage({ port });
    const stored = storedDraft();

    expect(await storage.replaceIf(null, stored)).toBe(true);
    expect(port.replaceIf).toHaveBeenCalledTimes(1);
    const [cursor, sent] = vi.mocked(port.replaceIf).mock.calls[0]!;
    expect(cursor).toBeNull();
    expect(sent).toEqual(stored);
    expect(sent).not.toBe(stored);
    expect(sent.draft).not.toBe(stored.draft);
    expect(sent.assets["asset_001"]).toBe(stored.assets["asset_001"]);
    expect(await storage.load()).toBeNull();
    expect(await storage.clearIf(stored.draft.cursor)).toBe(true);

    expect(storage).not.toBe(port);
    expect(port.clearIf).toHaveBeenCalledTimes(1);
  });
});
