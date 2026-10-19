/**
 * Exam workspace header structure (TASK-SKRIPT-40-04-17, T2, T5, T6).
 *
 * Expected behavior:
 *   The header reads title block, Öppna, Spara som …, Exportera, Importera,
 *   a separator, PDF, the AI glyph and the status slot. Spara som … and
 *   Importera emit their intents directly, PDF is a pressed toggle, the
 *   course and points line opens Provets detaljer, and neither Ångra nor Gör
 *   om is in the header.
 */

import { describe, expect, it } from "vitest";

import { mountHeader } from "./ExamWorkspaceHeader.specSupport";

describe("ExamWorkspaceHeader layout", () => {
  it("keeps the order title, meta, Öppna, Spara som, Exportera, Importera, PDF, AI, status", () => {
    const wrapper = mountHeader();
    const order = [
      "exam-workspace-title", "exam-workspace-rename", "exam-workspace-details",
      "exam-workspace-open", "exam-workspace-save-as-command", "exam-workspace-export",
      "exam-workspace-import", "exam-workspace-print-preview-toggle", "exam-workspace-suggest-all",
      "exam-workspace-save-state",
    ];
    const ids = wrapper.findAll("[data-test]").map((element) => element.attributes("data-test"));
    expect(ids.filter((id) => order.includes(id ?? ""))).toEqual(order);
    wrapper.unmount();
  });

  it("has no Ångra, no Gör om and no Spara button in the header", () => {
    const wrapper = mountHeader();
    expect(wrapper.find('[data-test="exam-workspace-undo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-redo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-save"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-save-menu"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("puts a separator between the file commands and PDF", () => {
    const wrapper = mountHeader();
    const separator = wrapper.get(".xw-toolsep").element;
    const pdf = wrapper.get('[data-test="exam-workspace-print-preview-toggle"]').element;
    const importButton = wrapper.get('[data-test="exam-workspace-import"]').element;
    expect(importButton.compareDocumentPosition(separator) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(separator.compareDocumentPosition(pdf) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    wrapper.unmount();
  });

  it("emits saveAs from the Spara som … command and keeps its canSaveAs gate", async () => {
    const wrapper = mountHeader();
    const button = wrapper.get('[data-test="exam-workspace-save-as-command"]');
    expect(button.attributes("aria-label")).toBe("Spara som …");
    expect(button.attributes("title")).toBe("Spara som …");
    expect(button.text()).toBe("Spara som");
    await button.trigger("click");
    expect(wrapper.emitted("saveAs")).toHaveLength(1);
    wrapper.unmount();

    const gated = mountHeader({ canSaveAs: false });
    expect(gated.get('[data-test="exam-workspace-save-as-command"]').attributes("disabled")).toBeDefined();
    gated.unmount();
  });

  it("emits importFile from Importera", async () => {
    const wrapper = mountHeader();
    const button = wrapper.get('[data-test="exam-workspace-import"]');
    expect(button.attributes("title")).toBe("Importera prov");
    expect(button.text()).toBe("Importera");
    await button.trigger("click");
    expect(wrapper.emitted("importFile")).toHaveLength(1);
    wrapper.unmount();
  });

  it("emits toggleOpen from Öppna", async () => {
    const wrapper = mountHeader();
    await wrapper.get('[data-test="exam-workspace-open"]').trigger("click");
    expect(wrapper.emitted("toggleOpen")).toHaveLength(1);
    wrapper.unmount();
  });

  it("shows PDF as a pressed toggle that follows the preview state", async () => {
    const closed = mountHeader({ previewOpen: false });
    const button = closed.get('[data-test="exam-workspace-print-preview-toggle"]');
    expect(button.text()).toBe("PDF");
    expect(button.attributes("aria-label")).toBe("Förhandsgranska PDF");
    expect(button.attributes("title")).toBe("Förhandsgranska PDF");
    expect(button.attributes("aria-pressed")).toBe("false");
    await button.trigger("click");
    expect(closed.emitted("togglePreview")).toHaveLength(1);
    closed.unmount();

    const open = mountHeader({ previewOpen: true });
    expect(open.get('[data-test="exam-workspace-print-preview-toggle"]').attributes("aria-pressed")).toBe("true");
    open.unmount();
  });

  it("opens the details from the course and points line, not from the title", async () => {
    const wrapper = mountHeader({ courseLabel: "Svenska 1", total: 24 });
    const meta = wrapper.get('[data-test="exam-workspace-details"]');
    expect(meta.text()).toBe("Svenska 1 · 24 p");
    expect(meta.attributes("title")).toBe("Provets detaljer");

    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
    expect(wrapper.emitted("toggleDetails")).toBeUndefined();

    await meta.trigger("click");
    expect(wrapper.emitted("toggleDetails")).toHaveLength(1);
    wrapper.unmount();
  });

  it("shows Utan kurs when the exam has no course", () => {
    const wrapper = mountHeader({ courseLabel: null, total: 0 });
    expect(wrapper.get('[data-test="exam-workspace-details"]').text()).toBe("Utan kurs · 0 p");
    wrapper.unmount();
  });
});
