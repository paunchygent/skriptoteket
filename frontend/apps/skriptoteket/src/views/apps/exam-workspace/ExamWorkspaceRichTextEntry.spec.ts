/**
 * Exam workspace rich text entry.
 *
 * Expected behavior:
 *   One choice, matching entry, ordering step or part instruction edits on the
 *   shared editor like a word processor: a selection across paragraphs
 *   deletes, Backspace merges, Enter starts a paragraph and Shift+Enter breaks
 *   the line. An edit emits the whole body and keeps the marks of the text it
 *   edits, clearing the text emits the empty body and keeps it, a disabled
 *   entry is not editable and emits nothing, and a stored picture renders and
 *   stays.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamBodySegment } from "../../../api/examWorkspace";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import {
  editorBehind,
  posIn,
  press,
  selectText,
  settleEditors,
  surfaceOf,
} from "./ExamWorkspaceRichTextEntry.specSupport";

const TEST_ID = "entry";

type Body = NativeExamBodyParagraph[];

function text(value: string, marks: Array<"bold" | "italic"> = []): NativeExamBodySegment {
  return { kind: "text", text: value, marks };
}
function paragraph(...segments: NativeExamBodySegment[]): NativeExamBodyParagraph {
  return { heading_level: null, segments };
}

let mounted: VueWrapper | null = null;

async function mountEntry(
  body: Body,
  props: Record<string, unknown> = {},
): Promise<VueWrapper> {
  mounted = mount(ExamWorkspaceRichTextEntry, {
    attachTo: document.body,
    props: { body, label: "Text för svarsalternativ A", testId: TEST_ID, ...props },
  });
  await settleEditors();
  return mounted;
}

function bodies(wrapper: VueWrapper): Body[] {
  return (wrapper.emitted("updateBody") ?? []).map((args) => args[0] as Body);
}

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
});

describe("ExamWorkspaceRichTextEntry", () => {
  it("emits the body keeping the mark of the edited text", async () => {
    const wrapper = await mountEntry([paragraph(text("Syre", ["italic"]), text(" och kväve"))]);
    const editor = editorBehind(wrapper, TEST_ID);

    editor.commands.setTextSelection(posIn(editor, "Syre", 4));
    editor.commands.insertContent("gas");

    expect(bodies(wrapper).at(-1)).toEqual([
      paragraph(text("Syregas", ["italic"]), text(" och kväve")),
    ]);
  });

  describe("word-processor editing", () => {
    const TWO = [paragraph(text("första")), paragraph(text("andra"))];

    it("deletes a selection across two paragraphs with Backspace and merges them", async () => {
      const wrapper = await mountEntry(TWO);
      const editor = editorBehind(wrapper, TEST_ID);
      editor.commands.setTextSelection({
        from: posIn(editor, "första", 3),
        to: posIn(editor, "andra", 2),
      });

      press(surfaceOf(wrapper, TEST_ID), "Backspace");

      expect(bodies(wrapper)).toEqual([[paragraph(text("fördra"))]]);
    });

    it("merges a paragraph into the one before it with Backspace at its start", async () => {
      const wrapper = await mountEntry(TWO);
      const editor = editorBehind(wrapper, TEST_ID);
      editor.commands.setTextSelection(posIn(editor, "andra", 0));

      press(surfaceOf(wrapper, TEST_ID), "Backspace");

      expect(bodies(wrapper).at(-1)).toEqual([paragraph(text("förstaandra"))]);
    });

    it("starts a new paragraph on Enter", async () => {
      const wrapper = await mountEntry([paragraph(text("abcd"))]);
      const editor = editorBehind(wrapper, TEST_ID);
      editor.commands.setTextSelection(posIn(editor, "abcd", 2));

      press(surfaceOf(wrapper, TEST_ID), "Enter");

      expect(bodies(wrapper)).toEqual([[paragraph(text("ab")), paragraph(text("cd"))]]);
    });

    it("breaks the line inside the paragraph on Shift+Enter", async () => {
      const wrapper = await mountEntry([paragraph(text("abcd"))]);
      const editor = editorBehind(wrapper, TEST_ID);
      editor.commands.setTextSelection(posIn(editor, "abcd", 2));

      press(surfaceOf(wrapper, TEST_ID), "Enter", { shiftKey: true });

      expect(bodies(wrapper)).toEqual([[paragraph(text("ab\ncd"))]]);
    });

    it("emits the empty body when the text is cleared and keeps it empty", async () => {
      const wrapper = await mountEntry(TWO);
      const editor = editorBehind(wrapper, TEST_ID);
      editor.commands.selectAll();

      press(surfaceOf(wrapper, TEST_ID), "Backspace");
      expect(bodies(wrapper)).toEqual([[]]);

      // The owner stores the empty body; the entry neither restores text nor emits again.
      await wrapper.setProps({ body: [] });
      surfaceOf(wrapper, TEST_ID).blur();
      await nextTick();
      expect(editor.getText()).toBe("");
      expect(bodies(wrapper)).toEqual([[]]);
    });
  });

  it("tells the item editor when the entry takes focus", async () => {
    const wrapper = await mountEntry([paragraph(text("Syre"))]);

    surfaceOf(wrapper, TEST_ID).focus();

    expect(wrapper.emitted("focusEntry")).toHaveLength(1);
  });

  it("carries the label, the invalid state and the description on the editing surface", async () => {
    const wrapper = await mountEntry([paragraph(text("Syre"))], { invalid: true, describedBy: "hint-1" });
    const surface = surfaceOf(wrapper, TEST_ID);

    expect(surface.getAttribute("aria-label")).toBe("Text för svarsalternativ A");
    expect(surface.getAttribute("aria-invalid")).toBe("true");
    expect(surface.getAttribute("aria-describedby")).toBe("hint-1");
    expect(surface.getAttribute("contenteditable")).toBe("true");

    await wrapper.setProps({ invalid: false, describedBy: undefined });
    expect(surface.hasAttribute("aria-invalid")).toBe(false);
    expect(surface.hasAttribute("aria-describedby")).toBe(false);
  });

  it("draws the input variant with its own border and the paragraph variant without", async () => {
    const input = await mountEntry([paragraph(text("Syre"))], { borderClass: "border-success" });
    expect(input.classes()).toContain("border-success");
    input.unmount();

    const flowing = await mountEntry([paragraph(text("Syre"))], { variant: "paragraph" });
    expect(flowing.classes()).not.toContain("border");
    expect(flowing.classes()).not.toContain("xw-richtext--compact");
  });

  describe("while disabled", () => {
    it("is not editable and emits nothing", async () => {
      const wrapper = await mountEntry([paragraph(text("Syre"))], { disabled: true });
      const editor = editorBehind(wrapper, TEST_ID);

      expect(surfaceOf(wrapper, TEST_ID).getAttribute("contenteditable")).toBe("false");
      editor.commands.selectAll();
      press(surfaceOf(wrapper, TEST_ID), "Backspace");
      editor.commands.insertContent("x");

      expect(wrapper.emitted("updateBody")).toBeUndefined();
    });

    it("becomes editable again when the lock lifts", async () => {
      const wrapper = await mountEntry([paragraph(text("Syre"))], { disabled: true });

      await wrapper.setProps({ disabled: false });

      expect(surfaceOf(wrapper, TEST_ID).getAttribute("contenteditable")).toBe("true");
    });
  });

  describe("pictures", () => {
    const body: Body = [paragraph(text("Se "), { kind: "asset", asset_id: "asset_001" })];
    const url = "https://gateway.test/assets/asset_001";

    it("renders a mapped picture inside the fixed atom", async () => {
      const wrapper = await mountEntry(body, { assetUrls: { asset_001: url } });

      expect(wrapper.get('[data-asset-id="asset_001"] img').attributes("src")).toBe(url);
    });

    it("keeps the placeholder without a mapped URL", async () => {
      const wrapper = await mountEntry(body);

      // ProseMirror appends its own separator <img> after a trailing atom.
      expect(wrapper.find("img.xw-picture__image").exists()).toBe(false);
      expect(wrapper.find('[data-asset-id="asset_001"]').exists()).toBe(true);
    });

    it("keeps the picture when only the text is edited", async () => {
      const wrapper = await mountEntry(body, { assetUrls: { asset_001: url } });
      const editor = editorBehind(wrapper, TEST_ID);

      selectText(editor, "Se ", 1, 3);
      press(surfaceOf(wrapper, TEST_ID), "Backspace");

      expect(bodies(wrapper).at(-1)).toEqual([
        paragraph(text("S"), { kind: "asset", asset_id: "asset_001" }),
      ]);
    });
  });
});
