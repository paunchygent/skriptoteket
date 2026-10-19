/**
 * Exam workspace mark toolbar: the "Lucka" gap button, the gap tool toggle
 * and the per-platform shortcut tooltips.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4, TASK-SKRIPT-40-04-09 G3):
 *   The toolbar shows no gap button unless asked. With `showGap` it renders
 *   one more button after the marks, labelled "Lucka", which emits `makeGap`.
 *   A `gapDisabledReason` disables the button and becomes its tooltip.
 *   Mousedown on the button is prevented so the caret stays in the paragraph.
 *   Right after the Lucka button sits a glyph-only gap tool toggle: no visible
 *   text, its shortcut in the tooltip and `aria-keyshortcuts`, pressed while
 *   the tool is on, emitting `toggleGapTool`, and disabled with the cap reason
 *   or `disabled`. Every mark and heading tooltip names its shortcut for the
 *   viewer's platform.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { BODY_MARKS, MARK_LABELS } from "./examWorkspaceBodyMarks";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";

const MAKE_GAP = "[data-test='exam-workspace-toolbar-make-gap']";
const GAP_TOOL = "[data-test='exam-workspace-toolbar-gap-tool']";

describe("ExamWorkspaceMarkToolbar gap button", () => {
  it("renders no gap button without showGap", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    expect(wrapper.find(MAKE_GAP).exists()).toBe(false);
  });

  it("shows the Lucka button with showGap and emits makeGap on click", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const button = wrapper.get(MAKE_GAP);
    expect(button.text()).toContain("Lucka");
    expect(button.attributes("aria-label")).toBe("Gör till lucka");
    await button.trigger("click");
    expect(wrapper.emitted("makeGap")).toHaveLength(1);
  });

  it("disables the button with the reason as its tooltip", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showGap: true, gapDisabledReason: "Högst 999 luckor" },
    });
    const button = wrapper.get(MAKE_GAP);
    const element = button.element;
    if (!(element instanceof HTMLButtonElement)) {
      throw new Error("the Lucka button is not a button");
    }
    expect(element.disabled).toBe(true);
    expect(button.attributes("title")).toBe("Högst 999 luckor");
  });

  it("prevents mousedown on the button so the caret stays", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const button = wrapper.get(MAKE_GAP);
    const event = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
    let prevented = false;
    event.preventDefault = () => {
      prevented = true;
    };
    button.element.dispatchEvent(event);
    expect(prevented).toBe(true);
  });
});

describe("ExamWorkspaceMarkToolbar gap tool toggle", () => {
  it("renders no toggle without showGap", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    expect(wrapper.find(GAP_TOOL).exists()).toBe(false);
  });

  it("sits right after the Lucka button with no visible text", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const toggle = wrapper.get(GAP_TOOL);
    expect(toggle.text()).toBe("");
    expect(toggle.attributes("aria-label")).toBe("Luckverktyg");
    const previous = toggle.element.previousElementSibling;
    if (!(previous instanceof HTMLButtonElement)) {
      throw new Error("the toggle does not sit right after a button");
    }
    expect(previous.getAttribute("data-test")).toBe("exam-workspace-toolbar-make-gap");
  });

  it("reads unpressed by default and pressed with gapToolOn", () => {
    const off = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    expect(off.get(GAP_TOOL).attributes("aria-pressed")).toBe("false");

    const on = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true, gapToolOn: true } });
    const toggle = on.get(GAP_TOOL);
    expect(toggle.attributes("aria-pressed")).toBe("true");
    expect(toggle.classes()).toContain("bg-panel-muted");
  });

  it("emits toggleGapTool once on click and never makeGap", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    await wrapper.get(GAP_TOOL).trigger("click");
    expect(wrapper.emitted("toggleGapTool")).toHaveLength(1);
    expect(wrapper.emitted("makeGap")).toBeUndefined();
  });

  it("keeps the Lucka button emitting makeGap beside the toggle", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true, gapToolOn: true } });
    await wrapper.get(MAKE_GAP).trigger("click");
    expect(wrapper.emitted("makeGap")).toHaveLength(1);
    expect(wrapper.emitted("toggleGapTool")).toBeUndefined();
  });

  it("disables the toggle with the cap reason as its tooltip", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showGap: true, gapDisabledReason: "Högst 999 luckor" },
    });
    const toggle = wrapper.get(GAP_TOOL);
    const element = toggle.element;
    if (!(element instanceof HTMLButtonElement)) {
      throw new Error("the gap tool toggle is not a button");
    }
    expect(element.disabled).toBe(true);
    expect(toggle.attributes("title")).toBe("Högst 999 luckor");
  });

  it("disables the toggle with disabled", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true, disabled: true } });
    const element = wrapper.get(GAP_TOOL).element;
    if (!(element instanceof HTMLButtonElement)) {
      throw new Error("the gap tool toggle is not a button");
    }
    expect(element.disabled).toBe(true);
  });
});

describe("ExamWorkspaceMarkToolbar shortcut tooltips", () => {
  it("names each mark shortcut in the title and aria-keyshortcuts", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    for (const mark of BODY_MARKS) {
      const button = wrapper.get(`[data-test='exam-workspace-body-mark-${mark}']`);
      expect(button.attributes("aria-label")).toBe(MARK_LABELS[mark]);
      const title = button.attributes("title") ?? "";
      expect(title.startsWith(`${MARK_LABELS[mark]} (`)).toBe(true);
      expect(title.endsWith(")")).toBe(true);
      expect(button.attributes("aria-keyshortcuts")).toMatch(/^(Meta|Control)\+/);
    }
  });

  it("names each heading shortcut in the title and aria-keyshortcuts", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showHeadings: true } });
    for (const level of [1, 2, 3] as const) {
      const button = wrapper.get(`[data-test='exam-workspace-body-heading-${level}']`);
      expect(button.attributes("aria-label")).toBe(`Rubrik ${level}`);
      const title = button.attributes("title") ?? "";
      expect(title.startsWith(`Rubrik ${level} (`)).toBe(true);
      expect(title.endsWith(")")).toBe(true);
      expect(button.attributes("aria-keyshortcuts")).toMatch(/^(Meta|Control)\+/);
    }
  });

  it("names the gap tool shortcut in the toggle tooltip", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const toggle = wrapper.get(GAP_TOOL);
    const title = toggle.attributes("title") ?? "";
    expect(title.startsWith("Luckverktyg (")).toBe(true);
    expect(title.endsWith(")")).toBe(true);
    expect(toggle.attributes("aria-keyshortcuts")).toMatch(/^(Meta|Control)\+/);
  });
});
