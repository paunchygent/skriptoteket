/**
 * Document Converter layout ownership specs.
 *
 * Domain purpose:
 *   Prove the route keeps intake, file operations, and preview responsibilities
 *   in their own columns for the Document Converter teacher workflow.
 *
 * Relationships:
 *   - Exercises `DocumentConverterView.vue` through rendered DOM ownership.
 *   - Mocks the project-preview API boundary for the HTML/CSS preview lane.
 */

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DocumentConverterView from "./DocumentConverterView.vue";

const AUTO_PREVIEW_DEBOUNCE_MS = 350;

const apiMocks = vi.hoisted(() => ({
  discardDocumentConverterProjectPreview: vi.fn(),
  downloadDocumentConverterProjectPreviewArtifact: vi.fn(),
  loadDocumentConverterProjectPreviewArtifactBlob: vi.fn(),
  renderDocumentConverterProjectPreview: vi.fn(),
  saveDocumentConverterProjectPreviewArtifact: vi.fn(),
}));

vi.mock("./documentConverterProjectPreviewApi", () => ({
  discardDocumentConverterProjectPreview: apiMocks.discardDocumentConverterProjectPreview,
  downloadDocumentConverterProjectPreviewArtifact:
    apiMocks.downloadDocumentConverterProjectPreviewArtifact,
  loadDocumentConverterProjectPreviewArtifactBlob:
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob,
  renderDocumentConverterProjectPreview: apiMocks.renderDocumentConverterProjectPreview,
  saveDocumentConverterProjectPreviewArtifact:
    apiMocks.saveDocumentConverterProjectPreviewArtifact,
}));

function textFile(name: string, content: string, type: string): File {
  return new File([content], name, { type });
}

function mockFiles(input: Element, files: File[]): void {
  Object.defineProperty(input, "files", {
    configurable: true,
    value: files,
  });
}

function buildPreviewResult() {
  return {
    artifacts: [
      {
        artifact_id: "artifact-a4",
        content_type: "application/pdf",
        download_url: null,
        filename: "index-a4.pdf",
        kind: "combined_pdf",
        size_bytes: 128,
        source_entry_id: null,
      },
      {
        artifact_id: "artifact-a5",
        content_type: "application/pdf",
        download_url: null,
        filename: "appendix-a5.pdf",
        kind: "combined_pdf",
        size_bytes: 128,
        source_entry_id: null,
      },
    ],
    created_at: "2026-06-25T12:00:00Z",
    error: null,
    expires_at: "2026-06-26T12:00:00Z",
    output_mode: "separate_pdfs",
    preview_id: "preview-a4",
    status: "succeeded",
    template_id: "academic_phd",
  } as const;
}

async function addProjectFiles(wrapper: VueWrapper): Promise<void> {
  const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-file-input"]');
  mockFiles(input.element, [
    textFile("index.html", "<h1>Hej</h1>", "text/html"),
    textFile("styles.css", "h1{}", "text/css"),
    textFile("cover.png", "png", "image/png"),
  ]);
  await input.trigger("change");
}

async function flushAutoPreview(): Promise<void> {
  await vi.advanceTimersByTimeAsync(AUTO_PREVIEW_DEBOUNCE_MS);
  await flushPromises();
}

describe("DocumentConverterView layout ownership", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiMocks.discardDocumentConverterProjectPreview.mockReset();
    apiMocks.downloadDocumentConverterProjectPreviewArtifact.mockReset();
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockReset();
    apiMocks.renderDocumentConverterProjectPreview.mockReset();
    apiMocks.saveDocumentConverterProjectPreviewArtifact.mockReset();

    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:document-converter-layout"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("keeps the compact project intake surface out of the preview column", async () => {
    const wrapper = mount(DocumentConverterView);
    const fileInput = wrapper.get<HTMLInputElement>('[data-testid="document-converter-file-input"]');
    const clickSpy = vi.spyOn(fileInput.element, "click");
    const text = wrapper.text();

    expect(text).toContain("DOKUMENTKONVERTERARE");
    expect(text).toContain("HTML/CSS");
    expect(text).toContain("Exportera som");
    expect(text).toContain("Enskilda PDF-filer");
    expect(text).toContain("Kombinerad PDF");
    expect(text).toContain("Format");
    expect(text).toContain("Ladda ned");
    expect(text).toContain("Spara i Mina filer");
    expect(text).toContain("Dra filer hit eller klicka");
    expect(text).not.toContain("Lägg till fil");
    expect(text).not.toContain("Mall");
    expect(text).not.toContain("Förhandsvisa");
    expect(text).not.toContain("Tillfällig förhandsvisning");
    expect(text).not.toContain("Automatisk förhandsvisning");
    expect(text).not.toContain("Filoperationer");
    expect(text).not.toContain("HTML/CSS-projekt till PDF");
    expect(text).not.toContain("Ingen PDF ännu");
    expect(wrapper.find('[data-testid="document-converter-preview"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="document-converter-discard"]').exists()).toBe(false);
    expect(wrapper.find('[aria-label="Status"]').exists()).toBe(false);
    expect(wrapper.find('select[aria-label="Mall"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-test^="document-converter-output-"]')).toHaveLength(2);

    await wrapper.get('[data-testid="document-converter-dropzone"]').trigger("click");

    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it("keeps project intake in the source column and file operations out of preview", async () => {
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue(buildPreviewResult());
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "index.pdf",
    });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await flushAutoPreview();

    const sourceColumn = wrapper.get('[data-testid="document-converter-source-column"]');
    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const previewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(sourceColumn.find('[data-testid="document-converter-dropzone"]').exists()).toBe(true);
    expect(sourceColumn.find('[data-testid="document-converter-file-input"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      true,
    );
    expect(operationsColumn.find('[data-testid="document-converter-download"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-save"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      true,
    );
    expect(previewColumn.find('[data-testid="document-converter-dropzone"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-file-input"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-download"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-save"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-pdf-frame"]').exists()).toBe(true);
  });

  it("removes the compact project summary while keeping the dropzone and categorized source lists", async () => {
    const wrapper = mount(DocumentConverterView);

    await addProjectFiles(wrapper);
    await flushPromises();

    const sourceColumn = wrapper.get('[data-testid="document-converter-source-column"]');

    expect(wrapper.find('[aria-label="Mobilöversikt"]').exists()).toBe(false);
    expect(sourceColumn.find('[data-testid="document-converter-dropzone"]').exists()).toBe(true);
    expect(sourceColumn.text()).toContain("HTML (1/10)");
    expect(sourceColumn.text()).toContain("index.html");
    expect(sourceColumn.text()).toContain("CSS (1/10)");
    expect(sourceColumn.text()).toContain("styles.css");
    expect(sourceColumn.text()).toContain("Bilder (1/20)");
    expect(sourceColumn.text()).toContain("cover.png");
    expect(sourceColumn.text()).not.toContain("3 filer");
  });
});
