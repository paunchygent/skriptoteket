/**
 * Document Converter single-file route workflow specs.
 *
 * Domain purpose:
 *   Prove the route exposes owner-scoped file conversion controls and
 *   teacher-facing current-result state alongside the HTML/CSS preview lane.
 *
 * Relationships:
 *   - Exercises `DocumentConverterView.vue` through user-visible controls.
 *   - Mocks the project-preview and single-file API boundaries.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

describe("DocumentConverterView single-file surface", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fileApiMocks.listDocumentConverterSavedFiles.mockResolvedValue({ files: [] });
    fileApiMocks.listDocumentConverterSingleFileRoutes.mockResolvedValue({
      routes: [
        {
          output_format: "pdf",
          source_format: "html",
          title: "HTML -> PDF",
        },
      ],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows file conversion as a tabbed mode without visible history or raw ids", async () => {
    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();
    const text = wrapper.text();

    expect(wrapper.get('[role="tablist"]').attributes("aria-label")).toBe("Välj arbetsyta");
    expect(text).toContain("Filkonvertering");
    expect(text).toContain("HTML/CSS-projekt");
    expect(text).toContain("Lokal fil");
    expect(text).toContain("Mina filer");
    expect(text).toContain("Källformat");
    expect(text).toContain("Exportformat");
    expect(text).toContain("HTML till PDF");
    expect(text).toContain("Välj en fil som du vill konvertera");
    expect(text).not.toContain("HTML -> PDF");
    expect(text).not.toContain("En fil");
    expect(text).not.toContain("Arbetssätt");
    expect(text).not.toContain("Aktuell källa");
    expect(text).not.toContain("Historik");
    expect(text).not.toContain("Inget resultat än");
    expect(text).not.toContain("preview-");
    expect(text).not.toContain("artifact-");
  });

  it("submits local upload batches in the source-panel order", async () => {
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
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
          artifact_id: "artifact-andra",
          content_type: "application/pdf",
          download_url: null,
          filename: "andra.pdf",
          kind: "converted_document",
          size_bytes: 128,
          source_entry_id: null,
        },
        status: "succeeded",
      })
      .mockResolvedValueOnce({
        error: null,
        job_id: "job-forsta",
        result_artifact: {
          artifact_id: "artifact-forsta",
          content_type: "application/pdf",
          download_url: null,
          filename: "forsta.pdf",
          kind: "converted_document",
          size_bytes: 128,
          source_entry_id: null,
        },
        status: "succeeded",
      });
    fileApiMocks.downloadDocumentConverterJobArtifact.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "andra.pdf",
    });

    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
    const firstFile = new File(["<h1>Första</h1>"], "forsta.html", { type: "text/html" });
    const secondFile = new File(["<h1>Andra</h1>"], "andra.html", { type: "text/html" });
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [firstFile, secondFile],
    });
    await input.trigger("change");
    await wrapper.get('[data-testid="document-converter-source-move-down-0"]').trigger("click");

    expect(wrapper.text()).toContain("1. andra.html");
    expect(wrapper.text()).toContain("2. forsta.html");

    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();

    expect(fileApiMocks.submitDocumentConverterUploadJob).toHaveBeenCalledWith({
      files: [secondFile, firstFile],
      outputFormat: "pdf",
      sourceFormat: "html",
    });
    expect(wrapper.text()).toContain("andra.pdf");
    expect(wrapper.text()).toContain("forsta.pdf");
  });

  it("keeps long-running single-file jobs pending instead of writing a failed history entry", async () => {
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "lektion.html",
          job_id: "job-long",
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "queued",
        },
      ],
    });
    fileApiMocks.getDocumentConverterJobStatus.mockResolvedValue({
      error: null,
      job_id: "job-long",
      result_artifact: null,
      status: "running",
    });

    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [new File(["<h1>Hej</h1>"], "lektion.html", { type: "text/html" })],
    });
    await input.trigger("change");

    const submitPromise = wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();
    await vi.advanceTimersByTimeAsync(20_000);
    await submitPromise;
    await flushPromises();

    expect(fileApiMocks.getDocumentConverterJobStatus).toHaveBeenCalledTimes(20);
    expect(wrapper.text()).toContain("Arbetar med filen...");
    expect(wrapper.text()).not.toContain("Misslyckades");
    expect(wrapper.text()).not.toContain("Konverteringen kunde inte slutföras.");
    expect(wrapper.text()).not.toContain("Historik");
    expect(wrapper.find('[data-testid="document-converter-retry"]').exists()).toBe(false);
  });

  it("records immediately succeeded single-file jobs as ready results instead of failed history", async () => {
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "lektion.html",
          job_id: "job-ready",
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "succeeded",
        },
      ],
    });
    fileApiMocks.getDocumentConverterJobStatus.mockResolvedValue({
      error: null,
      job_id: "job-ready",
      result_artifact: {
        artifact_id: "artifact-ready",
        content_type: "application/pdf",
        download_url: null,
        filename: "lektion.pdf",
        kind: "converted_document",
        size_bytes: 128,
        source_entry_id: null,
      },
      status: "succeeded",
    });
    fileApiMocks.downloadDocumentConverterJobArtifact.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "lektion.pdf",
    });

    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [new File(["<h1>Hej</h1>"], "lektion.html", { type: "text/html" })],
    });
    await input.trigger("change");
    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();

    expect(fileApiMocks.getDocumentConverterJobStatus).toHaveBeenCalledWith({ jobId: "job-ready" });
    expect(wrapper.text()).toContain("lektion.pdf");
    expect(wrapper.text()).not.toContain("Misslyckades");
    expect(wrapper.text()).not.toContain("Konverteringen kunde inte slutföras.");
    expect(wrapper.text()).not.toContain("Historik");
  });
});
