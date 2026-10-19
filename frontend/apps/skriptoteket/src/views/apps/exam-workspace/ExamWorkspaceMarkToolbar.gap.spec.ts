/**
 * Exam workspace mark toolbar: the "Lucka" gap button.
 *
 * Expected behavior (TASK-SKRIPT-40-04-08 J4):
 *   The toolbar shows no gap button unless asked. With `showGap` it renders
 *   one more button after the marks, labelled "Lucka", which emits `makeGap`.
 *   A `gapDisabledReason` disables the button and becomes its tooltip.
 *   Mousedown on the button is prevented so the caret stays in the paragraph.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";

describe("ExamWorkspaceMarkToolbar gap button", () => {
  it("renders no gap button without showGap", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: {} });
    expect(wrapper.find("[data-test='exam-workspace-toolbar-make-gap']").exists()).toBe(false);
  });

  it("shows the Lucka button with showGap and emits makeGap on click", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const button = wrapper.get("[data-test='exam-workspace-toolbar-make-gap']");
    expect(button.text()).toContain("Lucka");
    expect(button.attributes("aria-label")).toBe("Gör till lucka");
    await button.trigger("click");
    expect(wrapper.emitted("makeGap")).toHaveLength(1);
  });

  it("disables the button with the reason as its tooltip", () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, {
      props: { showGap: true, gapDisabledReason: "Högst 999 luckor" },
    });
    const button = wrapper.get("[data-test='exam-workspace-toolbar-make-gap']");
    expect((button.element as HTMLButtonElement).disabled).toBe(true);
    expect(button.attributes("title")).toBe("Högst 999 luckor");
  });

  it("prevents mousedown on the button so the caret stays", async () => {
    const wrapper = mount(ExamWorkspaceMarkToolbar, { props: { showGap: true } });
    const button = wrapper.get("[data-test='exam-workspace-toolbar-make-gap']");
    const event = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
    let prevented = false;
    event.preventDefault = () => {
      prevented = true;
    };
    button.element.dispatchEvent(event);
    expect(prevented).toBe(true);
  });
});
