/** Route-level feedback must announce the selected failure, not stale progress. */
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DocumentConverterView from "./DocumentConverterView.vue";

const fileApi = vi.hoisted(() => ({
  listDocumentConverterSavedFiles: vi.fn(),
  listDocumentConverterSingleFileRoutes: vi.fn(),
  submitDocumentConverterUploadJob: vi.fn(),
  submitDocumentConverterSavedFileJob: vi.fn(),
  getDocumentConverterJobStatus: vi.fn(),
  downloadDocumentConverterJobArtifact: vi.fn(),
  saveDocumentConverterJobArtifact: vi.fn(),
}));
vi.mock("./documentConverterFileApi", () => fileApi);

async function selectUpload(wrapper: VueWrapper, filename: string): Promise<void> {
  const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [new File(["source"], filename)],
  });
  await input.trigger("change");
}

async function startConversion(): Promise<VueWrapper> {
  const wrapper = mount(DocumentConverterView);
  await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
  await flushPromises();
  await selectUpload(wrapper, "lektion.html");
  await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
  await flushPromises();
  expect(fileApi.submitDocumentConverterUploadJob).toHaveBeenCalledOnce();
  return wrapper;
}

describe("DocumentConverterView feedback selection", () => {
  let wrapper: VueWrapper | undefined;

  beforeEach(() => {
    vi.resetAllMocks();
    setActivePinia(createPinia());
    fileApi.listDocumentConverterSavedFiles.mockResolvedValue({ files: [] });
    fileApi.listDocumentConverterSingleFileRoutes.mockResolvedValue({
      routes: [{ source_format: "html", output_format: "pdf", title: "HTML -> PDF" }],
    });
    // Leave the real submission in progress while the teacher changes the source.
    fileApi.submitDocumentConverterUploadJob.mockReturnValue(new Promise(() => {}));
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.restoreAllMocks();
  });

  it("announces an unsupported replacement file instead of the existing conversion progress", async () => {
    wrapper = await startConversion();
    expect(wrapper.get('[role="status"]').text()).toBe("Startar konverteringen...");

    await selectUpload(wrapper, "lektion.exe");

    const alert = wrapper.get('[role="alert"]');
    expect(alert.text()).toBe("Filformatet stöds inte. Välj HTML, DOCX, Markdown eller PDF.");
    expect(alert.attributes("aria-live")).toBe("assertive");
    expect(alert.attributes("aria-atomic")).toBe("true");
    expect(wrapper.text()).not.toContain("Startar konverteringen...");
  });

  it("announces ordinary conversion progress politely without an alert", async () => {
    wrapper = await startConversion();

    const status = wrapper.get('[role="status"]');
    expect(status.text()).toBe("Startar konverteringen...");
    expect(status.attributes("aria-live")).toBe("polite");
    expect(status.attributes("aria-atomic")).toBe("true");
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
  });
});
