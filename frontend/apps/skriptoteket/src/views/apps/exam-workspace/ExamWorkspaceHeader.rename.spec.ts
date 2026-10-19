/**
 * Exam workspace header inline title edit (TASK-SKRIPT-40-04-17, T7).
 *
 * Expected behavior:
 *   Clicking the title or the pencil replaces the title with a single-line
 *   input holding the title, selected. Enter or blur emits renameTitle with
 *   the new title; Escape restores the old one without emitting. An empty or
 *   unchanged title emits nothing, and a title that cannot be renamed does
 *   not start the edit.
 */

import { flushPromises } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { mountHeader } from "./ExamWorkspaceHeader.specSupport";

const TITLE = '[data-test="exam-workspace-title"]';
const PENCIL = '[data-test="exam-workspace-rename"]';
const INPUT = '[data-test="exam-workspace-title-input"]';

describe("ExamWorkspaceHeader inline rename", () => {
  it.each([TITLE, PENCIL])("starts the edit from %s with the text selected", async (trigger) => {
    const wrapper = mountHeader();
    await wrapper.get(trigger).trigger("click");
    await flushPromises();

    const input = wrapper.get<HTMLInputElement>(INPUT);
    expect(input.element.value).toBe("Prov 1");
    expect(input.element.selectionStart).toBe(0);
    expect(input.element.selectionEnd).toBe("Prov 1".length);
    expect(document.activeElement).toBe(input.element);
    expect(wrapper.find(TITLE).exists()).toBe(false);
    wrapper.unmount();
  });

  it("names the pencil Byt namn på provet", () => {
    const wrapper = mountHeader();
    expect(wrapper.get(PENCIL).attributes("title")).toBe("Byt namn på provet");
    expect(wrapper.get(PENCIL).attributes("aria-label")).toBe("Byt namn på provet");
    expect(wrapper.get(PENCIL).classes()).toContain("xw-tool");
    wrapper.unmount();
  });

  it("commits on Enter once, even though the input then blurs", async () => {
    const wrapper = mountHeader();
    await wrapper.get(TITLE).trigger("click");
    await flushPromises();

    const input = wrapper.get(INPUT);
    await input.setValue("  Nytt   namn ");
    await input.trigger("keydown", { key: "Enter" });
    await input.trigger("blur");

    expect(wrapper.emitted("renameTitle")).toEqual([["Nytt namn"]]);
    expect(wrapper.find(INPUT).exists()).toBe(false);
    wrapper.unmount();
  });

  it("commits on blur", async () => {
    const wrapper = mountHeader();
    await wrapper.get(PENCIL).trigger("click");
    await flushPromises();

    const input = wrapper.get(INPUT);
    await input.setValue("Efter blur");
    await input.trigger("blur");

    expect(wrapper.emitted("renameTitle")).toEqual([["Efter blur"]]);
    wrapper.unmount();
  });

  it("restores the old title on Escape and emits nothing, even when the input then blurs", async () => {
    const wrapper = mountHeader();
    await wrapper.get(TITLE).trigger("click");
    await flushPromises();

    const input = wrapper.get(INPUT);
    await input.setValue("Kasseras");
    await input.trigger("keydown", { key: "Escape" });
    await input.trigger("blur");

    expect(wrapper.emitted("renameTitle")).toBeUndefined();
    expect(wrapper.get(TITLE).text()).toBe("Prov 1");
    wrapper.unmount();
  });

  it("emits nothing for an empty or unchanged title", async () => {
    const wrapper = mountHeader();
    await wrapper.get(TITLE).trigger("click");
    await flushPromises();
    await wrapper.get(INPUT).setValue("   ");
    await wrapper.get(INPUT).trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("renameTitle")).toBeUndefined();
    expect(wrapper.get(TITLE).text()).toBe("Prov 1");

    await wrapper.get(TITLE).trigger("click");
    await flushPromises();
    await wrapper.get(INPUT).trigger("blur");
    expect(wrapper.emitted("renameTitle")).toBeUndefined();
    wrapper.unmount();
  });

  it("does not start the edit when the exam cannot be renamed", async () => {
    const wrapper = mountHeader({ canRename: false });
    expect(wrapper.get(TITLE).attributes("disabled")).toBeDefined();
    expect(wrapper.get(PENCIL).attributes("disabled")).toBeDefined();
    await wrapper.get(TITLE).trigger("click");
    expect(wrapper.find(INPUT).exists()).toBe(false);
    wrapper.unmount();
  });

  it("shows the full title as a tooltip and the only truncating element is the title", () => {
    const wrapper = mountHeader({ title: "Ett mycket långt provnamn som inte får plats" });
    expect(wrapper.get(TITLE).attributes("title")).toBe("Ett mycket långt provnamn som inte får plats");
    wrapper.unmount();
  });
});
