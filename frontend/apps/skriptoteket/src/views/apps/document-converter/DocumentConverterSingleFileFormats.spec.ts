/** Single-file source and export format selection. */
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { fileApiMocks, setupSingleFileView } from "./documentConverterSingleFileView.test-support";
import DocumentConverterView from "./DocumentConverterView.vue";

describe("Single-file source and export format selection", () => {
  setupSingleFileView();

  it("infers the single-file source format from local picker files before submission", async () => {
    fileApiMocks.listDocumentConverterSingleFileRoutes.mockResolvedValue({
      routes: [
        {
          output_format: "pdf",
          source_format: "html",
          title: "HTML -> PDF",
        },
        {
          output_format: "md",
          source_format: "pdf",
          title: "PDF -> Markdown",
        },
      ],
    });
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "tom.pdf",
          job_id: "job-pdf",
          producer: "sir_convert",
          producer_reason: "heavy_pdf",
          status: "succeeded",
        },
      ],
    });
    fileApiMocks.getDocumentConverterJobStatus.mockResolvedValue({
      error: null,
      job_id: "job-pdf",
      result_artifact: {
        artifact_id: "artifact-md",
        content_type: "text/markdown",
        download_url: null,
        filename: "tom.md",
        kind: "converted_document",
        size_bytes: 128,
        source_entry_id: null,
      },
      status: "succeeded",
    });

    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
    expect(input.attributes("accept")).toContain(".pdf");
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [new File(["%PDF"], "tom.pdf", { type: "application/pdf" })],
    });
    await input.trigger("change");
    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();

    expect(fileApiMocks.submitDocumentConverterUploadJob).toHaveBeenCalledWith({
      files: [expect.objectContaining({ name: "tom.pdf" })],
      outputFormat: "md",
      sourceFormat: "pdf",
    });
    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    expect(
      operationsColumn.get<HTMLInputElement>('[data-testid="document-converter-filename-stem"]')
        .element.value,
    ).toBe("tom");
    expect(operationsColumn.text()).toContain(".md");
  });

  it("updates the output format when a replacement upload infers another source route", async () => {
    fileApiMocks.listDocumentConverterSingleFileRoutes.mockResolvedValue({
      routes: [
        {
          output_format: "pdf",
          source_format: "html",
          title: "HTML -> PDF",
        },
        {
          output_format: "md",
          source_format: "pdf",
          title: "PDF -> Markdown",
        },
      ],
    });
    fileApiMocks.submitDocumentConverterUploadJob.mockResolvedValue({
      jobs: [
        {
          error: null,
          input_filename: "single-file-proof.html",
          job_id: "job-html",
          producer: "local",
          producer_reason: "local_html_to_pdf",
          status: "succeeded",
        },
      ],
    });
    fileApiMocks.getDocumentConverterJobStatus.mockResolvedValue({
      error: null,
      job_id: "job-html",
      result_artifact: {
        artifact_id: "artifact-html",
        content_type: "application/pdf",
        download_url: null,
        filename: "single-file-proof.pdf",
        kind: "converted_document",
        size_bytes: 128,
        source_entry_id: null,
      },
      status: "succeeded",
    });

    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [new File(["%PDF"], "tom.pdf", { type: "application/pdf" })],
    });
    await input.trigger("change");

    expect(wrapper.get('[data-test="document-converter-source-pdf"]').attributes("aria-checked")).toBe(
      "true",
    );
    expect(wrapper.get('[data-test="document-converter-output-md"]').attributes("aria-checked")).toBe(
      "true",
    );

    const htmlFile = new File(["<h1>Proof</h1>"], "single-file-proof.html", {
      type: "text/html",
    });
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [htmlFile],
    });
    await input.trigger("change");

    expect(wrapper.get('[data-test="document-converter-source-html"]').attributes("aria-checked")).toBe(
      "true",
    );
    expect(wrapper.get('[data-test="document-converter-output-pdf"]').attributes("aria-checked")).toBe(
      "true",
    );

    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();

    expect(fileApiMocks.submitDocumentConverterUploadJob).toHaveBeenCalledWith({
      files: [htmlFile],
      outputFormat: "pdf",
      sourceFormat: "html",
    });
  });

  it("clears stale local uploads when replacement selections are unsupported or mixed", async () => {
    fileApiMocks.listDocumentConverterSingleFileRoutes.mockResolvedValue({
      routes: [
        {
          output_format: "pdf",
          source_format: "html",
          title: "HTML -> PDF",
        },
        {
          output_format: "md",
          source_format: "pdf",
          title: "PDF -> Markdown",
        },
      ],
    });

    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>('[data-testid="document-converter-single-file-input"]');
    const htmlFile = new File(["<h1>Hej</h1>"], "lektion.html", { type: "text/html" });
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [htmlFile],
    });
    await input.trigger("change");

    expect(wrapper.text()).toContain("1. lektion.html");

    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [new File(["text"], "anteckning.txt", { type: "text/plain" })],
    });
    await input.trigger("change");

    expect(wrapper.text()).toContain("Filformatet stöds inte.");
    expect(wrapper.text()).not.toContain("lektion.html");
    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();
    expect(fileApiMocks.submitDocumentConverterUploadJob).not.toHaveBeenCalled();

    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [htmlFile],
    });
    await input.trigger("change");
    expect(wrapper.text()).toContain("1. lektion.html");

    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [htmlFile, new File(["text"], "anteckning.txt", { type: "text/plain" })],
    });
    await input.trigger("change");

    expect(wrapper.text()).toContain("Filformatet stöds inte.");
    expect(wrapper.text()).not.toContain("lektion.html");
    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();
    expect(fileApiMocks.submitDocumentConverterUploadJob).not.toHaveBeenCalled();

    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [htmlFile],
    });
    await input.trigger("change");
    expect(wrapper.text()).toContain("1. lektion.html");

    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [htmlFile, new File(["%PDF"], "tom.pdf", { type: "application/pdf" })],
    });
    await input.trigger("change");

    expect(wrapper.text()).toContain("Välj filer med samma källformat.");
    expect(wrapper.text()).not.toContain("lektion.html");
    await wrapper.get('[data-testid="document-converter-start-single-file"]').trigger("click");
    await flushPromises();
    expect(fileApiMocks.submitDocumentConverterUploadJob).not.toHaveBeenCalled();
  });

});
