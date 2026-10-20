/**
 * Exam workspace Skrivyta field: the "Alla fritextfrågor" popover, focus and lifecycle.
 *
 * Expected behavior:
 *   The "Alla fritextfrågor" tool opens a popover in either of two states.
 *   When other free-text questions differ, it names how many questions get
 *   the count and which differ, and confirming emits the current count and
 *   closes. When all already match, it confirms that with only "Stäng". The
 *   tool stays enabled when the counts match and is inert only while the
 *   field is disabled. Escape anywhere in the document, Avbryt, Stäng and a
 *   pointer press on a non-focusable outside surface close the popover and
 *   return focus to the tool; a pointer press on a focusable outside control
 *   closes it and that control keeps the focus; Tab to a control outside
 *   closes it without moving focus.
 */

import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import {
  APPLY_ALL,
  CANCEL,
  CLOSE,
  CONFIRM,
  MATCHING,
  POPOVER,
  mountField,
  mountedWrappers,
  requireButton,
  teardownWritingLinesField,
} from "./ExamWorkspaceWritingLinesField.specSupport";

afterEach(() => {
  teardownWritingLinesField();
});

describe("ExamWorkspaceWritingLinesField", () => {
  it("opens no popover until the tool is pressed", () => {
    const wrapper = mountField(8);
    const tool = wrapper.get(APPLY_ALL);

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(tool.attributes("aria-haspopup")).toBe("dialog");
    expect(tool.attributes("aria-expanded")).toBe("false");
    expect(tool.attributes("title")).toBe("Samma skrivyta för alla fritextfrågor");
  });

  it("names the questions that change and what they get", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");

    const popover = wrapper.get(POPOVER);
    const paragraphs = popover.findAll("p").map((p) => p.text());
    expect(popover.attributes("role")).toBe("dialog");
    expect(popover.attributes("aria-label")).toBe("Samma skrivyta för alla fritextfrågor");
    expect(wrapper.get(APPLY_ALL).attributes("aria-expanded")).toBe("true");
    expect(popover.get("h3").text()).toBe("Samma skrivyta för alla fritextfrågor");
    expect(paragraphs).toEqual([
      "Alla 6 fritextfrågor får 8 rader.",
      "1a, 1b och 3a har i dag en annan skrivyta.",
    ]);
    expect(popover.findAll("button").map((button) => button.text())).toEqual(["Avbryt", "Använd 8 rader"]);
  });

  it("uses the singular for one row in the popover", async () => {
    const wrapper = mountField(1, { freeText: [{ itemId: "i1", label: "1", lines: 1 }, { itemId: "i2", label: "2", lines: 3 }] });
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.findAll(`${POPOVER} p`).slice(0, 2).map((paragraph) => paragraph.text())).toEqual([
      "Alla 2 fritextfrågor får 1 rad.",
      "2 har i dag en annan skrivyta.",
    ]);
    expect(wrapper.get(CONFIRM).text()).toBe("Använd 1 rad");
  });

  it("moves focus to the confirm action on open", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.vm.$nextTick();

    expect(document.activeElement).toBe(wrapper.get(CONFIRM).element);
  });

  it("emits the current count to every free-text question on confirm and closes", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(CONFIRM).trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("applyToAll")).toEqual([[8]]);
    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
  });

  it("emits nothing from opening the popover", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.emitted("applyToAll")).toBeUndefined();
  });

  it("closes on Avbryt without emitting and returns focus to the tool", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(CANCEL).trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(wrapper.emitted("applyToAll")).toBeUndefined();
    expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
  });

  it("closes on Escape without emitting and returns focus to the tool", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.vm.$nextTick();
    await wrapper.get(CONFIRM).trigger("keydown", { key: "Escape" });
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(wrapper.emitted("applyToAll")).toBeUndefined();
    expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
  });

  it("closes on Escape pressed outside the popover and returns focus to the tool", async () => {
    const outside = document.createElement("div");
    document.body.append(outside);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      await nextTick();
      // Focus left the popover without landing on another control (relatedTarget null), so the popover stays open.
      requireButton(wrapper.get(CONFIRM).element).blur();
      await nextTick();
      expect(wrapper.find(POPOVER).exists()).toBe(true);
      outside.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      await nextTick();

      expect(wrapper.find(POPOVER).exists()).toBe(false);
      expect(wrapper.emitted("applyToAll")).toBeUndefined();
      expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
    } finally {
      outside.remove();
    }
  });

  it("ignores other keys and Escape during composition while open", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await nextTick();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, isComposing: true }));
    await nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(true);
  });

  it("closes without moving focus when Tab leaves the popover for a field outside", async () => {
    const outside = document.createElement("input");
    document.body.append(outside);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      await nextTick();
      const confirmButton = requireButton(wrapper.get(CONFIRM).element);
      expect(document.activeElement).toBe(confirmButton);
      outside.focus();
      await nextTick();

      expect(wrapper.find(POPOVER).exists()).toBe(false);
      expect(wrapper.emitted("applyToAll")).toBeUndefined();
      expect(document.activeElement).toBe(outside);
    } finally {
      outside.remove();
    }
  });

  it("stays open when focus moves between the tool and the popover", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await nextTick();
    requireButton(wrapper.get(APPLY_ALL).element).focus();
    requireButton(wrapper.get(CANCEL).element).focus();
    await nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(true);
  });

  it("closes on a pointer press on a non-focusable outside surface and returns focus to the tool", async () => {
    const surface = document.createElement("div");
    document.body.append(surface);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      await nextTick();
      surface.dispatchEvent(new Event("pointerdown", { bubbles: true }));
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(wrapper.find(POPOVER).exists()).toBe(false);
      expect(wrapper.emitted("applyToAll")).toBeUndefined();
      expect(document.activeElement).toBe(wrapper.get(APPLY_ALL).element);
    } finally {
      surface.remove();
    }
  });

  it("closes on a pointer press on a focusable outside control and leaves focus there", async () => {
    const outside = document.createElement("input");
    document.body.append(outside);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      await nextTick();
      outside.dispatchEvent(new Event("pointerdown", { bubbles: true }));
      outside.focus();
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(wrapper.find(POPOVER).exists()).toBe(false);
      expect(wrapper.emitted("applyToAll")).toBeUndefined();
      expect(document.activeElement).toBe(outside);
    } finally {
      outside.remove();
    }
  });

  it("removes its open-lifetime listeners on unmount", async () => {
    const outside = document.createElement("button");
    document.body.append(outside);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      await nextTick();
      wrapper.unmount();
      mountedWrappers.splice(mountedWrappers.indexOf(wrapper), 1);

      outside.focus();
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      outside.dispatchEvent(new Event("pointerdown", { bubbles: true }));
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(document.activeElement).toBe(outside);
    } finally {
      outside.remove();
    }
  });

  it("removes its open-lifetime listeners on close", async () => {
    const outside = document.createElement("button");
    document.body.append(outside);
    try {
      const wrapper = mountField(8);
      await wrapper.get(APPLY_ALL).trigger("click");
      await wrapper.get(CANCEL).trigger("click");
      await nextTick();
      outside.focus();
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      await nextTick();

      expect(document.activeElement).toBe(outside);
    } finally {
      outside.remove();
    }
  });

  it("stays open for a pointer press inside the popover", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    wrapper.get(POPOVER).element.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(true);
  });

  it("closes when the tool is pressed again", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.get(APPLY_ALL).trigger("click");

    expect(wrapper.find(POPOVER).exists()).toBe(false);
  });

  it("closes when the field becomes disabled", async () => {
    const wrapper = mountField(8);
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.setProps({ disabled: true });

    expect(wrapper.find(POPOVER).exists()).toBe(false);
  });

  it("names the exam's only free-text question instead of counting it", async () => {
    const wrapper = mountField(8, { freeText: [{ itemId: "i1", label: "1", lines: 8 }] });
    await wrapper.get(APPLY_ALL).trigger("click");
    await wrapper.vm.$nextTick();

    const popover = wrapper.get(POPOVER);
    expect(popover.text()).toContain("Det här är provets enda fritextfråga.");
    expect(popover.text()).not.toContain("Alla 1");
  });

  it("keeps the tool enabled and opens a confirmation with only Stäng when every count matches", async () => {
    const wrapper = mountField(8, { freeText: MATCHING });
    const tool = wrapper.get(APPLY_ALL);

    expect(tool.attributes("disabled")).toBeUndefined();
    expect(tool.attributes("title")).toBe("Samma skrivyta för alla fritextfrågor");
    await tool.trigger("click");
    await wrapper.vm.$nextTick();

    const popover = wrapper.get(POPOVER);
    expect(popover.text()).toContain("Alla 6 fritextfrågor har redan 8 rader.");
    expect(popover.find(".xw-pop__ok svg").exists()).toBe(true);
    expect(popover.findAll("button").map((button) => button.text())).toEqual(["Stäng"]);
    expect(wrapper.find(CONFIRM).exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.get(CLOSE).element);

    await wrapper.get(CLOSE).trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.find(POPOVER).exists()).toBe(false);
    expect(wrapper.emitted("applyToAll")).toBeUndefined();
    expect(document.activeElement).toBe(tool.element);
  });
});
