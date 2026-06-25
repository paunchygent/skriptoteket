/**
 * Document Converter route-visible workflow specs.
 *
 * Domain purpose:
 *   Prove the authenticated Document Converter route renders the approved
 *   Swedish HTML/CSS project workflow and maps visible export choices onto the
 *   scoped project-preview API contract.
 *
 * Relationships:
 *   - Exercises `DocumentConverterView.vue` through user-visible controls.
 *   - Mocks only the route-specific project-preview API boundary.
 */

import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentConverterView from "./DocumentConverterView.vue";

const apiMocks = vi.hoisted(() => ({
  discardDocumentConverterProjectPreview: vi.fn(),
  downloadDocumentConverterProjectPreviewArtifact: vi.fn(),
  renderDocumentConverterProjectPreview: vi.fn(),
  saveDocumentConverterProjectPreviewArtifact: vi.fn(),
}));

vi.mock("./documentConverterProjectPreviewApi", () => ({
  discardDocumentConverterProjectPreview: apiMocks.discardDocumentConverterProjectPreview,
  downloadDocumentConverterProjectPreviewArtifact:
    apiMocks.downloadDocumentConverterProjectPreviewArtifact,
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

async function addProjectFiles(wrapper: VueWrapper, files?: File[]): Promise<void> {
  const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-file-input"]');
  mockFiles(
    input.element,
    files ?? [
      textFile("index.html", "<h1>Hej</h1>", "text/html"),
      textFile("styles.css", "h1{}", "text/css"),
      textFile("cover.png", "png", "image/png"),
    ],
  );
  await input.trigger("change");
}

describe("DocumentConverterView", () => {
  beforeEach(() => {
    apiMocks.discardDocumentConverterProjectPreview.mockReset();
    apiMocks.downloadDocumentConverterProjectPreviewArtifact.mockReset();
    apiMocks.renderDocumentConverterProjectPreview.mockReset();
    apiMocks.saveDocumentConverterProjectPreviewArtifact.mockReset();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:document-converter"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders locked Swedish copy with two output choices and real paper sizes", () => {
    const wrapper = mount(DocumentConverterView);
    const text = wrapper.text();

    expect(text).toContain("DOKUMENTKONVERTERARE");
    expect(text).toContain("HTML/CSS");
    expect(text).toContain("Lägg till fil");
    expect(text).toContain("Exportera som");
    expect(text).toContain("Enskilda PDF-filer");
    expect(text).toContain("Kombinerad PDF");
    expect(text).toContain("Format");
    expect(text).toContain("A3");
    expect(text).toContain("A4");
    expect(text).toContain("A5");
    expect(text).not.toContain("Båda");
    expect(text).not.toContain("both");
    expect(text).not.toContain("rendera");
    expect(text).not.toContain("artifact");
    expect(text).not.toContain("preview id");
    expect(text).not.toContain("TTL");
    expect(text).not.toContain("backend");
    expect(text).not.toContain("Flera dokument");
    expect(text).not.toContain("SKRIPTOTEKET");
    expect(wrapper.findAll('[data-test^="document-converter-output-"]')).toHaveLength(2);
    expect(wrapper.findAll('[data-testid="document-converter-file-input"]')).toHaveLength(1);
  });

  it("maps visible output labels to separate_pdfs and combined_pdf in the submitted manifest", async () => {
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue({
      artifacts: [
        {
          artifact_id: "artifact-separate",
          content_type: "application/pdf",
          download_url: null,
          filename: "index.pdf",
          kind: "separate_pdf",
          size_bytes: 12,
          source_entry_id: "index",
        },
      ],
      created_at: "2026-06-25T12:00:00Z",
      error: null,
      expires_at: "2026-06-26T12:00:00Z",
      output_mode: "separate_pdfs",
      preview_id: "preview-1",
      status: "succeeded",
      template_id: "academic_phd",
    });
    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);

    await wrapper.get('[data-test="document-converter-paper-a5"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    expect(apiMocks.renderDocumentConverterProjectPreview).toHaveBeenLastCalledWith(
      expect.objectContaining({
        htmlEntryFilename: "index.html",
        outputMode: "separate_pdfs",
        paperSize: "a5",
      }),
    );

    await wrapper.get('[data-test="document-converter-output-combined_pdf"]').trigger("click");
    await wrapper.get('[data-test="document-converter-paper-a3"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    expect(apiMocks.renderDocumentConverterProjectPreview).toHaveBeenLastCalledWith(
      expect.objectContaining({
        outputMode: "combined_pdf",
        paperSize: "a3",
      }),
    );
  });

  it("keeps CSS and image files added before the HTML entry", async () => {
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue({
      artifacts: [
        {
          artifact_id: "artifact-separate",
          content_type: "application/pdf",
          download_url: null,
          filename: "index.pdf",
          kind: "separate_pdf",
          size_bytes: 12,
          source_entry_id: "index",
        },
      ],
      created_at: "2026-06-25T12:00:00Z",
      error: null,
      expires_at: "2026-06-26T12:00:00Z",
      output_mode: "separate_pdfs",
      preview_id: "preview-1",
      status: "succeeded",
      template_id: "academic_phd",
    });
    const wrapper = mount(DocumentConverterView);

    await addProjectFiles(wrapper, [
      textFile("styles.css", "h1{}", "text/css"),
      textFile("cover.png", "png", "image/png"),
    ]);
    expect(wrapper.text()).toContain("CSS (1/10)");
    expect(wrapper.text()).toContain("Bilder (1/20)");
    expect(wrapper.text()).toContain("HTML/CSS");

    await addProjectFiles(wrapper, [textFile("index.html", "<h1>Hej</h1>", "text/html")]);
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    expect(apiMocks.renderDocumentConverterProjectPreview).toHaveBeenLastCalledWith(
      expect.objectContaining({
        files: expect.arrayContaining([
          expect.objectContaining({ name: "styles.css" }),
          expect.objectContaining({ name: "cover.png" }),
          expect.objectContaining({ name: "index.html" }),
        ]),
        htmlEntryFilename: "index.html",
      }),
    );
  });

  it("replaces an existing project file when the same filename is added again", async () => {
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue({
      artifacts: [
        {
          artifact_id: "artifact-separate",
          content_type: "application/pdf",
          download_url: null,
          filename: "index.pdf",
          kind: "separate_pdf",
          size_bytes: 12,
          source_entry_id: "index",
        },
      ],
      created_at: "2026-06-25T12:00:00Z",
      error: null,
      expires_at: "2026-06-26T12:00:00Z",
      output_mode: "separate_pdfs",
      preview_id: "preview-1",
      status: "succeeded",
      template_id: "academic_phd",
    });
    const wrapper = mount(DocumentConverterView);

    await addProjectFiles(wrapper, [textFile("index.html", "<h1>Old</h1>", "text/html")]);
    await addProjectFiles(wrapper, [
      textFile("index.html", "<h1>Changed document</h1>", "text/html"),
    ]);
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    const submittedFiles = apiMocks.renderDocumentConverterProjectPreview.mock.lastCall?.[0]
      .files as File[];
    expect(submittedFiles.filter((file) => file.name === "index.html")).toHaveLength(1);
  });

  it("rejects unsupported files before preview submission", async () => {
    const wrapper = mount(DocumentConverterView);

    await addProjectFiles(wrapper, [textFile("notes.txt", "text", "text/plain")]);

    expect(wrapper.text()).toContain("Filen stöds inte. Lägg till HTML, CSS eller bilder.");
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");

    expect(apiMocks.renderDocumentConverterProjectPreview).not.toHaveBeenCalled();
  });

  it("rejects file groups over the governed caps before preview submission", async () => {
    const wrapper = mount(DocumentConverterView);

    await addProjectFiles(
      wrapper,
      Array.from({ length: 11 }, (_, index) =>
        textFile(`page-${index + 1}.html`, "<h1>Hej</h1>", "text/html"),
      ),
    );

    expect(wrapper.text()).toContain("Du kan lägga till högst 10 HTML-filer.");
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");

    expect(apiMocks.renderDocumentConverterProjectPreview).not.toHaveBeenCalled();
  });

  it("renders preview result actions, downloads selected artifacts, saves, and discards", async () => {
    const artifact = {
      artifact_id: "artifact-1",
      content_type: "application/pdf",
      download_url: null,
      filename: "index.pdf",
      kind: "combined_pdf",
      size_bytes: 128,
      source_entry_id: null,
    };
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue({
      artifacts: [artifact],
      created_at: "2026-06-25T12:00:00Z",
      error: null,
      expires_at: "2026-06-26T12:00:00Z",
      output_mode: "combined_pdf",
      preview_id: "preview-1",
      status: "succeeded",
      template_id: "academic_phd",
    });
    apiMocks.downloadDocumentConverterProjectPreviewArtifact.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "index.pdf",
    });
    apiMocks.saveDocumentConverterProjectPreviewArtifact.mockResolvedValue({
      source_artifact_id: "source-1",
      vault_artifact: {
        bytes: 128,
        created_at: "2026-06-25T12:10:00Z",
        file_id: "vault-1",
        name: "index.pdf",
      },
    });
    apiMocks.discardDocumentConverterProjectPreview.mockResolvedValue({
      preview_id: "preview-1",
      status: "discarded",
    });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await wrapper.get('[data-test="document-converter-output-combined_pdf"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("index.pdf");
    expect(wrapper.text()).toContain("Tillfällig förhandsvisning");
    expect(wrapper.get(".dc-preview-state").find("span").exists()).toBe(false);
    expect(wrapper.find(".dc-preview-tools").exists()).toBe(false);
    expect(wrapper.find(".dc-page-strip").exists()).toBe(false);
    expect(wrapper.find('[data-testid="document-converter-artifact-result"]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain("1 / 1");
    expect(wrapper.text()).not.toContain("100%");

    await wrapper.get('[data-testid="document-converter-download"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-save"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-discard"]').trigger("click");
    await flushPromises();

    expect(apiMocks.downloadDocumentConverterProjectPreviewArtifact).toHaveBeenCalledWith({
      artifact,
      previewId: "preview-1",
    });
    expect(apiMocks.saveDocumentConverterProjectPreviewArtifact).toHaveBeenCalledWith({
      artifact,
      previewId: "preview-1",
    });
    expect(apiMocks.discardDocumentConverterProjectPreview).toHaveBeenCalledWith({
      previewId: "preview-1",
    });
    expect(wrapper.text()).not.toContain("index.pdf");
  });

  it("marks preview output stale after input or export changes and shows a recovery path on failure", async () => {
    apiMocks.renderDocumentConverterProjectPreview
      .mockResolvedValueOnce({
        artifacts: [
          {
            artifact_id: "artifact-1",
            content_type: "application/pdf",
            download_url: null,
            filename: "index.pdf",
            kind: "combined_pdf",
            size_bytes: 128,
            source_entry_id: null,
          },
        ],
        created_at: "2026-06-25T12:00:00Z",
        error: null,
        expires_at: "2026-06-26T12:00:00Z",
        output_mode: "combined_pdf",
        preview_id: "preview-1",
        status: "succeeded",
        template_id: "academic_phd",
      })
      .mockRejectedValueOnce(new Error("nope"));

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await wrapper.get('[data-test="document-converter-output-combined_pdf"]').trigger("click");
    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="document-converter-output-separate_pdfs"]').trigger("click");
    expect(wrapper.text()).toContain("Uppdatera");

    await wrapper.get('[data-testid="document-converter-preview"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Det gick inte att förhandsvisa.");
    expect(wrapper.text()).toContain("index.pdf");
    expect(wrapper.text()).toContain("Uppdatera");
    expect(wrapper.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      undefined,
    );
  });
});
