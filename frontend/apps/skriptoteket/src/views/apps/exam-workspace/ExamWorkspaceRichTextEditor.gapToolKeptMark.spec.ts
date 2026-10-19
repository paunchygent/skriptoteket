/**
 * Exam workspace rich-text editor: the kept-word decoration.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 item 4, unit H4):
 *   With the gap tool on, a word carrying a kept link shows a faint dotted
 *   underline and the tooltip `Har sparade svar för en lucka`; with the tool
 *   off it looks like plain text.
 *
 * jsdom has no layout, so the spec reads the editor DOM ProseMirror renders
 * for its inline decorations.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { NativeExamBodySegment } from "../../../api/examWorkspace";
import { paragraph } from "./ExamWorkspaceRichTextEditor.specSupport";
import { closeGapToolEditors, openEditor } from "./ExamWorkspaceRichTextEditor.gapTool.specSupport";

function keptText(value: string, keptGapId: string): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: keptGapId };
}

function plainText(value: string): NativeExamBodySegment {
  return { kind: "text", marks: [], text: value, kept_gap_id: null };
}

const KEPT_TOOLTIP = "Har sparade svar för en lucka";

describe("ExamWorkspaceRichTextEditor kept-word decoration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    closeGapToolEditors();
  });

  it("with the tool on, a kept word shows the dotted underline and tooltip", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });

    const marked = opened.surface.querySelector(".xw-kept-gap");
    expect(marked).not.toBeNull();
    expect(marked?.textContent).toBe("Stockholm");
    expect(marked?.getAttribute("title")).toBe(KEPT_TOOLTIP);
  });

  it("with the tool off, a kept word looks like plain text", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
    });

    expect(opened.surface.querySelector(".xw-kept-gap")).toBeNull();
    expect(opened.surface.getAttribute("title")).toBeNull();
    expect(opened.editor.getText()).toBe("Hon heter Stockholm idag.");
  });

  it("switching the tool off removes the decoration and switching it on brings it back", async () => {
    const opened = await openEditor({
      body: [paragraph(plainText("Hon heter "), keptText("Stockholm", "gap_003"), plainText(" idag."))],
      gapsInteractive: true,
      nextGapId: "gap_004",
      gapTool: true,
    });
    expect(opened.surface.querySelector(".xw-kept-gap")).not.toBeNull();

    await opened.setProps({ gapTool: false });
    await nextTick();
    expect(opened.surface.querySelector(".xw-kept-gap")).toBeNull();

    await opened.setProps({ gapTool: true });
    await nextTick();
    const marked = opened.surface.querySelector(".xw-kept-gap");
    expect(marked).not.toBeNull();
    expect(marked?.getAttribute("title")).toBe(KEPT_TOOLTIP);
  });
});
