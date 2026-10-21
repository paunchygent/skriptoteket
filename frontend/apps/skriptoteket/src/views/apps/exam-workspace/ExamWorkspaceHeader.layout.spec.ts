/**
 * Exam workspace header structure (TASK-SKRIPT-40-04-17, T2, T5, T6).
 *
 * Expected behavior:
 *   The header reads title block, Uppgifter, a separator, Nytt prov, Öppna,
 *   Spara som …, Exportera, Importera, a separator, PDF, the AI glyph and the
 *   status slot.
 *   Uppgifter opens Provets uppgifter and is the only way in from the header;
 *   the course and points line is plain text. Nytt prov, Spara som … and
 *   Importera emit their intents directly, PDF is a pressed toggle, and
 *   neither Ångra nor Gör om is in the header.
 */

import { describe, expect, it } from "vitest";

import { mountHeader } from "./ExamWorkspaceHeader.specSupport";

describe("ExamWorkspaceHeader layout", () => {
  it("keeps the order title, meta, Uppgifter, Nytt prov, Öppna, Spara som, Exportera, Importera, PDF, AI, status", () => {
    const wrapper = mountHeader();
    const order = [
      "exam-workspace-title", "exam-workspace-rename", "exam-workspace-meta", "exam-workspace-details",
      "exam-workspace-new", "exam-workspace-open", "exam-workspace-save-as-command", "exam-workspace-export",
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
    const separators = wrapper.findAll(".xw-toolsep");
    expect(separators).toHaveLength(2);
    const separator = separators[1].element;
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

  it("opens Provets uppgifter from the first toolbar command, not from the title or the meta line", async () => {
    const closed = mountHeader({ courseLabel: "Svenska 1", total: 24, detailsOpen: false });
    const command = closed.get('[data-test="exam-workspace-details"]');
    expect(closed.get('[role="toolbar"]').find("button").element).toBe(command.element);
    expect(command.element.nextElementSibling?.classList.contains("xw-toolsep")).toBe(true);
    expect(command.element.nextElementSibling?.nextElementSibling).toBe(closed.get('[data-test="exam-workspace-new"]').element);
    expect(command.text()).toBe("Uppgifter");
    expect(command.attributes("title")).toBe("Provets uppgifter");
    expect(command.attributes("aria-label")).toBe("Provets uppgifter");
    expect(command.attributes("aria-haspopup")).toBe("dialog");
    expect(command.attributes("aria-expanded")).toBe("false");

    const meta = closed.get('[data-test="exam-workspace-meta"]');
    expect(meta.element.tagName).not.toBe("BUTTON");
    expect(meta.text()).toBe("Svenska 1 · 24 p");
    await meta.trigger("click");
    await closed.get('[data-test="exam-workspace-title"]').trigger("click");
    expect(closed.emitted("toggleDetails")).toBeUndefined();

    await command.trigger("click");
    expect(closed.emitted("toggleDetails")).toHaveLength(1);
    closed.unmount();

    const open = mountHeader({ detailsOpen: true });
    expect(open.get('[data-test="exam-workspace-details"]').attributes("aria-expanded")).toBe("true");
    open.unmount();
  });

  it("shows no Uppgifter command or meta line while no exam is open", () => {
    const wrapper = mountHeader({ title: null });
    expect(wrapper.find('[data-test="exam-workspace-details"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-meta"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("shows Utan kurs when the exam has no course", () => {
    const wrapper = mountHeader({ courseLabel: null, total: 0 });
    expect(wrapper.get('[data-test="exam-workspace-meta"]').text()).toBe("Utan kurs · 0 p");
    wrapper.unmount();
  });
});
