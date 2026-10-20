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
 * this spec stays structural: the full variant renders two paragraphs as
 * sibling block elements directly under `.xw-richtext__surface` inside a
 * wrapper with class `xw-richtext` (and without `xw-richtext--compact`),
 * while the compact variant's wrapper carries `xw-richtext--compact`.
 * The visual proof is the staging walk.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import ExamWorkspaceRichTextEditor from "./ExamWorkspaceRichTextEditor.vue";
import { paragraph, text } from "./ExamWorkspaceRichTextEditor.specSupport";
// The SFC source: `?raw` bypasses the Vue transform and returns the file
// text, so the spec can assert on the component's own style block.
import editorSource from "./ExamWorkspaceRichTextEditor.vue?raw";

const PARAGRAPH_SPACE_RULE =
  ".xw-richtext:not(.xw-richtext--compact) .xw-richtext__surface > * + *";

async function mountVariant(variant: "field" | "compact") {
  const testId = variant === "compact" ? "paragraph-space-compact" : "paragraph-space-full";
  const wrapper = mount(ExamWorkspaceRichTextEditor, {
    attachTo: document.body,
    props: {
      body: [paragraph(text("first")), paragraph(text("second"))],
      label: "Frågetext",
      testId,
      variant,
    },
  });
  await nextTick();
  await nextTick();
  const surface = wrapper.get(`[data-test='${testId}']`).element as HTMLElement;
  const richtext = surface.closest(".xw-richtext") as HTMLElement | null;
  if (!richtext) {
    throw new Error("the surface has no .xw-richtext wrapper");
  }
  return { wrapper, surface, richtext };
}

describe("ExamWorkspaceRichTextEditor paragraph space", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders two paragraphs as siblings under the surface in the full variant", async () => {
    const { wrapper, surface, richtext } = await mountVariant("field");
    try {
      expect(richtext.classList.contains("xw-richtext")).toBe(true);
      expect(richtext.classList.contains("xw-richtext--compact")).toBe(false);
      const blocks = Array.from(surface.children);
      expect(blocks).toHaveLength(2);
      for (const block of blocks) {
        expect(block.tagName).toBe("P");
        expect(block.parentElement).toBe(surface);
      }
      expect(blocks[0]?.textContent).toContain("first");
      expect(blocks[1]?.textContent).toContain("second");
    } finally {
      wrapper.unmount();
    }
  });

  it("marks the compact variant wrapper so the gap rule stays away", async () => {
    const { wrapper, richtext } = await mountVariant("compact");
    try {
      expect(richtext.classList.contains("xw-richtext")).toBe(true);
      expect(richtext.classList.contains("xw-richtext--compact")).toBe(true);
    } finally {
      wrapper.unmount();
    }
  });

  it("keeps the full-variant paragraph gap rule in the component styles", () => {
    // The test setup does not inject SFC styles into jsdom, so the spec reads
    // the component source.
    expect(editorSource).toContain(`${PARAGRAPH_SPACE_RULE} { margin-top: 1rem; }`);
  });
});
