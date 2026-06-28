/**
 * Document Converter saved-file batch specs.
 *
 * Domain purpose:
 *   Prove Filkonvertering can submit ordered Mina filer batches by Vault refs
 *   without exposing implementation identifiers or browser-uploading bytes.
 *
 * Relationships:
 *   - Exercises `DocumentConverterView.vue` through teacher-visible controls.
 *   - Mocks the Document Converter file API boundary.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentConverterView from "./DocumentConverterView.vue";

const previewApiMocks = vi.hoisted(() => ({
  discardDocumentConverterProjectPreview: vi.fn(),
  downloadDocumentConverterProjectPreviewArtifact: vi.fn(),
  loadDocumentConverterProjectPreviewArtifactBlob: vi.fn(),
  renderDocumentConverterProjectPreview: vi.fn(),
  saveDocumentConverterProjectPreviewArtifact: vi.fn(),
}));

const fileApiMocks = vi.hoisted(() => ({
  downloadDocumentConverterJobArtifact: vi.fn(),
  getDocumentConverterJobStatus: vi.fn(),
  listDocumentConverterSavedFiles: vi.fn(),
  listDocumentConverterSingleFileRoutes: vi.fn(),
  saveDocumentConverterJobArtifact: vi.fn(),
  submitDocumentConverterSavedFileJob: vi.fn(),
  submitDocumentConverterUploadJob: vi.fn(),
}));

vi.mock("./documentConverterProjectPreviewApi", () => ({
  discardDocumentConverterProjectPreview: previewApiMocks.discardDocumentConverterProjectPreview,
  downloadDocumentConverterProjectPreviewArtifact:
    previewApiMocks.downloadDocumentConverterProjectPreviewArtifact,
  loadDocumentConverterProjectPreviewArtifactBlob:
    previewApiMocks.loadDocumentConverterProjectPreviewArtifactBlob,
  renderDocumentConverterProjectPreview: previewApiMocks.renderDocumentConverterProjectPreview,
  saveDocumentConverterProjectPreviewArtifact:
    previewApiMocks.saveDocumentConverterProjectPreviewArtifact,
}));

vi.mock("./documentConverterFileApi", () => ({
  downloadDocumentConverterJobArtifact: fileApiMocks.downloadDocumentConverterJobArtifact,
  getDocumentConverterJobStatus: fileApiMocks.getDocumentConverterJobStatus,
  listDocumentConverterSavedFiles: fileApiMocks.listDocumentConverterSavedFiles,
  listDocumentConverterSingleFileRoutes: fileApiMocks.listDocumentConverterSingleFileRoutes,
  saveDocumentConverterJobArtifact: fileApiMocks.saveDocumentConverterJobArtifact,
  submitDocumentConverterSavedFileJob: fileApiMocks.submitDocumentConverterSavedFileJob,
  submitDocumentConverterUploadJob: fileApiMocks.submitDocumentConverterUploadJob,
}));

describe("DocumentConverterView saved-file batches", () => {
  beforeEach(() => {
    fileApiMocks.listDocumentConverterSavedFiles.mockResolvedValue({
      files: [
        {
          bytes: 128,
          created_at: "2026-06-28T08:00:00Z",
          file_id: "11111111-1111-1111-1111-111111111111",
          name: "forsta.html",
          ref: "vault:11111111-1111-1111-1111-111111111111",
          source_format: "html",
        },
        {
          bytes: 128,
          created_at: "2026-06-28T08:01:00Z",
          file_id: "22222222-2222-2222-2222-222222222222",
          name: "andra.html",
          ref: "vault:22222222-2222-2222-2222-222222222222",
          source_format: "html",
        },
      ],
    });
    fileApiMocks.listDocumentConverterSingleFileRoutes.mockResolvedValue({
      routes: [{ output_format: "pdf", source_format: "html", title: "HTML -> PDF" }],
    });
    fileApiMocks.submitDocumentConverterSavedFileJob.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "andra.html",
          job_id: "job-andra",
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "succeeded",
        },
        {
          error: null,
          input_filename: "forsta.html",
          job_id: "job-forsta",
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "succeeded",
        },
      ],
    });
    fileApiMocks.getDocumentConverterJobStatus
      .mockResolvedValueOnce({
        error: null,
        job_id: "job-andra",
        result_artifact: {
          content_type: "application/pdf",
          filename: "andra.pdf",
          size_bytes: 128,
          source_artifact_id: "document-converter:job-andra:converted_document",
        },
        status: "succeeded",
      })
      .mockResolvedValueOnce({
        error: null,
        job_id: "job-forsta",
        result_artifact: {
          content_type: "application/pdf",
          filename: "forsta.pdf",
          size_bytes: 128,
          source_artifact_id: "document-converter:job-forsta:converted_document",
        },
        status: "succeeded",
      });
    fileApiMocks.downloadDocumentConverterJobArtifact.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "andra.pdf",
    });
  });

  it("submits selected Mina filer refs in the visible order", async () => {
    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await wrapper.get('[data-test="document-converter-origin-saved"]').trigger("click");
    await flushPromises();

    const select = wrapper.get<HTMLSelectElement>(
      '[data-testid="document-converter-saved-file-select"]',
    );
    await select.setValue("vault:11111111-1111-1111-1111-111111111111");
    await select.setValue("vault:22222222-2222-2222-2222-222222222222");

    expect(wrapper.text()).toContain("1. forsta.html");
    expect(wrapper.text()).toContain("2. andra.html");
    expect(wrapper.text()).not.toContain("vault:");

    await wrapper.get('[data-testid="document-converter-source-move-up-1"]').trigger("click");
    expect(wrapper.text()).toContain("1. andra.html");
    expect(wrapper.text()).toContain("2. forsta.html");

    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();

    expect(fileApiMocks.submitDocumentConverterSavedFileJob).toHaveBeenCalledWith({
      outputFormat: "pdf",
      sourceFormat: "html",
      sourceRefs: [
        "vault:22222222-2222-2222-2222-222222222222",
        "vault:11111111-1111-1111-1111-111111111111",
      ],
    });
    expect(wrapper.text()).toContain("andra.pdf");
    expect(wrapper.text()).toContain("forsta.pdf");
  });

  it("removes selected Mina filer entries before submission", async () => {
    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await wrapper.get('[data-test="document-converter-origin-saved"]').trigger("click");
    await flushPromises();

    const select = wrapper.get<HTMLSelectElement>(
      '[data-testid="document-converter-saved-file-select"]',
    );
    await select.setValue("vault:11111111-1111-1111-1111-111111111111");
    await select.setValue("vault:22222222-2222-2222-2222-222222222222");
    await wrapper.get('[data-testid="document-converter-source-remove-1"]').trigger("click");

    expect(wrapper.text()).toContain("1. forsta.html");
    expect(wrapper.text()).not.toContain("2. andra.html");
  });
});
