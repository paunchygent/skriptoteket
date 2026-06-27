/**
 * Document Converter single-file API client specs.
 *
 * Domain purpose:
 *   Prove the route-level single-file workflow talks to the scoped backend
 *   endpoints for local uploads, owner-filtered saved files, and server-owned
 *   result actions.
 *
 * Relationships:
 *   - Exercises `documentConverterFileApi.ts` only.
 *   - Mocks the protected API client boundary.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../api/openapi";
import {
  downloadDocumentConverterJobArtifact,
  listDocumentConverterSavedFiles,
  submitDocumentConverterSavedFileJob,
  submitDocumentConverterUploadJob,
} from "./documentConverterFileApi";

const apiMocks = vi.hoisted(() => ({
  apiFetchBlobResponse: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock("../../../api/client", () => ({
  apiFetchBlobResponse: apiMocks.apiFetchBlobResponse,
  apiGet: apiMocks.apiGet,
  apiPost: apiMocks.apiPost,
}));

type DocumentConverterSavedFileOption =
  components["schemas"]["DocumentConverterSavedFileOption"];

function savedFile(params?: Partial<DocumentConverterSavedFileOption>): DocumentConverterSavedFileOption {
  return {
    bytes: 128,
    created_at: "2026-06-26T08:00:00Z",
    file_id: params?.file_id ?? "vault-file-1",
    name: params?.name ?? "lektion.html",
    ref: params?.ref ?? "vault:11111111-1111-1111-1111-111111111111",
    source_format: params?.source_format ?? "html",
  };
}

describe("documentConverterFileApi", () => {
  beforeEach(() => {
    apiMocks.apiFetchBlobResponse.mockReset();
    apiMocks.apiGet.mockReset();
    apiMocks.apiPost.mockReset();
  });

  it("loads only backend-filtered saved-file sources", async () => {
    apiMocks.apiGet.mockResolvedValue({
      files: [savedFile()],
    });

    const result = await listDocumentConverterSavedFiles();

    expect(apiMocks.apiGet).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/saved-files",
    );
    expect(result.files?.[0]?.name).toBe("lektion.html");
  });

  it("submits a saved-file job with a source ref instead of upload bytes", async () => {
    apiMocks.apiPost.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "lektion.html",
          job_id: "job-1",
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "succeeded",
        },
      ],
    });

    await submitDocumentConverterSavedFileJob({
      outputFormat: "pdf",
      sourceFormat: "html",
      sourceRef: "vault:11111111-1111-1111-1111-111111111111",
    });

    expect(apiMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/saved-files/jobs",
      expect.objectContaining({
        source_ref: "vault:11111111-1111-1111-1111-111111111111",
      }),
    );
  });

  it("submits a local upload as multipart form data and downloads result blobs from the job route", async () => {
    const file = new File(["<h1>Hej</h1>"], "lektion.html", { type: "text/html" });
    apiMocks.apiPost.mockResolvedValue({
      jobs: [],
    });
    apiMocks.apiFetchBlobResponse.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "lektion.pdf",
    });

    await submitDocumentConverterUploadJob({
      files: [file],
      outputFormat: "pdf",
      sourceFormat: "html",
    });
    await downloadDocumentConverterJobArtifact({ jobId: "job-1" });

    expect(apiMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/jobs",
      expect.any(FormData),
    );
    expect(apiMocks.apiFetchBlobResponse).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/jobs/job-1/artifact",
      { method: "GET" },
    );
  });
});
