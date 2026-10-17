/** Project API doubles, file intake fixtures and result-control assertions. */
import { flushPromises, type VueWrapper } from "@vue/test-utils";
import { expect, vi } from "vitest";

export const AUTO_PREVIEW_DEBOUNCE_MS = 350;

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

export { apiMocks };

export type Deferred<T> = {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T | PromiseLike<T>) => void;
};

export function deferred<T>(): Deferred<T> {
  let resolve!: Deferred<T>["resolve"];
  let reject!: Deferred<T>["reject"];
  const promise = new Promise<T>((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, reject, resolve };
}

export function textFile(name: string, content: string, type: string): File {
  return new File([content], name, { type });
}

export function mockFiles(input: Element, files: File[]): void {
  Object.defineProperty(input, "files", {
    configurable: true,
    value: files,
  });
}

export function buildPreviewResult(params?: {
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

export async function addProjectFiles(wrapper: VueWrapper, files?: File[]): Promise<void> {
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

export async function dropProjectFiles(wrapper: VueWrapper, files: File[]): Promise<void> {
  await wrapper.get('[data-testid="document-converter-dropzone"]').trigger("dragover");
  await wrapper.get('[data-testid="document-converter-dropzone"]').trigger("drop", {
    dataTransfer: { files },
  });
}

export async function flushAutoPreview(ms = AUTO_PREVIEW_DEBOUNCE_MS): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

export function expectResultActionsEnabled(wrapper: VueWrapper): void {
  expect(resultActionDisabledState(wrapper)).toEqual([undefined, undefined, undefined]);
}
export function expectResultActionsDisabled(wrapper: VueWrapper): void {
  expect(resultActionDisabledState(wrapper)).toEqual(["", "", ""]);
}
export function resultActionDisabledState(wrapper: VueWrapper): Array<string | undefined> {
  return [
    wrapper.get('[data-testid="document-converter-download"]').attributes("disabled"),
    wrapper.get('[data-testid="document-converter-save"]').attributes("disabled"),
    wrapper.get<HTMLInputElement>('[data-testid="document-converter-filename-stem"]').attributes("disabled"),
  ];
}

export function expectFilenameIntent(wrapper: VueWrapper, stem: string, extension: string): void {
  const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
  expect(
    operationsColumn.get<HTMLInputElement>('[data-testid="document-converter-filename-stem"]').element.value,
  ).toBe(stem);
  expect(operationsColumn.text()).toContain(`.${extension}`);
}
