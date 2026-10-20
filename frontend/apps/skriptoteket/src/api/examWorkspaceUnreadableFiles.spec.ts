/**
 * Unreadable saved exams transport (TASK-SKRIPT-41-02-06, U4).
 *
 * Expected behavior:
 *   The list reads the unreadable-documents route; the download fetches the
 *   stored Mina filer file unchanged through the vault download path; the
 *   remove posts once to the vault delete path.
 */

import { describe, expect, it, vi } from "vitest";

import { apiFetchBlobResponse, apiGet, apiPost } from "./client";
import {
  downloadSavedExamFile,
  listUnreadableExamWorkspaceDocuments,
  removeSavedExamFile,
} from "./examWorkspaceUnreadableFiles";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);
const apiFetchBlobResponseMock = vi.mocked(apiFetchBlobResponse);

const UNREADABLE_DOCUMENTS_PATH =
  "/api/v1/apps/documents.conversion_hub/exam-workspace/unreadable-documents";

describe("examWorkspaceUnreadableFiles transport", () => {
  it("lists unreadable documents from the unreadable-documents route", async () => {
    apiGetMock.mockResolvedValueOnce({ documents: [] });

    const result = await listUnreadableExamWorkspaceDocuments();

    expect(apiGetMock).toHaveBeenCalledTimes(1);
    expect(apiGetMock).toHaveBeenCalledWith(UNREADABLE_DOCUMENTS_PATH);
    expect(result).toEqual({ documents: [] });
  });

  it("downloads the stored file unchanged through the vault download path", async () => {
    const blob = new Blob(["provdokument"]);
    apiFetchBlobResponseMock.mockResolvedValueOnce({
      blob,
      contentType: "application/zip",
      filename: "Prov.provdokument.zip",
    });

    const result = await downloadSavedExamFile("file/1");

    expect(apiFetchBlobResponseMock).toHaveBeenCalledTimes(1);
    expect(apiFetchBlobResponseMock).toHaveBeenCalledWith("/api/v1/vault/files/file%2F1/download");
    expect(result.blob).toBe(blob);
  });

  it("removes the stored file with one POST to the vault delete path", async () => {
    apiPostMock.mockResolvedValueOnce({
      file: { id: "file-1", name: "Prov.provdokument.zip" },
    });

    const result = await removeSavedExamFile("file/1");

    expect(apiPostMock).toHaveBeenCalledTimes(1);
    expect(apiPostMock).toHaveBeenCalledWith("/api/v1/vault/files/file%2F1/delete");
    expect(result).toEqual({ id: "file-1", name: "Prov.provdokument.zip" });
  });
});
