/**
 * Exam workspace guest draft browser storage.
 *
 * Expected behavior:
 *   One current draft round-trips through the port with its picture blobs,
 *   a save replaces the earlier draft, clear removes it, and the factory uses
 *   an injected port instead of opening IndexedDB.
 */

import { describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  newGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  createExamWorkspaceGuestDraftStorage,
  createInMemoryExamWorkspaceGuestDraftStorage,
  EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME,
  EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION,
  EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY,
  EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME,
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
    draft: newGuestDraft(exam(title), createIds()),
  };
}

describe("examWorkspaceGuestDraftStorage", () => {
  it("names its own database, store and single record key", () => {
    expect(EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME).toBe("skriptoteket_exam_workspace_guest");
    expect(EXAM_WORKSPACE_GUEST_DRAFT_DB_VERSION).toBe(1);
    expect(EXAM_WORKSPACE_GUEST_DRAFT_STORE_NAME).toBe("drafts");
    expect(EXAM_WORKSPACE_GUEST_DRAFT_RECORD_KEY).toBe("current");
    expect(EXAM_WORKSPACE_GUEST_DRAFT_DB_NAME).not.toBe("skriptoteket_curated_apps");
  });

  it("round-trips the draft and its picture blobs through the in-memory store", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const stored = storedDraft();

    await storage.save(stored);
    const loaded = await storage.load();

    expect(loaded).toEqual(stored);
    expect(loaded?.draft.draft_id).toBe(stored.draft.draft_id);
    expect(loaded?.assets["asset_001"]).toBe(stored.assets["asset_001"]);
    expect(loaded?.assets["asset_001"]?.size).toBe(9);
    expect(loaded?.assets["asset_001"]?.type).toBe("image/png");
  });

  it("keeps only the latest saved draft", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    const first = storedDraft("Första");
    const second = storedDraft("Andra");

    await storage.save(first);
    await storage.save(second);

    expect((await storage.load())?.draft.saved_document.title).toBe("Andra");
  });

  it("clears the current draft", async () => {
    const storage = createInMemoryExamWorkspaceGuestDraftStorage();
    await storage.save(storedDraft());

    await storage.clear();

    expect(await storage.load()).toBeNull();
  });

  it("uses the injected port instead of opening IndexedDB", async () => {
    const port: ExamWorkspaceGuestDraftStoragePort = {
      clear: vi.fn(async () => {}),
      load: vi.fn(async () => null),
      save: vi.fn(async () => {}),
    };
    const storage = createExamWorkspaceGuestDraftStorage({ port });
    const stored = storedDraft();

    await storage.save(stored);
    expect(port.save).toHaveBeenCalledWith(stored);
    expect(await storage.load()).toBeNull();
    await storage.clear();

    expect(storage).toBe(port);
    expect(port.clear).toHaveBeenCalledTimes(1);
  });
});
