/** Shared API doubles and isolated single-file route setup. */
import { flushPromises, mount } from "@vue/test-utils";
import DocumentConverterView from "./DocumentConverterView.vue";
import { afterEach, beforeEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

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

export { fileApiMocks };

export function setupSingleFileView(): void {
  beforeEach(() => {
    setActivePinia(createPinia());
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

}

/** A completed local HTML conversion shared by result-action and mode-isolation specs. */
export async function mountReadySingleFileResult() {
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

    return wrapper;
}
