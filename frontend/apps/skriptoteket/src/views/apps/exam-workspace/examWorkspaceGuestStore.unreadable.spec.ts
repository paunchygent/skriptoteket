/**
 * Guest exam workspace store: an unreadable stored draft is refused (U14, repairs F1).
 *
 * Expected behavior:
 *   `getExamWorkspaceDocument` refuses a stored draft the browser cannot
 *   read with the server's outdated-format refusal, before returning any
 *   editable document. A current draft still opens, and one older document
 *   among current ones still refuses. The stored record stays untouched by
 *   the refusal.
 */

import { beforeEach, describe, expect, it } from "vitest";

import type { StoredGuestDraft } from "./examWorkspaceGuestDraftStorage";
import { setupGuestStore, startBlank, type GuestStoreSetup } from "./examWorkspaceGuestStore.specSupport";

const CURRENT_TOKEN = '"native_exam_document_v11"';
const OLD_TOKEN = '"native_exam_document_v10"';

/**
 * Rewrite the seeded record's version tokens: every token for a fully old
 * draft, or only the first one (the baseline) for a mixed draft. The parsed
 * record keeps the draft's shape; only version strings change.
 */
async function seatVersions(setup: GuestStoreSetup, mode: "all" | "first"): Promise<string> {
  const lineageId = await startBlank(setup);
  const stored = await setup.storage.load();
  if (stored === null) {
    throw new Error("expected the blank start to seed a draft");
  }
  const serialized = JSON.stringify(stored);
  const downgraded: StoredGuestDraft = JSON.parse(
    mode === "all"
      ? serialized.replaceAll(CURRENT_TOKEN, OLD_TOKEN)
      : serialized.replace(CURRENT_TOKEN, OLD_TOKEN),
  );
  expect(await setup.storage.replaceIf(stored.draft.cursor, downgraded)).toBe(true);
  return lineageId;
}

describe("examWorkspaceGuestStore unreadable drafts", () => {
  let setup: GuestStoreSetup;

  beforeEach(() => {
    setup = setupGuestStore();
  });

  it("refuses a stored v10 draft with the outdated-format refusal", async () => {
    const lineageId = await seatVersions(setup, "all");

    await expect(setup.store.store.shared.getExamWorkspaceDocument(lineageId)).rejects.toMatchObject({
      code: "DOCUMENT_SCHEMA_OUTDATED",
      status: 422,
    });
  });

  it("keeps the stored record untouched by the refusal", async () => {
    const lineageId = await seatVersions(setup, "all");

    await expect(
      setup.store.store.shared.getExamWorkspaceDocument(lineageId),
    ).rejects.toMatchObject({ code: "DOCUMENT_SCHEMA_OUTDATED" });
    const stored = await setup.storage.load();
    expect(stored?.draft.lineage_id).toBe(lineageId);
    expect(stored?.draft.saved_document.schema_version).toBe("native_exam_document_v10");
  });

  it("still opens a current v11 draft", async () => {
    const lineageId = await startBlank(setup);

    const response = await setup.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(response.document.schema_version).toBe("native_exam_document_v11");
  });

  it("refuses a draft with one older document among current ones", async () => {
    const lineageId = await seatVersions(setup, "first");

    await expect(setup.store.store.shared.getExamWorkspaceDocument(lineageId)).rejects.toMatchObject({
      code: "DOCUMENT_SCHEMA_OUTDATED",
      status: 422,
    });
  });
});
