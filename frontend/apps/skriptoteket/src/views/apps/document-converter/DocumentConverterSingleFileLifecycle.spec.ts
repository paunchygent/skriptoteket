/** Single-file pending and malformed job results. */
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { fileApiMocks, setupSingleFileView } from "./documentConverterSingleFileView.test-support";
import DocumentConverterView from "./DocumentConverterView.vue";

describe("Single-file pending and malformed job results", () => {
  setupSingleFileView();

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

  it.each([
    {
      artifact: {
        artifact_id: "artifact-null-filename",
        content_type: "application/pdf",
        download_url: null,
        filename: null,
        kind: "converted_document",
        size_bytes: 128,
        source_entry_id: null,
      },
      label: "null",
    },
    {
      artifact: {
        artifact_id: "artifact-missing-filename",
        content_type: "application/pdf",
        download_url: null,
        kind: "converted_document",
        size_bytes: 128,
        source_entry_id: null,
      },
      label: "missing",
    },
  ])("fails closed without showing job ids when a succeeded result has $label filename", async ({ artifact, label }) => {
    const jobId = `job-${label}-filename`;
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "lektion.html",
          job_id: jobId,
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "succeeded",
        },
      ],
    });
    fileApiMocks.getDocumentConverterJobStatus.mockResolvedValue({
      error: null,
      job_id: jobId,
      result_artifact: artifact,
      status: "succeeded",
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

    expect(wrapper.text()).toContain("Konverteringen kunde inte slutföras.");
    expect(wrapper.text()).not.toContain(jobId);
    expect(wrapper.text()).not.toContain(artifact.artifact_id);
  });

});
