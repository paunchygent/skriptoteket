/**
 * Document Converter route-visible workflow specs.
 *
 * Domain purpose:
 *   Prove the authenticated Document Converter route automatically renders the
 *   current HTML/CSS project into a real embedded PDF preview while keeping
 *   teacher-facing copy truthful and stale state non-authoritative.
 *
 * Relationships:
 *   - Exercises `DocumentConverterView.vue` through user-visible controls.
 *   - Mocks only the route-specific project-preview API boundary.
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

type Deferred<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T | PromiseLike<T>) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: Deferred<T>["resolve"];
  let reject!: Deferred<T>["reject"];
  const promise = new Promise<T>((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, reject, resolve };
}

function textFile(name: string, content: string, type: string): File {
  return new File([content], name, { type });
}

function mockFiles(input: Element, files: File[]): void {
  Object.defineProperty(input, "files", {
    configurable: true,
    value: files,
  });
}

function buildPreviewResult(params?: {
  artifacts?: Array<{
    artifactId: string;
    filename: string;
    sourceEntryId?: string | null;
  }>;
  artifactId?: string;
  filename?: string;
  outputMode?: "separate_pdfs" | "combined_pdf";
  previewId?: string;
  sourceEntryId?: string | null;
  templateId?: "academic_phd" | "clean_worksheet" | "expressive_handout";
}) {
  const artifacts = params?.artifacts?.map((artifact) => ({
    artifact_id: artifact.artifactId,
    content_type: "application/pdf",
    download_url: null,
    filename: artifact.filename,
    kind: "combined_pdf",
    size_bytes: 128,
    source_entry_id: artifact.sourceEntryId ?? null,
  })) ?? [
    {
      artifact_id: params?.artifactId ?? "artifact-1",
      content_type: "application/pdf",
      download_url: null,
      filename: params?.filename ?? "index.pdf",
      kind: "combined_pdf",
      size_bytes: 128,
      source_entry_id: params?.sourceEntryId ?? null,
    },
  ];
  return {
    artifacts,
    created_at: "2026-06-25T12:00:00Z",
    error: null,
    expires_at: "2026-06-26T12:00:00Z",
    output_mode: params?.outputMode ?? "combined_pdf",
    preview_id: params?.previewId ?? "preview-1",
    status: "succeeded",
    template_id: params?.templateId ?? "academic_phd",
  } as const;
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

async function dropProjectFiles(wrapper: VueWrapper, files: File[]): Promise<void> {
  await wrapper.get('[data-testid="document-converter-dropzone"]').trigger("dragover");
  await wrapper.get('[data-testid="document-converter-dropzone"]').trigger("drop", {
    dataTransfer: { files },
  });
}

async function flushAutoPreview(ms = AUTO_PREVIEW_DEBOUNCE_MS): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

describe("DocumentConverterView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiMocks.discardDocumentConverterProjectPreview.mockReset();
    apiMocks.downloadDocumentConverterProjectPreviewArtifact.mockReset();
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockReset();
    apiMocks.renderDocumentConverterProjectPreview.mockReset();
    apiMocks.saveDocumentConverterProjectPreviewArtifact.mockReset();

    let objectUrlSequence = 0;
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => {
        objectUrlSequence += 1;
        return `blob:document-converter-${objectUrlSequence}`;
      }),
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

  it("hides the internal template selector, exposes the compact drop zone, and removes legacy preview bookkeeping", async () => {
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
    expect(text).not.toContain("Ingen PDF ännu");
    expect(wrapper.find('[data-testid="document-converter-preview"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="document-converter-discard"]').exists()).toBe(false);
    expect(wrapper.find('[aria-label="Status"]').exists()).toBe(false);
    expect(wrapper.find('select[aria-label="Mall"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-test^="document-converter-output-"]')).toHaveLength(2);

    await wrapper.get('[data-testid="document-converter-dropzone"]').trigger("click");

    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it("automatically renders an embedded PDF after adding a supported HTML project and refreshes on governed changes", async () => {
    const secondRender = deferred<ReturnType<typeof buildPreviewResult>>();

    apiMocks.renderDocumentConverterProjectPreview
      .mockResolvedValueOnce(
        buildPreviewResult({
          artifactId: "artifact-a4",
          filename: "index-a4.pdf",
          outputMode: "separate_pdfs",
          previewId: "preview-a4",
        }),
      )
      .mockReturnValueOnce(secondRender.promise);
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "index.pdf",
    });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);

    expect(apiMocks.renderDocumentConverterProjectPreview).not.toHaveBeenCalled();
    await flushAutoPreview(AUTO_PREVIEW_DEBOUNCE_MS - 1);
    expect(apiMocks.renderDocumentConverterProjectPreview).not.toHaveBeenCalled();

    await flushAutoPreview(1);

    expect(apiMocks.renderDocumentConverterProjectPreview).toHaveBeenCalledWith(
      expect.objectContaining({
        htmlEntryFilename: "index.html",
        outputMode: "separate_pdfs",
        paperSize: "a4",
        templateId: "academic_phd",
      }),
    );
    expect(apiMocks.loadDocumentConverterProjectPreviewArtifactBlob).toHaveBeenCalledWith({
      artifact: expect.objectContaining({ artifact_id: "artifact-a4" }),
      previewId: "preview-a4",
    });

    const firstFrame = wrapper.get<HTMLIFrameElement>(
      '[data-testid="document-converter-pdf-frame"]',
    );
    expect(firstFrame.attributes("src")).toMatch(/^blob:document-converter-/);
    expect(wrapper.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      undefined,
    );
    expect(wrapper.get('[data-testid="document-converter-save"]').attributes("disabled")).toBe(
      undefined,
    );
    expect(wrapper.text()).not.toContain("Skapar PDF...");
    expect(wrapper.text()).not.toContain("Det gick inte att skapa PDF:en.");

    await wrapper.get('[data-test="document-converter-output-combined_pdf"]').trigger("click");
    await wrapper.get('[data-test="document-converter-paper-a3"]').trigger("click");

    await flushAutoPreview();

    expect(apiMocks.renderDocumentConverterProjectPreview).toHaveBeenLastCalledWith(
      expect.objectContaining({
        outputMode: "combined_pdf",
        paperSize: "a3",
        templateId: "academic_phd",
      }),
    );
    expect(wrapper.text()).toContain("Skapar PDF...");
    expect(wrapper.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      undefined,
    );
    expect(wrapper.get('[data-testid="document-converter-save"]').attributes("disabled")).toBe(
      undefined,
    );

    secondRender.resolve(
      buildPreviewResult({
        artifactId: "artifact-a3",
        filename: "index-a3.pdf",
        outputMode: "combined_pdf",
        previewId: "preview-a3",
        templateId: "academic_phd",
      }),
    );
    await flushPromises();

    expect(
      wrapper.get<HTMLIFrameElement>('[data-testid="document-converter-pdf-frame"]').attributes(
        "src",
      ),
    ).toMatch(/^blob:document-converter-/);
    expect(wrapper.text()).toContain("index-a3.pdf");
  });

  it("shares validation and merge behavior between drag-drop and picker intake", async () => {
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue(
      buildPreviewResult({
        artifactId: "artifact-separate",
        outputMode: "separate_pdfs",
        previewId: "preview-separated",
        sourceEntryId: "index",
      }),
    );
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "index.pdf",
    });

    const wrapper = mount(DocumentConverterView);

    await dropProjectFiles(wrapper, [
      textFile("styles.css", "h1{}", "text/css"),
      textFile("cover.png", "png", "image/png"),
    ]);
    await flushAutoPreview();

    expect(apiMocks.renderDocumentConverterProjectPreview).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("CSS (1/10)");
    expect(wrapper.text()).toContain("Bilder (1/20)");
    expect(wrapper.text()).toContain("HTML/CSS");

    await addProjectFiles(wrapper, [textFile("index.html", "<h1>Hej</h1>", "text/html")]);
    await flushAutoPreview();

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

  it("keeps the previous PDF visible but disables artifact actions after a failed auto-refresh until retry succeeds", async () => {
    apiMocks.renderDocumentConverterProjectPreview
      .mockResolvedValueOnce(
        buildPreviewResult({
          artifactId: "artifact-success-1",
          filename: "first.pdf",
          outputMode: "separate_pdfs",
          previewId: "preview-success-1",
        }),
      )
      .mockRejectedValueOnce(new Error("latest failed"))
      .mockResolvedValueOnce(
        buildPreviewResult({
          artifactId: "artifact-success-2",
          filename: "retry.pdf",
          outputMode: "combined_pdf",
          previewId: "preview-success-2",
        }),
      );
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "index.pdf",
    });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await flushAutoPreview();

    expect(wrapper.text()).toContain("first.pdf");
    expect(wrapper.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      undefined,
    );
    const successfulSrc = wrapper.get<HTMLIFrameElement>(
      '[data-testid="document-converter-pdf-frame"]',
    ).attributes("src");

    await wrapper.get('[data-test="document-converter-output-combined_pdf"]').trigger("click");
    await flushAutoPreview();

    expect(wrapper.text()).toContain("Det gick inte att skapa PDF:en.");
    expect(wrapper.text()).toContain("first.pdf");
    expect(
      wrapper.get<HTMLIFrameElement>('[data-testid="document-converter-pdf-frame"]').attributes(
        "src",
      ),
    ).toBe(successfulSrc);
    expect(wrapper.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      undefined,
    );
    expect(wrapper.get('[data-testid="document-converter-save"]').attributes("disabled")).toBe(
      undefined,
    );
    expect(wrapper.get('[data-testid="document-converter-retry"]').attributes("aria-label")).toBe(
      "Försök igen",
    );
    expect(wrapper.get('[data-testid="document-converter-retry"]').attributes("title")).toBe(
      "Försök igen",
    );
    expect(wrapper.find('[data-testid="document-converter-preview"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="document-converter-discard"]').exists()).toBe(false);

    await wrapper.get('[data-testid="document-converter-retry"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("retry.pdf");
    expect(wrapper.text()).not.toContain("Det gick inte att skapa PDF:en.");
    expect(wrapper.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      undefined,
    );
    expect(wrapper.get('[data-testid="document-converter-save"]').attributes("disabled")).toBe(
      undefined,
    );
  });

  it("revokes superseded PDF object URLs when the preview changes and when the route unmounts", async () => {
    apiMocks.renderDocumentConverterProjectPreview
      .mockResolvedValueOnce(
        buildPreviewResult({
          artifactId: "artifact-1",
          filename: "first.pdf",
          previewId: "preview-1",
        }),
      )
      .mockResolvedValueOnce(
        buildPreviewResult({
          artifactId: "artifact-2",
          filename: "second.pdf",
          previewId: "preview-2",
          templateId: "clean_worksheet",
        }),
      );
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockResolvedValue({
      blob: new Blob(["pdf"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "index.pdf",
    });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await flushAutoPreview();

    await wrapper.get('[data-test="document-converter-paper-a3"]').trigger("click");
    await flushAutoPreview();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:document-converter-1");

    wrapper.unmount();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:document-converter-2");
  });

  it("rejects unsupported files before preview submission", async () => {
    const wrapper = mount(DocumentConverterView);

    await addProjectFiles(wrapper, [textFile("notes.txt", "text", "text/plain")]);
    await flushAutoPreview();

    expect(wrapper.text()).toContain("Filen stöds inte. Lägg till HTML, CSS eller bilder.");
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
    await flushAutoPreview();

    expect(wrapper.text()).toContain("Du kan lägga till högst 10 HTML-filer.");
    expect(apiMocks.renderDocumentConverterProjectPreview).not.toHaveBeenCalled();
  });
});
