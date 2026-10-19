/**
 * Exam workspace mark toolbar: group order, history pair and glyph source.
 *
 * Expected behavior (TASK-SKRIPT-40-04-17 T4, T11, T14, T16):
 *   The toolbar holds Ångra and Gör om, the marks, Tom lucka and the gap
 *   switch, and the headings in that order, one `.xw-tools` group each with an `.xw-toolsep`
 *   between groups. Ångra and Gör om disable on the injected availability and
 *   call the injected undo and redo; without injected keys that group and its
 *   separator are absent. Every glyph renders through `UiGlyph`.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import { UiGlyph } from "../../../components/ui";
import { provideExamWorkspaceHistoryKeys } from "./examWorkspaceHistoryKeys";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import toolbarSource from "./ExamWorkspaceMarkToolbar.vue?raw";

const UNDO = "[data-test='exam-workspace-undo']";
const REDO = "[data-test='exam-workspace-redo']";
const GAP_TOOL = "[data-test='exam-workspace-toolbar-gap-tool']";

function mountWithHistory(
  props: Record<string, unknown>,
  keys: { canUndo: boolean; canRedo: boolean } | null,
) {
  const undo = vi.fn();
  const redo = vi.fn();
  const canUndo = ref(keys?.canUndo ?? false);
  const canRedo = ref(keys?.canRedo ?? false);
  const Host = defineComponent({
    setup() {
      if (keys) {
        provideExamWorkspaceHistoryKeys({ undo, redo, canUndo, canRedo });
      }
      return () => h(ExamWorkspaceMarkToolbar, props);
    },
  });
  const wrapper = mount(Host);
  return { wrapper, undo, redo, canUndo, canRedo };
}

function toolbarRoot(wrapper: { get(selector: string): { element: Element } }): Element {
  return wrapper.get("[role='toolbar']").element;
}

describe("ExamWorkspaceMarkToolbar group order", () => {
  it("renders four groups in order with a separator between each", () => {
    const { wrapper } = mountWithHistory(
      { showGap: true, showHeadings: true },
      { canUndo: true, canRedo: true },
    );
    const children = Array.from(toolbarRoot(wrapper).children).map((child) =>
      child.classList.contains("xw-toolsep") ? "sep" : "group",
    );
    expect(children).toEqual(["group", "sep", "group", "sep", "group", "sep", "group"]);

    const groups = wrapper.findAll(".xw-tools");
    const tests = groups.map((group) =>
      group.findAll("button").map((button) => button.attributes("data-test")),
    );
    expect(tests).toEqual([
      ["exam-workspace-undo", "exam-workspace-redo"],
      [
        "exam-workspace-body-mark-bold",
        "exam-workspace-body-mark-italic",
        "exam-workspace-body-mark-underline",
        "exam-workspace-body-mark-superscript",
        "exam-workspace-body-mark-subscript",
      ],
      ["exam-workspace-toolbar-gap-tool", "exam-workspace-toolbar-empty-gap"],
      [
        "exam-workspace-body-heading-1",
        "exam-workspace-body-heading-2",
        "exam-workspace-body-heading-3",
      ],
    ]);
  });

  it("renders all twelve tools in order inside the single scrolling toolbar root", () => {
    const { wrapper } = mountWithHistory(
      { showGap: true, showHeadings: true },
      { canUndo: true, canRedo: true },
    );
    const root = toolbarRoot(wrapper);
    expect(root.classList.contains("xw-toolbar")).toBe(true);
    expect(wrapper.findAll("[role='toolbar']")).toHaveLength(1);
    const tools = Array.from(root.querySelectorAll("button")).map((button) =>
      button.getAttribute("data-test"),
    );
    expect(tools).toEqual([
      "exam-workspace-undo",
      "exam-workspace-redo",
      "exam-workspace-body-mark-bold",
      "exam-workspace-body-mark-italic",
      "exam-workspace-body-mark-underline",
      "exam-workspace-body-mark-superscript",
      "exam-workspace-body-mark-subscript",
      "exam-workspace-toolbar-gap-tool",
      "exam-workspace-toolbar-empty-gap",
      "exam-workspace-body-heading-1",
      "exam-workspace-body-heading-2",
      "exam-workspace-body-heading-3",
    ]);
  });

  it("omits the gap and heading groups and their separators when not shown", () => {
    const { wrapper } = mountWithHistory({}, { canUndo: false, canRedo: false });
    expect(wrapper.findAll(".xw-tools")).toHaveLength(2);
    expect(wrapper.findAll(".xw-toolsep")).toHaveLength(1);
  });

  it("omits the history group and its separator without injected keys", () => {
    const { wrapper } = mountWithHistory({ showGap: true }, null);
    expect(wrapper.find(UNDO).exists()).toBe(false);
    expect(wrapper.find(REDO).exists()).toBe(false);
    expect(wrapper.findAll(".xw-tools")).toHaveLength(2);
    expect(wrapper.findAll(".xw-toolsep")).toHaveLength(1);
    expect(toolbarRoot(wrapper).children[0]?.classList.contains("xw-tools")).toBe(true);
  });
});

describe("ExamWorkspaceMarkToolbar Ångra and Gör om", () => {
  it("disables both from the injected availability and names why", () => {
    const { wrapper } = mountWithHistory({}, { canUndo: false, canRedo: false });
    expect(wrapper.get(UNDO).attributes("disabled")).toBeDefined();
    expect(wrapper.get(REDO).attributes("disabled")).toBeDefined();
    expect(wrapper.get(UNDO).attributes("title")).toBe("Inget att ångra");
    expect(wrapper.get(REDO).attributes("title")).toBe("Inget att göra om");
  });

  it("enables both, carries the shortcut and calls undo and redo on click", async () => {
    const { wrapper, undo, redo } = mountWithHistory({}, { canUndo: true, canRedo: true });
    const undoTitle = wrapper.get(UNDO).attributes("title") ?? "";
    const redoTitle = wrapper.get(REDO).attributes("title") ?? "";
    expect(undoTitle).toMatch(/^Ångra \((⌘Z|Ctrl\+Z)\)$/);
    expect(redoTitle).toMatch(/^Gör om \((⇧⌘Z|Ctrl\+Shift\+Z)\)$/);
    expect(wrapper.get(UNDO).attributes("aria-label")).toBe("Ångra");
    expect(wrapper.get(REDO).attributes("aria-label")).toBe("Gör om");
    await wrapper.get(UNDO).trigger("click");
    await wrapper.get(REDO).trigger("click");
    expect(undo).toHaveBeenCalledTimes(1);
    expect(redo).toHaveBeenCalledTimes(1);
  });

  it("follows a change of the injected availability", async () => {
    const { wrapper, canUndo, canRedo } = mountWithHistory({}, { canUndo: false, canRedo: false });
    canUndo.value = true;
    canRedo.value = true;
    await wrapper.vm.$nextTick();
    expect(wrapper.get(UNDO).attributes("disabled")).toBeUndefined();
    expect(wrapper.get(REDO).attributes("disabled")).toBeUndefined();
  });
});

describe("ExamWorkspaceMarkToolbar faces", () => {
  it("gives every button the tool face and the gap switch its pressed state", () => {
    const { wrapper } = mountWithHistory(
      { showGap: true, showHeadings: true, gapToolOn: true },
      { canUndo: true, canRedo: true },
    );
    for (const button of wrapper.findAll("button")) {
      expect(button.classes()).toContain("xw-tool");
    }
    const toggle = wrapper.get(GAP_TOOL);
    expect(toggle.classes()).toContain("xw-tool--switch");
    expect(toggle.attributes("aria-pressed")).toBe("true");
  });

  it("renders every glyph through UiGlyph", () => {
    const { wrapper } = mountWithHistory(
      { showGap: true, showHeadings: true },
      { canUndo: true, canRedo: true },
    );
    const meanings = wrapper.findAllComponents(UiGlyph).map((glyph) => glyph.props("meaning"));
    expect(meanings).toEqual([
      "undo",
      "redo",
      "bold",
      "italic",
      "underline",
      "superscript",
      "subscript",
      "gap-tool",
      "empty-gap",
      "heading-1",
      "heading-2",
      "heading-3",
    ]);
    for (const glyph of wrapper.findAllComponents(UiGlyph)) {
      expect(glyph.props("size")).toBe(16);
    }
  });

  it("imports no Lucide icon directly", () => {
    expect(toolbarSource).not.toMatch(/lucide/i);
  });
});
