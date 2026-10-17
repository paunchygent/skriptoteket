/** Single-file result ownership and mode isolation. */
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { fileApiMocks, mountReadySingleFileResult, setupSingleFileView } from "./documentConverterSingleFileView.test-support";
import DocumentConverterView from "./DocumentConverterView.vue";

describe("Single-file result ownership and mode isolation", () => {
  setupSingleFileView();

  it("shows file conversion as a tabbed mode without visible history or raw ids", async () => {
    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();
    const text = wrapper.text();

    expect(wrapper.get('[role="tablist"]').attributes("aria-label")).toBe("Välj arbetsyta");
    expect(text).toContain("Filkonvertering");
    expect(text).toContain("HTML/CSS-projekt");
    expect(text).toContain("Lokal fil");
    expect(text).toContain("Mina filer");
    expect(text).toContain("Källformat");
    expect(text).toContain("Exportformat");
    expect(text).not.toContain("HTML till PDF");
    expect(text).not.toContain("Filoperationer");
    expect(text).not.toContain("HTML/CSS-projekt till PDF");
    expect(text).not.toContain("Automatisk förhandsvisning");
    expect(text).toContain("Välj en fil som du vill konvertera");
    expect(text).not.toContain("HTML -> PDF");
    expect(text).not.toContain("En fil");
    expect(text).not.toContain("Arbetssätt");
    expect(text).not.toContain("Aktuell källa");
    expect(text).not.toContain("Historik");
    expect(text).not.toContain("Inget resultat än");
    expect(text).not.toContain("preview-");
    expect(text).not.toContain("artifact-");
  });

  it("uses the same source operations preview ownership for single-file conversion", async () => {
    const wrapper = mount(DocumentConverterView);
    await wrapper.get('[data-test="document-converter-mode-single"]').trigger("click");
    await flushPromises();

    const sourceColumn = wrapper.get('[data-testid="document-converter-source-column"]');
    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const previewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(sourceColumn.find('[data-testid="document-converter-single-file-input"]').exists()).toBe(
      true,
    );
    expect(sourceColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      false,
    );

    expect(operationsColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      true,
    );
    expect(operationsColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      true,
    );
    expect(operationsColumn.find('[data-testid="document-converter-download"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-save"]').exists()).toBe(true);

    expect(previewColumn.find('[data-testid="document-converter-single-file-input"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-download"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-save"]').exists()).toBe(false);
  });

  it("keeps a succeeded single-file result in the same source operations preview columns without leaking into project mode", async () => {
    const wrapper = await mountReadySingleFileResult();

    const sourceColumn = wrapper.get('[data-testid="document-converter-source-column"]');
    const operationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const previewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(fileApiMocks.getDocumentConverterJobStatus).toHaveBeenCalledWith({ jobId: "job-ready" });
    expect(sourceColumn.find('[data-testid="document-converter-single-file-input"]').exists()).toBe(
      true,
    );
    expect(sourceColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      false,
    );
    expect(sourceColumn.text()).toContain("1. lektion.html");

    expect(operationsColumn.find('[data-testid="document-converter-start-single-file"]').exists()).toBe(
      true,
    );
    expect(
      operationsColumn.get<HTMLInputElement>('[data-testid="document-converter-filename-stem"]')
        .element.value,
    ).toBe("lektion");
    expect(operationsColumn.text()).toContain(".pdf");
    expect(operationsColumn.find('[data-testid="document-converter-download"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-save"]').exists()).toBe(true);
    expect(operationsColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );

    expect(previewColumn.find('[data-testid="document-converter-pdf-frame"]').exists()).toBe(true);
    expect(previewColumn.text()).not.toContain("lektion.pdf");
    expect(previewColumn.find('[data-testid="document-converter-filename-stem"]').exists()).toBe(
      false,
    );
    expect(previewColumn.find('[data-testid="document-converter-download"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-save"]').exists()).toBe(false);
    expect(previewColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );

    expect(
      operationsColumn.get<HTMLInputElement>('[data-testid="document-converter-filename-stem"]')
        .element.value,
    ).toBe("lektion");
    expect(operationsColumn.text()).toContain(".pdf");
    expect(wrapper.text()).not.toContain("Misslyckades");
    expect(wrapper.text()).not.toContain("Konverteringen kunde inte slutföras.");
    expect(wrapper.text()).not.toContain("Historik");

    await wrapper.get('[data-test="document-converter-mode-project"]').trigger("click");
    await flushPromises();

    const projectOperationsColumn = wrapper.get('[data-testid="document-converter-operations-column"]');
    const projectPreviewColumn = wrapper.get('[data-testid="document-converter-preview-column"]');

    expect(wrapper.text()).not.toContain("lektion.pdf");
    expect(projectOperationsColumn.text()).toContain("Lägg till HTML, CSS och bilder.");
    expect(projectOperationsColumn.find('[data-testid="document-converter-artifact-selector"]').exists()).toBe(
      false,
    );
    expect(projectOperationsColumn.get('[data-testid="document-converter-download"]').attributes("disabled")).toBe(
      "",
    );
    expect(projectOperationsColumn.get('[data-testid="document-converter-save"]').attributes("disabled")).toBe(
      "",
    );
    expect(projectPreviewColumn.find('[data-testid="document-converter-pdf-frame"]').exists()).toBe(false);
    expect(projectPreviewColumn.text()).toContain("Förhandsvisning");
    expect(projectPreviewColumn.text()).not.toContain("Lägg till HTML, CSS och bilder.");
  });
});
