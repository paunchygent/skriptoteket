/** Single-file upload ordering and removal. */
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { fileApiMocks, setupSingleFileView } from "./documentConverterSingleFileView.test-support";
import DocumentConverterView from "./DocumentConverterView.vue";

describe("Single-file upload ordering and removal", () => {
  setupSingleFileView();

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

  it("removes local upload files from the visible list before submission", async () => {
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
      jobs: [
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
    fileApiMocks.getDocumentConverterJobStatus.mockResolvedValue({
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
      filename: "forsta.pdf",
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

    expect(wrapper.text()).toContain("1. forsta.html");
    expect(wrapper.text()).toContain("2. andra.html");

    await wrapper.get('[data-testid="document-converter-source-remove-1"]').trigger("click");

    expect(wrapper.text()).toContain("1. forsta.html");
    expect(wrapper.text()).not.toContain("andra.html");

    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();

    expect(fileApiMocks.submitDocumentConverterUploadJob).toHaveBeenCalledWith({
      files: [firstFile],
      outputFormat: "pdf",
      sourceFormat: "html",
    });
  });

});
