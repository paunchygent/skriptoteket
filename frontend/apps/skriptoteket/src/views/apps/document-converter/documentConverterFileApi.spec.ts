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
  saveDocumentConverterJobArtifact,
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

  it("submits a saved-file job with ordered source refs instead of upload bytes", async () => {
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
      sourceRefs: [
        "vault:22222222-2222-2222-2222-222222222222",
        "vault:11111111-1111-1111-1111-111111111111",
      ],
    });

    expect(apiMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/saved-files/jobs",
      expect.objectContaining({
        source_refs: [
          "vault:22222222-2222-2222-2222-222222222222",
          "vault:11111111-1111-1111-1111-111111111111",
        ],
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

  it("sends edited filename stem intent to protected download and save endpoints", async () => {
    apiMocks.apiFetchBlobResponse.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "Backendens namn.pdf",
    });
    apiMocks.apiPost.mockResolvedValue({
      source_artifact_id: "document-converter:sir-job-1:converted_document",
      vault_artifact: {
        bytes: 12,
        created_at: "2026-06-27T09:00:00Z",
        file_id: "file-1",
        name: "Backendens namn.pdf",
      },
    });

    const download = await downloadDocumentConverterJobArtifact({
      filenameStem: "Lärarens förslag.pdf",
      jobId: "job-1",
    });
    const saved = await saveDocumentConverterJobArtifact({
      filenameStem: "Lärarens förslag.pdf",
      jobId: "job-1",
    });

    expect(apiMocks.apiFetchBlobResponse).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/jobs/job-1/artifact?filename_stem=L%C3%A4rarens+f%C3%B6rslag.pdf",
      { method: "GET" },
    );
    expect(apiMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/documents.conversion_hub/document-converter/jobs/job-1/artifact/save?filename_stem=L%C3%A4rarens+f%C3%B6rslag.pdf",
    );
    expect(download.filename).toBe("Backendens namn.pdf");
    expect(saved.vault_artifact.name).toBe("Backendens namn.pdf");
  });
});
