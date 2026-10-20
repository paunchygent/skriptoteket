/**
 * Exam workspace rich-text editor: paragraph space in the full variant.
 *
 * Expected behavior (TASK-SKRIPT-40-04-20 D4):
 *   In the full exam editor, consecutive paragraphs (and headings) sit with
 *   a visible 1rem gap between them, matching the print's 4 mm paragraph
 *   space. The compact variant (choice options and entry fields, wrapper
 *   class `xw-richtext--compact`) stays tight: it keeps no such gap rule.
 *
 * The gap itself is one CSS rule in `ExamWorkspaceRichTextEditor.vue`, so
 * this spec stays behavioural: the full variant shows two paragraphs as two
 * separate paragraph elements inside the labelled textbox, found by their
 * visible text; the compact variant's textbox sits inside the compact
 * wrapper the CSS rule excludes, while the full one does not. The visual
 * proof is the staging walk.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { paragraph, text } from "./ExamWorkspaceRichTextEditor.specSupport";

const LABEL = "Frågetext";

async function mountVariant(variant: "field" | "compact") {
  const wrapper = mount(ExamWorkspaceRichTextEditor, {
    attachTo: document.body,
    props: {
      body: [paragraph(text("first")), paragraph(text("second"))],
      label: LABEL,
      testId: variant === "compact" ? "paragraph-space-compact" : "paragraph-space-full",
      variant,
    },
  });
  await nextTick();
  await nextTick();
  return wrapper;
}

type EditorWrapper = Awaited<ReturnType<typeof mountVariant>>;

/** The editing surface, found by its accessible role and label. */
function textbox(wrapper: EditorWrapper): HTMLElement {
  const surface = wrapper.get(`[role="textbox"][aria-label="${LABEL}"]`).element;
  if (!(surface instanceof HTMLElement)) {
    throw new Error("the editing surface is not an element");
  }
  return surface;
}

/** The `.xw-richtext` wrapper around the editing surface. */
function richtextWrapper(surface: HTMLElement): HTMLElement {
  const richtext = surface.closest(".xw-richtext");
  if (!(richtext instanceof HTMLElement)) {
    throw new Error("the surface has no .xw-richtext wrapper");
  }
  return richtext;
}

/** The paragraph inside the surface holding the given visible text. */
function paragraphWithText(surface: HTMLElement, value: string): HTMLElement | undefined {
  return Array.from(surface.querySelectorAll("p")).find(
    (block) => block.textContent?.includes(value) ?? false,
  );
}

describe("ExamWorkspaceRichTextEditor paragraph space", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("shows two paragraphs as separate paragraph elements inside the labelled textbox", async () => {
    const wrapper = await mountVariant("field");
    try {
      const surface = textbox(wrapper);
      expect(surface.querySelectorAll("p").length).toBe(2);
      const first = paragraphWithText(surface, "first");
      const second = paragraphWithText(surface, "second");
      if (first === undefined || second === undefined) {
        throw new Error("expected paragraphs holding first and second");
      }
      expect(first.tagName).toBe("P");
      expect(second.tagName).toBe("P");
      expect(first).not.toBe(second);
      expect(surface.contains(first)).toBe(true);
      expect(surface.contains(second)).toBe(true);
    } finally {
      wrapper.unmount();
    }
  });

  it("keeps the compact textbox inside the compact wrapper and the full one outside it", async () => {
    const full = await mountVariant("field");
    try {
      const wrapper = richtextWrapper(textbox(full));
      expect(wrapper.classList.contains("xw-richtext")).toBe(true);
      expect(wrapper.classList.contains("xw-richtext--compact")).toBe(false);
    } finally {
      full.unmount();
    }
    const compact = await mountVariant("compact");
    try {
      const wrapper = richtextWrapper(textbox(compact));
      expect(wrapper.classList.contains("xw-richtext")).toBe(true);
      expect(wrapper.classList.contains("xw-richtext--compact")).toBe(true);
    } finally {
      compact.unmount();
    }
  });
});
