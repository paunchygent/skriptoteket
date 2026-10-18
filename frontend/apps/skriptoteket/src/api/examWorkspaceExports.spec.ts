/**
 * Exam workspace export transport behavior.
 *
 * Expected behavior:
 *   The thin typed client calls the export endpoints with the exact paths the
 *   backend contract defines: a blob download per target, a checklist for the
 *   exported revision, and a stored export. A download response without a
 *   Content-Disposition file name is a fault.
 */

import { describe, expect, it, vi } from "vitest";

import { apiFetchBlobResponse, apiGet } from "./client";
import {
  downloadExamWorkspaceExport,
  getExamWorkspaceExportChecklist,
} from "./examWorkspaceExports";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}));

const apiGetMock = vi.mocked(apiGet);
const apiFetchBlobResponseMock = vi.mocked(apiFetchBlobResponse);

const DOCUMENTS_ROOT = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents";

describe("examWorkspaceExports transport", () => {
  it("downloads each export target as a blob from the export path", async () => {
    const blobResponse = {
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "prov-qti.zip",
    };
    apiFetchBlobResponseMock.mockResolvedValueOnce(blobResponse);

    const result = await downloadExamWorkspaceExport("lineage-1", "qti", 2);

    expect(apiFetchBlobResponseMock).toHaveBeenCalledWith(
      `${DOCUMENTS_ROOT}/lineage-1/exports/qti?expected_revision=2`,
    );
    expect(result).toEqual(blobResponse);
  });

  it("treats an export response without a Content-Disposition file name as a fault", async () => {
    apiFetchBlobResponseMock.mockResolvedValueOnce({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: null,
    });

    await expect(downloadExamWorkspaceExport("lineage-1", "qti", 2)).rejects.toThrow(
      "Content-Disposition",
    );
  });

  it("requests only the checklist for the exported revision", async () => {
    const response = { entries: [] };
    apiGetMock.mockResolvedValueOnce(response);

    const result = await getExamWorkspaceExportChecklist("lineage-1", 2);

    expect(apiGetMock).toHaveBeenCalledWith(
      `${DOCUMENTS_ROOT}/lineage-1/export-checklist?expected_revision=2`,
    );
    expect(result).toBe(response);
  });
});
