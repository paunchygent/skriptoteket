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
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExamConverterAuthenticatedView from "./ExamConverterAuthenticatedView.vue";

const routeMocks = vi.hoisted(() => ({
  route: {
    query: {},
  },
  router: {
    replace: vi.fn(),
  },
}));

vi.mock("vue-router", () => ({
  useRoute: () => routeMocks.route,
  useRouter: () => routeMocks.router,
}));

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

beforeEach(() => {
  routeMocks.route.query = {};
  routeMocks.router.replace.mockReset();
  routeMocks.router.replace.mockResolvedValue(undefined);
});

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

    expect(wrapper.find('[data-test="conversion-hub-mode-exam"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="conversion-hub-mode-transcript"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-host-frame"]').attributes("aria-label")).toBe(
      "Provhantering",
    );
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
    expect(workspace.text()).toContain("Dra hit .dxe-filen eller välj provfilen här.");
    expect(workspace.text()).toContain("Endast en .dxe-fil kan användas här.");
    expect(text).toContain("Provfil");
    expect(text).toContain("Välj en .dxe-fil för att fortsätta.");
    expect(text).toContain("Konvertera");
    expect(text).not.toContain("Valfritt rättat prov");
    expect(text).not.toContain("Välj fil (.pdf)");
    expect(text).not.toContain("Målfiler");
    expect(text).not.toContain("QTI-format");
    expect(wrapper.html()).not.toContain("lucide-help-circle");
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
    expect(wrapper.text()).toContain(
      "Det gick inte att använda filen. Välj en .dxe-fil från Exam.net.",
    );
    expect(wrapper.text()).toContain("Välj en .dxe-fil för att fortsätta.");
    expect(wrapper.text()).not.toContain("Konverterar provet");
  });

  it("preserves the current .dxe when an invalid picker replacement is attempted", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );
    await chooseSourceFile(
      wrapper,
      new File(["pdf"], "Ma1c_HT25_Rattat_prov.pdf", {
        type: "application/pdf",
      }),
    );

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_NationelltProv_HT25.dxe");

    await chooseSourceFile(
      wrapper,
      new File(
        ["docx"],
        "Ma1c_HT25_Stodmaterial.docx",
        {
          type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
      ),
    );

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_NationelltProv_HT25.dxe");
    expect(
      wrapper.find('[data-test="exam-converter-start-conversion"]').attributes("disabled"),
    ).toBeUndefined();
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
    expect(wrapper.text()).toContain("Välj en .dxe-fil för att fortsätta.");
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

  it("keeps supporting upload controls out of the authenticated rail", () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    expect(wrapper.find('[data-test="exam-converter-supporting-file-input"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-converter-supporting-file-state"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-converter-target-pdf"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-converter-target-qti"]').exists()).toBe(false);
  });

  it("accepts a dropped .dxe while ignoring extra files instead of treating them as supporting input", async () => {
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
    expect(wrapper.text()).toContain("Ma1c_NationelltProv_HT25.dxe");
    expect(wrapper.text()).not.toContain("Ma1c_HT25_Rattat_prov.pdf");
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

  it("preserves the current .dxe when an ambiguous multi-DXE replacement is dropped", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await chooseSourceFile(
      wrapper,
      new File(["exam"], "Ma1c_NationelltProv_HT25.dxe", {
        type: "application/octet-stream",
      }),
    );

    await dropFiles(wrapper, [
      new File(["exam"], "Prov_A.dxe", {
        type: "application/octet-stream",
      }),
      new File(["exam"], "Prov_B.dxe", {
        type: "application/octet-stream",
      }),
    ]);

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      true,
    );
    expect(wrapper.text()).toContain("Ma1c_NationelltProv_HT25.dxe");
    expect(
      wrapper.find('[data-test="exam-converter-start-conversion"]').attributes("disabled"),
    ).toBeUndefined();
  });

  it("shows source-file guidance when a dropped PDF cannot be used", async () => {
    const wrapper = mount(ExamConverterAuthenticatedView);

    await dropFiles(wrapper, [
      new File(["answers"], "Ma1c_HT25_Rattat_prov.pdf", {
        type: "application/pdf",
      }),
    ]);

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      false,
    );
    expect(wrapper.text()).toContain(
      "Det gick inte att använda filen. Välj en .dxe-fil från Exam.net.",
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
    await wrapper.find("button.btn-ghost").trigger("click");

    expect(wrapper.find('[data-test="exam-converter-selected-source-file"]').exists()).toBe(
      false,
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
