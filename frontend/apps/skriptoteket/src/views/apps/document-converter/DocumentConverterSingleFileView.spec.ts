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
    expect(text).not.toContain("HTML till PDF");
    expect(text).not.toContain("Filoperationer");
    expect(text).not.toContain("HTML/CSS-projekt till PDF");
    expect(text).not.toContain("Automatisk förhandsvisning");
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

  it("uses the same source operations preview ownership for single-file conversion", async () => {
    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const sourceColumn = wrapper.get('[data-testid="document-converter-source-column"]');
    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const previewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(sourceColumn.find('[data-testid="document-converter-single-file-input"]').exists()).toBe(
      true,
    );
    expect(sourceColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      false,
    );

    expect(operationsColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      true,
    );
    expect(operationsColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      true,
    );
    expect(operationsColumn.find('[data-testid="document-converter-download"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-save"]').exists()).toBe(true);

    expect(previewColumn.find('[data-testid="document-converter-single-file-input"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-download"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-save"]').exists()).toBe(false);
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

    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const previewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(operationsColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      true,
    );
    expect(operationsColumn.findAll(".dc-artifact-selector__item")).toHaveLength(2);
    expect(previewColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );
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

  it("keeps a succeeded single-file result in the same source operations preview columns", async () => {
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

    const sourceColumn = wrapper.get('[data-testid="document-converter-source-column"]');
    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const previewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(fileApiMocks.getDocumentConverterJobStatus).toHaveBeenCalledWith({ jobId: "job-ready" });
    expect(sourceColumn.find('[data-testid="document-converter-single-file-input"]').exists()).toBe(
      true,
    );
    expect(sourceColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      false,
    );
    expect(sourceColumn.text()).toContain("1. lektion.html");

    expect(operationsColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      true,
    );
    expect(
      operationsColumn.get<HTMLInputElement>('[data-testid="document-converter-filename-stem"]')
        .element.value,
    ).toBe("lektion");
    expect(operationsColumn.text()).toContain(".pdf");
    expect(operationsColumn.find('[data-testid="document-converter-download"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-save"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );

    expect(previewColumn.find('[data-testid="document-converter-pdf-frame"]').exists()).toBe(true);
    expect(previewColumn.text()).toContain("lektion.pdf");
    expect(previewColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-download"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-save"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );

    expect(wrapper.text()).toContain("lektion.pdf");
    expect(wrapper.text()).not.toContain("Misslyckades");
    expect(wrapper.text()).not.toContain("Konverteringen kunde inte slutföras.");
    expect(wrapper.text()).not.toContain("Historik");
  });
});
