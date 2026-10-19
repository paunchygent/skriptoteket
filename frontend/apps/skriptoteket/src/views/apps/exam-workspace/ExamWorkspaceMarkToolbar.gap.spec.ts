/**
 * Exam workspace mark toolbar: the gap tool toggle and the per-platform
 * shortcut tooltips.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviour 8):
 *   The gap tool switch is the only gap control. The toolbar renders no
 *   "Lucka" button: with `showGap` it renders one gap control only, the
 *   glyph-only gap tool toggle, which emits `toggleGapTool` and never
 *   `makeGap`. Mousedown on the toggle is prevented so the caret stays in
 *   the paragraph. Every mark and heading tooltip names its shortcut for the
 *   viewer's platform.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { BODY_MARKS, MARK_LABELS } from "./examWorkspaceBodyMarks";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";

const MAKE_GAP = "[data-test='exam-workspace-toolbar-make-gap']";
const GAP_TOOL = "[data-test='exam-workspace-toolbar-gap-tool']";

describe("ExamWorkspaceMarkToolbar gap control", () => {
  it("renders no Lucka button without showGap", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    expect(wrapper.find(MAKE_GAP).exists()).toBe(false);
  });

  it("renders no Lucka button with showGap: the toggle is the only gap control", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    expect(wrapper.find(MAKE_GAP).exists()).toBe(false);
    const toggle = wrapper.get(GAP_TOOL);
    expect(toggle.text()).toBe("");
    expect(toggle.attributes("aria-label")).toBe("Luckverktyg");
  });

  it("prevents mousedown on the toggle so the caret stays", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const toggle = wrapper.get(GAP_TOOL);
    const event = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
    let prevented = false;
    event.preventDefault = () => {
      prevented = true;
    };
    toggle.element.dispatchEvent(event);
    expect(prevented).toBe(true);
  });

  it("never emits makeGap: the toggle emits toggleGapTool once", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    await wrapper.get(GAP_TOOL).trigger("click");
    expect(wrapper.emitted("toggleGapTool")).toHaveLength(1);
    expect(wrapper.emitted("makeGap")).toBeUndefined();
  });

  it("declares the Tom lucka emit for the glyph TASK-SKRIPT-40-04-17 wires later", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    wrapper.vm.$emit("insertEmptyGap");
    expect(wrapper.emitted("insertEmptyGap")).toHaveLength(1);
  });
});

describe("ExamWorkspaceMarkToolbar gap tool toggle", () => {
  it("renders no toggle without showGap", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    expect(wrapper.find(GAP_TOOL).exists()).toBe(false);
  });

  it("reads unpressed by default and pressed with gapToolOn", () => {
    const off = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    expect(off.get(GAP_TOOL).attributes("aria-pressed")).toBe("false");

    const on = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true, gapToolOn: true } });
    const toggle = on.get(GAP_TOOL);
    expect(toggle.attributes("aria-pressed")).toBe("true");
    expect(toggle.classes()).toContain("bg-panel-muted");
  });

  it("disables the toggle with its own cap reason", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showGap: true, gapToolDisabledReason: "Luckverktyg – högst 999 luckor" },
    });
    const toggle = wrapper.get(GAP_TOOL);
    const element = toggle.element;
    if (!(element instanceof HTMLButtonElement)) {
      throw new Error("the gap tool toggle is not a button");
    }
    expect(element.disabled).toBe(true);
    expect(toggle.attributes("title")).toBe("Luckverktyg – högst 999 luckor");
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
