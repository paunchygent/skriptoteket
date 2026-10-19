/**
 * Guest exam workspace store: QTI start.
 *
 * Expected behavior:
 *   `startFromQti` parses through the public route and stores the document
 *   as the draft with the response's picture bytes beside it, opening the
 *   same workspace editor as a blank start. A concurrent tab's newer draft
 *   is kept like a lost blank start, and a limit hit reports through
 *   `onLimit` while the error still reaches the caller.
 */

import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import { createGuestExamWorkspaceStore } from "./examWorkspaceGuestStore";
import type { ExamWorkspaceGuestDraftStoragePort } from "./examWorkspaceGuestDraftStorage";
import {
  exam,
  installGuestStoreObjectUrls,
  pictureExam,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";

installGuestStoreObjectUrls();

function zipFile(): File {
  return new File(["qti"], "Prov_HT25.zip", { type: "application/zip" });
}

function pngBlob(): Blob {
  return new Blob(["png-bytes"], { type: "image/png" });
}

describe("examWorkspaceGuestStore QTI start", () => {
  it("stores the parsed document as the draft with the response's picture bytes", async () => {
    const context = setupGuestStore();
    const document = pictureExam("QTI-prov");
    const png = pngBlob();
    context.mocks.importQti.mockResolvedValue({ assets: { asset_001: png }, document, notes: [] });

    const lineageId = await context.store.startFromQti(zipFile(), null);

    expect(context.mocks.importQti).toHaveBeenCalledTimes(1);
    const [file, courseKey] = context.mocks.importQti.mock.calls[0]!;
    expect(file.name).toBe("Prov_HT25.zip");
    expect(courseKey).toBeNull();
    expect(lineageId).toBe(document.document_id);
    const stored = await context.storage.load();
    expect(stored?.draft.saved_document).toEqual(document);
    expect(stored?.assets["asset_001"]).toBe(png);
    expect(stored?.assets["asset_001"]?.size).toBe(png.size);
    expect(stored?.assets["asset_001"]?.type).toBe("image/png");
    expect(context.store.store.shared.examWorkspaceAssetUrl(lineageId, "asset_001")).toBe(
      "blob:picture",
    );
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(opened.document.title).toBe("QTI-prov");
  });

  it("passes the chosen course key to the public route", async () => {
    const context = setupGuestStore();
    const document = exam("QTI-prov");
    context.mocks.importQti.mockResolvedValue({ assets: {}, document, notes: [] });

    await context.store.startFromQti(zipFile(), "SVESVE02");

    expect(context.mocks.importQti).toHaveBeenCalledWith(expect.any(File), "SVESVE02");
  });

  it("keeps the QTI import notes on the draft and returns them on open", async () => {
    const context = setupGuestStore();
    const document = exam("QTI-prov");
    context.mocks.importQti.mockResolvedValue({
      assets: {},
      document,
      notes: ["Fråga 3 hoppades över."],
    });

    const lineageId = await context.store.startFromQti(zipFile(), null);

    const stored = await context.storage.load();
    expect(stored?.draft.notes).toEqual(["Fråga 3 hoppades över."]);
    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(opened.notes).toEqual(["Fråga 3 hoppades över."]);
  });

  it("opens a blank start without notes", async () => {
    const context = setupGuestStore();

    const lineageId = await startBlank(context);

    const opened = await context.store.store.shared.getExamWorkspaceDocument(lineageId);
    expect(opened.notes).toEqual([]);
  });

  it("reports the conflict and keeps the newer draft when a concurrent tab wins the slot", async () => {
    const context = setupGuestStore();
    context.mocks.importQti.mockResolvedValue({
      assets: {},
      document: exam("Förlorare"),
      notes: [],
    });
    const losing: ExamWorkspaceGuestDraftStoragePort = {
      clearIf: (expected) => context.storage.clearIf(expected),
      load: () => context.storage.load(),
      replaceIf: vi.fn(async () => false),
    };
    const loser = createGuestExamWorkspaceStore({
      api: context.api,
      ids: context.ids,
      onLimit: context.onLimit,
      storage: losing,
    });

    const error = await loser.startFromQti(zipFile(), null).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "CONFLICT", status: 409 });
    expect(losing.replaceIf).toHaveBeenCalledTimes(1);
    expect(await context.storage.load()).toBeNull();
  });

  it("reports the limit once and stores nothing when the public route refuses", async () => {
    const context = setupGuestStore();
    context.mocks.importQti.mockRejectedValue(
      new ApiError({
        code: "TOO_MANY_REQUESTS",
        message: "Gränsen för gäster är nådd. Logga in för att fortsätta.",
        status: 429,
      }),
    );

    const error = await context.store
      .startFromQti(zipFile(), null)
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 429 });
    expect(context.onLimit).toHaveBeenCalledTimes(1);
    expect(await context.storage.load()).toBeNull();
  });
});
