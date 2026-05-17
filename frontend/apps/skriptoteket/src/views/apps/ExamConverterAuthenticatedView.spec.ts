/**
 * Exam Converter authenticated host-frame behavior.
 *
 * Slice purpose:
 *   Provide the stable authenticated app frame and browser-local source-file
 *   intake for Exam Converter before upstream runtime, files, questions,
 *   reports, or save behavior is introduced.
 *
 * Expected behavior:
 *   The authenticated app host renders a two-zone workspace: a compact left
 *   setup rail and a dominant right workspace shell with a `.dxe` drop zone.
 *   Selecting a source file updates the rail and workspace locally only. It
 *   must not render file rows, question rows, report content, upstream runtime
 *   details, or service jargon in this slice.
 *
 * Recommended implementation shape:
 *   Keep `ExamConverterAuthenticatedView` as a composition component. Use a
 *   tiny composable for local file selection, and keep runtime clients,
 *   conversion result data, and save behavior out of this slice.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";

const FORBIDDEN_VISIBLE_WORDS = [
  "artefakt",
  "manifest",
  "bundle",
  "runtime",
  "Vault",
  "grant",
  "lease",
  "pipeline",
  "inloggad konvertering",
];

async function chooseFile(wrapper: ReturnType<typeof mount>, selector: string, file: File) {
  const input = wrapper.find<HTMLInputElement>(selector);
  Object.defineProperty(input.element, "files", {
    configurable: true,
    value: [file],
  });
  await input.trigger("change");
}

async function chooseSourceFile(wrapper: ReturnType<typeof mount>, file: File) {
  await chooseFile(wrapper, '[data-test="exam-converter-source-file-input"]', file);
}

async function dropFiles(wrapper: ReturnType<typeof mount>, files: File[]) {
  await wrapper.find('[data-test="exam-converter-source-drop-zone"]').trigger("drop", {
    dataTransfer: { files },
  });
}

describe("ExamConverterAuthenticatedView host frame", () => {
  it("renders the approved two-zone authenticated host frame", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find('[data-test="exam-converter-host-frame"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-workflow-rail-shell"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-workspace-shell"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("Konvertera prov");
    expect(wrapper.text()).toContain("Välj provfil för att börja");
  });

  it("renders the source-file drop zone as the slice-one intake affordance", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const text = wrapper.text();
    const dropZone = wrapper.find('[data-test="exam-converter-source-drop-zone"]');
    const rail = wrapper.find('[data-test="exam-converter-workflow-rail-shell"]');
    const workspace = wrapper.find('[data-test="exam-converter-workspace-shell"]');

    expect(dropZone.exists()).toBe(true);
    expect(workspace.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(true);
    expect(rail.find('[data-test="exam-converter-source-drop-zone"]').exists()).toBe(false);
    expect(dropZone.text()).toContain("Välj provfil");
    expect(workspace.text()).toContain(
      "Dra hit .dxe-filen. Om du har ett rättat prov som PDF kan du dra in båda samtidigt.",
    );
    expect(workspace.text()).toContain(
      ".dxe och rättat prov som PDF kan dras in samtidigt.",
    );
    expect(text).toContain("Provfil");
    expect(text).toContain("Ingen fil vald");
    expect(text).toContain("Valfritt rättat prov");
    expect(text).toContain("Välj fil (.pdf)");
    expect(text).toContain("Kan dras in samtidigt med provfilen.");
    expect(text).toContain("Målfiler");
    expect(text).toContain("PDF");
    expect(text).toContain("QTI-format");
    expect(text).toContain("För lagring och import av digitala prov.");
    expect(text).not.toContain("Exam.net-stöd är planerat");
  });

  it("keeps conversion results, generated files, question review, and report content out of slice one", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const text = wrapper.text();

    expect(text).not.toContain("Konverteringen av provet lyckades delvis");
    expect(text).not.toContain("Konverterade frågor");
    expect(text).not.toContain("Filer klara att hämta");
    expect(text).not.toContain("Öppna rapport");
    expect(text).not.toContain("Spara i mina filer");
  });

  it("updates the rail and workspace when a .dxe source file is selected", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_NationelltProv_HT25.dxe");
    expect(wrapper.text()).toContain("Filen är uppladdad");
    expect(wrapper.text()).toContain("Provfilen är vald");
    expect(wrapper.find('[data-test="exam-converter-source-drop-zone"]').text()).toContain(
      "Ma1c_NationelltProv_HT25.dxe",
    );
    expect(
      wrapper.find('[data-test="exam-converter-start-conversion"]').attributes("disabled"),
    ).toBeUndefined();
  });

  it("rejects non-.dxe files without inventing conversion state", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["pdf"], "Ma1c_HT25_Provblad.pdf", {
        type: "application/pdf",
      }),
    );

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      false,
    );
    expect(wrapper.text()).toContain("Välj en .dxe-fil från Exam.net.");
    expect(wrapper.text()).toContain("Ingen fil vald");
    expect(wrapper.text()).not.toContain("Konverterar provet");
  });

  it("returns to the idle intake state when the selected source file is removed", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await wrapper.find('[data-test="exam-converter-clear-source-file"]').trigger("click");

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      false,
    );
    expect(wrapper.text()).toContain("Välj provfil för att börja");
    expect(wrapper.text()).toContain("Ingen fil vald");
  });

  it("lets the rail source-file action use the same local .dxe intake", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseFile(
      wrapper,
      '[data-test="exam-converter-rail-source-file-input"]',
      new File(["exam"], "Ma1c_Rail_Selected.dxe", {
        type: "application/octet-stream",
      }),
    );

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_Rail_Selected.dxe");
  });

  it("selects, rejects, and removes the optional result-PDF locally", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseFile(
      wrapper,
      '[data-test="exam-converter-supporting-file-input"]',
      new File(["answers"], "Ma1c_HT25_Provblad.pdf", {
        type: "application/pdf",
      }),
    );

    expect(wrapper.find('[data-test="exam-converter-selected-supporting-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_HT25_Provblad.pdf");
    await wrapper.find('[data-test="exam-converter-clear-supporting-file"]').trigger("click");
    expect(wrapper.find('[data-test="exam-converter-selected-supporting-file"]').exists()).toBe(
      false,
    );

    await chooseFile(
      wrapper,
      '[data-test="exam-converter-supporting-file-input"]',
      new File(["word"], "Ma1c_HT25_Provblad.docx", {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      }),
    );

    expect(wrapper.text()).toContain("Välj en PDF-fil för svarsmall.");
  });

  it("announces and supports dropping a .dxe and corrected PDF together", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await dropFiles(wrapper, [
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
      new File(["answers"], "Ma1c_HT25_Rattat_prov.pdf", {
        type: "application/pdf",
      }),
    ]);

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="exam-converter-selected-supporting-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_NationelltProv_HT25.dxe");
    expect(wrapper.text()).toContain("Ma1c_HT25_Rattat_prov.pdf");
  });

  it("keeps single-exam intake explicit when several .dxe files are dropped", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await dropFiles(wrapper, [
      new File(["exam"], "Prov_A.dxe", {
        type: "application/octet-stream",
      }),
      new File(["exam"], "Prov_B.dxe", {
        type: "application/octet-stream",
      }),
    ]);

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      false,
    );
    expect(wrapper.text()).toContain("Välj en provfil åt gången.");
  });

  it("toggles output formats as local true/false choices", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const pdfTarget = wrapper.find('[data-test="exam-converter-target-pdf"]');
    const qtiTarget = wrapper.find('[data-test="exam-converter-target-qti"]');

    expect(pdfTarget.attributes("aria-pressed")).toBe("true");
    expect(qtiTarget.attributes("aria-pressed")).toBe("true");

    await pdfTarget.trigger("click");
    await qtiTarget.trigger("click");

    expect(wrapper.find('[data-test="exam-converter-target-pdf"]').attributes("aria-pressed")).toBe(
      "false",
    );
    expect(wrapper.find('[data-test="exam-converter-target-qti"]').attributes("aria-pressed")).toBe(
      "false",
    );
  });

  it("resets local choices without starting conversion", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await wrapper.find('[data-test="exam-converter-target-pdf"]').trigger("click");
    await wrapper.find("button.btn-ghost").trigger("click");

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-converter-target-pdf"]').attributes("aria-pressed")).toBe(
      "true",
    );
    expect(wrapper.text()).not.toContain("Konverterar provet");
  });

  it("keeps the host frame free of service jargon and flat runtime leakage", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const renderedText = wrapper.text();

    for (const forbiddenWord of FORBIDDEN_VISIBLE_WORDS) {
      expect(renderedText).not.toContain(forbiddenWord);
    }
    expect(renderedText).not.toContain("Ram för inmatning och förhandsval");
    expect(renderedText).not.toContain("kommande slice");
    expect(renderedText).not.toContain("Här placeras nästa godkända del");
    expect(renderedText).not.toContain("Det detaljerade innehållet");
  });

  it("keeps slice-one symbols on approved semantic token colors instead of random step colors", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const railHtml = wrapper
      .find('[data-test="exam-converter-workflow-rail-shell"]')
      .html();

    expect(railHtml).toContain("text-navy");
    expect(railHtml).not.toContain("text-terracotta");
    expect(railHtml).not.toContain("text-success");
    expect(railHtml).not.toContain("text-error");
    expect(railHtml).not.toContain("text-orange");
    expect(railHtml).not.toContain("text-green");
    expect(railHtml).not.toContain("text-blue");
  });

  it("keeps the workspace shell free of decorative status symbols while allowing the file affordance", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const workspaceHtml = wrapper
      .find('[data-test="exam-converter-workspace-shell"]')
      .html();

    expect(workspaceHtml).toContain("lucide-upload");
    expect(workspaceHtml).toContain("text-action");
    expect(workspaceHtml).not.toContain("border-action");
    expect(workspaceHtml).not.toContain("text-success");
    expect(workspaceHtml).not.toContain("text-error");
  });

  it("keeps the intake rail away from uppercase labels and recipe numbering", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const railHtml = wrapper
      .find('[data-test="exam-converter-workflow-rail-shell"]')
      .html();

    expect(railHtml).not.toContain("uppercase");
    expect(railHtml).not.toContain("tracking-[var(--huleedu-tracking-label)]");
    expect(wrapper.text()).not.toContain("PROVFIL");
    expect(wrapper.text()).not.toContain("EXPORTPROFIL");
    expect(wrapper.text()).not.toContain("1. Ladda upp provfil");
    expect(wrapper.text()).not.toContain("2. Lägg till resultat-PDF");
  });

  it("keeps workflow steps free of repetitive divider-line treatment", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);
    const railHtml = wrapper
      .find('[data-test="exam-converter-workflow-rail-shell"]')
      .html();

    expect(railHtml).not.toContain("border-b");
    expect(railHtml).not.toContain("last:border-b");
    expect(railHtml).not.toContain("divide-y");
  });

  it("keeps shell headings in restrained sans typography instead of serif hero styling", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find("#exam-converter-workflow-title").classes()).not.toContain("font-serif");
    expect(wrapper.find("#exam-converter-workflow-title").classes()).toContain("text-base");
    expect(wrapper.find("#exam-converter-auth-title").classes()).not.toContain("font-serif");
    expect(wrapper.find("#exam-converter-auth-title").classes()).toContain("text-lg");
  });
});
