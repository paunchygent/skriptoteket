/**
 * Exam workspace mark toolbar: the Tom lucka button.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 Behaviour 9 and L3, TASK-SKRIPT-40-04-17 unit 5):
 *   Where the redesign held a placeholder, the gap group holds a glyph-only
 *   Tom lucka button: the `empty-gap` meaning through `UiGlyph`, the native
 *   tooltip and aria-label `Tom lucka`, no text label. It emits
 *   `insertEmptyGap`, which the body editor inserts as one empty gap at the
 *   caret. It is disabled with the reason from `gapDisabledReason` as its
 *   tooltip while that reason is set, and it renders only in gap questions,
 *   with the gap tool switch.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import {
  EMPTY_GAP_AT_CAP_REASON,
} from "./useExamWorkspaceMakeGap";

const EMPTY_GAP = "[data-test='exam-workspace-toolbar-empty-gap']";
const GAP_TOOL = "[data-test='exam-workspace-toolbar-gap-tool']";

describe("ExamWorkspaceMarkToolbar Tom lucka", () => {
  it("renders no Tom lucka button without showGap", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    expect(wrapper.find(EMPTY_GAP).exists()).toBe(false);
  });

  it("renders a glyph-only Tom lucka button with the gap switch", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const button = wrapper.get(EMPTY_GAP);
    expect(button.text()).toBe("");
    expect(button.attributes("aria-label")).toBe("Tom lucka");
    expect(button.attributes("title")).toBe("Tom lucka");
    expect(button.classes()).toContain("xw-tool");
    expect(button.classes()).not.toContain("xw-tool--switch");
    expect(button.findComponent(UiGlyph).props("meaning")).toBe("empty-gap");
    expect(wrapper.find(GAP_TOOL).exists()).toBe(true);
  });

  it("emits insertEmptyGap on click and nothing else", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    await wrapper.get(EMPTY_GAP).trigger("click");
    expect(wrapper.emitted("insertEmptyGap")).toHaveLength(1);
    expect(wrapper.emitted("toggleGapTool")).toBeUndefined();
    expect(wrapper.emitted("makeGap")).toBeUndefined();
  });

  it("disables with the gap cap reason as its tooltip", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showGap: true, emptyGapDisabledReason: EMPTY_GAP_AT_CAP_REASON },
    });
    const button = wrapper.get(EMPTY_GAP);
    const element = button.element;
    if (!(element instanceof HTMLButtonElement)) {
      throw new Error("the Tom lucka button is not a button");
    }
    expect(element.disabled).toBe(true);
    expect(button.attributes("title")).toBe(EMPTY_GAP_AT_CAP_REASON);
  });

  it("disables with disabled", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true, disabled: true } });
    const element = wrapper.get(EMPTY_GAP).element;
    if (!(element instanceof HTMLButtonElement)) {
      throw new Error("the Tom lucka button is not a button");
    }
    expect(element.disabled).toBe(true);
  });
});
