/**
 * Exam workspace question tools: Import and Granskad as in-content tools.
 *
 * Expected behavior:
 *   Import is a `.xw-tool` with the file-import glyph and the word "Import",
 *   pressed through `aria-expanded` while the import view is open, and keeps
 *   its tooltip and label. Granskad is a glyph-only `.xw-tool` with the
 *   confirm glyph, pressed through `aria-pressed` while reviewed, and its
 *   tooltip and label follow the state. Neither carries the old `xw-btn`
 *   pressed or checked classes.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceQuestionTools from "./ExamWorkspaceQuestionTools.vue";

const IMPORT = '[data-test="exam-workspace-import-toggle"]';
const REVIEW = '[data-test="exam-workspace-review"]';

const mounted: Array<VueWrapper> = [];

function mountTools(importOpen: boolean, reviewed: boolean | null): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionTools, {
    props: { disabled: false, hasImport: true, importOpen, reviewed },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionTools", () => {
  it("renders Import as a worded tool pressed through aria-expanded", async () => {
    const wrapper = mountTools(false, false);
    const importTool = wrapper.get(IMPORT);

    expect(importTool.classes()).toEqual(["xw-tool", "xw-tool--word", "tools__import"]);
    expect(importTool.findComponent(UiGlyph).props("meaning")).toBe("file-import");
    expect(importTool.text()).toBe("Import");
    expect(importTool.attributes("aria-label")).toBe("Import");
    expect(importTool.attributes("title")).toBe("Visa frågan som den står i provfilen");
    expect(importTool.attributes("aria-expanded")).toBe("false");

    await wrapper.setProps({ importOpen: true });

    expect(wrapper.get(IMPORT).attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(IMPORT).classes()).not.toContain("xw-btn--pressed");
  });

  it("renders Granskad as a glyph-only tool pressed through aria-pressed", async () => {
    const wrapper = mountTools(false, false);
    const review = wrapper.get(REVIEW);

    expect(review.classes()).toEqual(["xw-tool"]);
    expect(review.findComponent(UiGlyph).props("meaning")).toBe("confirm");
    expect(review.text()).toBe("");
    expect(review.attributes("aria-pressed")).toBe("false");
    expect(review.attributes("title")).toBe("Markera som granskad");
    expect(review.attributes("aria-label")).toBe("Markera som granskad");

    await wrapper.setProps({ reviewed: true });

    const pressed = wrapper.get(REVIEW);
    expect(pressed.attributes("aria-pressed")).toBe("true");
    expect(pressed.classes()).toEqual(["xw-tool"]);
    expect(pressed.attributes("title")).toBe("Ångra granskad");
    expect(pressed.attributes("aria-label")).toBe("Ångra granskad");
  });

  it("emits each toggle", async () => {
    const wrapper = mountTools(false, false);

    await wrapper.get(IMPORT).trigger("click");
    await wrapper.get(REVIEW).trigger("click");

    expect(wrapper.emitted("toggleImport")).toHaveLength(1);
    expect(wrapper.emitted("toggleReviewed")).toHaveLength(1);
  });
});
