/**
 * Guest exam workspace store: exports, limits and asset URLs.
 *
 * Expected behavior:
 *   An export sends the saved copy and exactly its declared picture bytes;
 *   the checklist answers only for the saved revision; the public routes'
 *   429 limit error is recognized by status and reported once per failing
 *   call; the open draft's stored pictures map to object URLs and clear with
 *   the draft.
 */

import { describe, expect, it } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceExportChecklistResponse } from "../../../api/examWorkspaceExports";
import { isGuestLimitError } from "./examWorkspaceGuestStore";
import { newGuestDraft } from "./examWorkspaceGuestDraft";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import {
  DOCUMENT_ID,
  createIds,
  exam,
  installGuestStoreObjectUrls,
  pictureExam,
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

describe("examWorkspaceGuestStore exports and limits", () => {
  it("calls onLimit exactly once per failing call and still rejects with the same 429", async () => {
    const context = await startBlankSetup();
    const opened = await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);
    const limit = new ApiError({
      code: "TOO_MANY_REQUESTS",
      details: { bucket: "guest_edit", reason: "caller_limit" },
      message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
      status: 429,
    });
    context.mocks.createParent.mockRejectedValueOnce(limit);

    const error = await context.store.store.shared
      .createExamWorkspaceParent(DOCUMENT_ID, {
        child: newTeacherItem("item_002", 2, "free_text"),
        expected_cursor: opened.history_cursor,
        instruction: [],
        position: 0,
      })
      .catch((caught: unknown) => caught);

    expect(error).toBe(limit);
    expect(context.onLimit).toHaveBeenCalledTimes(1);
  });

  it("exports the saved copy and exactly its declared picture bytes", async () => {
    const context = setupGuestStore();
    const png = new Blob(["png-bytes"], { type: "image/png" });
    const unused = new Blob(["unused"], { type: "image/png" });
    const saved = pictureExam("Sparad");
    const seeded = newGuestDraft(saved, createIds(), []);
    expect(await context.storage.replaceIf(null, { assets: { asset_001: png, unused }, draft: seeded })).toBe(
      true,
    );

    // The editor's working copy drops the picture; the saved copy still declares it.
    const step = await context.store.store.shared.storeExamWorkspaceUndoStep(DOCUMENT_ID, {
      afterStepId: null,
      document: exam("Utkast"),
      expectedCursor: seeded.cursor,
    });
    expect(step.document.title).toBe("Utkast");

    context.mocks.exportDownload.mockResolvedValueOnce({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "prov.zip",
    });
    const result = await context.store.store.shared.downloadExamWorkspaceExport(
      DOCUMENT_ID,
      "qti",
      1,
    );

    const [target, request] = context.mocks.exportDownload.mock.calls[0]!;
    expect(target).toBe("qti");
    expect(request.document).toEqual(saved);
    expect(request.document.title).toBe("Sparad");
    expect(Object.keys(request.assets)).toEqual(["asset_001"]);
    expect(request.assets["asset_001"]).toBe(png);
    expect(result.filename).toBe("prov.zip");

    context.mocks.exportDownload.mockClear();
    const stale = await context.store.store.shared
      .downloadExamWorkspaceExport(DOCUMENT_ID, "qti", 99)
      .catch((caught: unknown) => caught);
    expect(stale).toBeInstanceOf(ApiError);
    expect(stale).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(context.mocks.exportDownload).not.toHaveBeenCalled();
  });

  it("returns the checklist only for the saved revision", async () => {
    const context = await startBlankSetup();
    const checklist: ExamWorkspaceExportChecklistResponse = {
      entries: [],
      inline_choice_min_options: 2,
    };
    context.mocks.exportChecklist.mockResolvedValueOnce(checklist);

    expect(
      await context.store.store.shared.getExamWorkspaceExportChecklist(DOCUMENT_ID, 1),
    ).toBe(checklist);

    const stale = await context.store.store.shared
      .getExamWorkspaceExportChecklist(DOCUMENT_ID, 2)
      .catch((caught: unknown) => caught);
    expect(stale).toBeInstanceOf(ApiError);
    expect(stale).toMatchObject({ status: 409 });
    expect(context.mocks.exportChecklist).toHaveBeenCalledTimes(1);
  });

  it("propagates a public 429 unchanged and recognizes only the limit status", async () => {
    const context = await startBlankSetup();
    const limit = new ApiError({
      code: "TOO_MANY_REQUESTS",
      details: { bucket: "guest_edit", reason: "caller_limit" },
      message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
      status: 429,
    });
    context.mocks.misspellings.mockRejectedValue(limit);

    const error = await context.store.store.shared
      .requestExamWorkspaceAnswerMisspellings({
        accepted_values: ["Göteborg"],
        document_text: "Göteborg",
        other_gold_answers: [],
      })
      .catch((caught: unknown) => caught);

    expect(error).toBe(limit);
    expect(isGuestLimitError(error)).toBe(true);
    expect(
      isGuestLimitError(new ApiError({ code: "VALIDATION_ERROR", message: "x", status: 422 })),
    ).toBe(false);
    expect(isGuestLimitError(new Error("429"))).toBe(false);
  });

  it("maps the open draft's stored pictures to object URLs and clears them", async () => {
    const context = setupGuestStore();
    const png = new Blob(["png-bytes"], { type: "image/png" });
    const draft = newGuestDraft(pictureExam(), createIds(), []);
    expect(await context.storage.replaceIf(null, { assets: { asset_001: png }, draft })).toBe(true);

    await context.store.store.shared.getExamWorkspaceDocument(DOCUMENT_ID);

    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "asset_001")).toBe(
      "blob:picture",
    );
    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "missing")).toBe("");
    expect(context.store.store.shared.examWorkspaceAssetUrl("other", "asset_001")).toBe("");

    await context.store.clear();

    expect(context.store.store.shared.examWorkspaceAssetUrl(DOCUMENT_ID, "asset_001")).toBe("");
    expect(await context.storage.load()).toBeNull();
  });
});
