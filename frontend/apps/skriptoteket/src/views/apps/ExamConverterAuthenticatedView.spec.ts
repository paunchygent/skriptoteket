/**
 * Exam Converter authenticated host-frame behavior.
 *
 * Slice purpose:
 *   Provide the stable authenticated app frame and source-file intake shell for
 *   Exam Converter before conversion, results, files, questions, reports, or
 *   save behavior is introduced.
 *
 * Expected behavior:
 *   The authenticated app host renders a two-zone workspace: a compact left
 *   setup rail and a dominant right workspace shell with the idle `.dxe` drop
 *   zone. It must not render conversion results, file rows, question rows,
 *   report content, runtime controls, or service jargon in this slice.
 *
 * Recommended implementation shape:
 *   Keep `ExamConverterAuthenticatedView` as a composition component and
 *   delegate the left and right structural regions to small presentational
 *   shell components. Runtime clients and conversion state stay out of this
 *   slice.
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
    expect(workspace.text()).toContain("Dra hit .dxe-filen eller välj fil från datorn");
    expect(text).toContain("Provfil");
    expect(text).toContain("Ingen fil vald");
    expect(text).toContain("Valfri resultat-PDF");
    expect(text).toContain("För svarsmall");
    expect(text).toContain("Målfiler");
    expect(text).toContain("PDF");
    expect(text).toContain("QTI-format");
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
