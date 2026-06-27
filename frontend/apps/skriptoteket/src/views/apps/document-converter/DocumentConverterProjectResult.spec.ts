/**
 * Document Converter project result specs.
 *
 * Domain purpose:
 *   Prove HTML/CSS project preview results keep artifact choices usable and do
 *   not let stale responses overwrite the current result state.
 *
 * Relationships:
 *   - Exercises `DocumentConverterView.vue` through user-visible result
 *     controls.
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

async function addProjectFiles(wrapper: VueWrapper): Promise<void> {
  const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-file-input"]');
  mockFiles(input.element, [textFile("index.html", "<h1>Hej</h1>", "text/html")]);
  await input.trigger("change");
}

async function flushAutoPreview(ms = AUTO_PREVIEW_DEBOUNCE_MS): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

describe("DocumentConverterView project results", () => {
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

  it("keeps the project artifact selector working for multi-pdf previews", async () => {
    apiMocks.renderDocumentConverterProjectPreview.mockResolvedValue(
      buildPreviewResult({
        artifacts: [
          { artifactId: "artifact-1", filename: "index.pdf" },
          { artifactId: "artifact-2", filename: "appendix.pdf" },
        ],
        outputMode: "separate_pdfs",
        previewId: "preview-multi",
      }),
    );
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob
      .mockResolvedValueOnce({
        blob: new Blob(["first"], { type: "application/pdf" }),
        contentType: "application/pdf",
        filename: "index.pdf",
      })
      .mockResolvedValueOnce({
        blob: new Blob(["second"], { type: "application/pdf" }),
        contentType: "application/pdf",
        filename: "appendix.pdf",
      });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await flushAutoPreview();

    expect(wrapper.findAll(".dc-artifact-list__item")).toHaveLength(2);
    expect(wrapper.text()).toContain("index.pdf");

    await wrapper.findAll(".dc-artifact-list__item")[1]!.trigger("click");
    await flushPromises();

    expect(apiMocks.loadDocumentConverterProjectPreviewArtifactBlob).toHaveBeenLastCalledWith({
      artifact: expect.objectContaining({ artifact_id: "artifact-2", filename: "appendix.pdf" }),
      previewId: "preview-multi",
    });
    expect(
      wrapper.get<HTMLIFrameElement>('[data-testid="document-converter-pdf-frame"]').attributes(
        "src",
      ),
    ).toMatch(/^blob:document-converter-/);
    expect(wrapper.text()).toContain("appendix.pdf");
  });

  it("ignores stale preview responses so older renders cannot overwrite newer selected state", async () => {
    const firstRender = deferred<ReturnType<typeof buildPreviewResult>>();
    const secondRender = deferred<ReturnType<typeof buildPreviewResult>>();

    apiMocks.renderDocumentConverterProjectPreview
      .mockReturnValueOnce(firstRender.promise)
      .mockReturnValueOnce(secondRender.promise);
    apiMocks.loadDocumentConverterProjectPreviewArtifactBlob.mockImplementation(async (params) => {
      return {
        blob: new Blob([params.previewId], { type: "application/pdf" }),
        contentType: "application/pdf",
        filename: `${params.previewId}.pdf`,
      };
    });

    const wrapper = mount(DocumentConverterView);
    await addProjectFiles(wrapper);
    await flushAutoPreview();

    await wrapper.get('[data-test="document-converter-output-combined_pdf"]').trigger("click");
    await flushAutoPreview();

    secondRender.resolve(
      buildPreviewResult({
        artifactId: "artifact-new",
        filename: "current.pdf",
        outputMode: "combined_pdf",
        previewId: "preview-current",
      }),
    );
    await flushPromises();
    expect(wrapper.text()).toContain("current.pdf");
    const currentSrc = wrapper.get<HTMLIFrameElement>(
      '[data-testid="document-converter-pdf-frame"]',
    ).attributes("src");

    firstRender.resolve(
      buildPreviewResult({
        artifactId: "artifact-old",
        filename: "stale.pdf",
        outputMode: "separate_pdfs",
        previewId: "preview-stale",
      }),
    );
    await flushPromises();

    expect(wrapper.text()).toContain("current.pdf");
    expect(wrapper.text()).not.toContain("stale.pdf");
    expect(
      wrapper.get<HTMLIFrameElement>('[data-testid="document-converter-pdf-frame"]').attributes(
        "src",
      ),
    ).toBe(currentSrc);
  });
});
