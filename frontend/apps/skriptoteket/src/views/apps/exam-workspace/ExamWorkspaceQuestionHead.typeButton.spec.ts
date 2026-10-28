/**
 * Exam workspace question header, the type switch as a built compact button.
 *
 * Expected behavior:
 *   The Byt frågetyp trigger is `xw-btn xw-btn--compact qhead__kind`, so at
 *   rest it shows the built compact frame, fill and text, and its states keep
 *   their meaning: unbuilt adds `qhead__kind--error` and the blocker glyph,
 *   converting and disabled both disable it, and a click opens Byt frågetyp.
 *   "Gör om till [typ]" is not in the head; the type the labeler suggests is
 *   still marked Förslag inside Byt frågetyp.
 */

import { flushPromises, mount } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";

const mounted: Array<VueWrapper> = [];

function mountHead(options: {
  converting?: boolean;
  disabled?: boolean;
  kind?: NativeExamItemKind;
  suggestedKind?: NativeExamItemKind | null;
  typeLabel?: string;
  unbuilt?: boolean;
} = {}): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionHead, {
    attachTo: document.body,
    props: {
      child: null,
      converting: options.converting ?? false,
      currentParentId: null,
      disabled: options.disabled ?? false,
      kind: options.kind ?? "free_text",
      label: "3",
      moveTargets: [],
      suggestedKind: options.suggestedKind ?? null,
      typeLabel: options.typeLabel ?? "Fritext",
      unbuilt: options.unbuilt ?? false,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

function typeTrigger(wrapper: VueWrapper): Omit<DOMWrapper<HTMLButtonElement>, "exists"> {
  return wrapper.get<HTMLButtonElement>('[data-test="exam-workspace-type"]');
}

function inDocument(testId: string): HTMLElement | null {
  const element = document.querySelector(`[data-test="${testId}"]`);
  return element instanceof HTMLElement ? element : null;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionHead type button", () => {
  it("shows the built compact button frame with its type name inside a truncating span", () => {
    const wrapper = mountHead();
    const trigger = typeTrigger(wrapper);
    const element = trigger.element;

    expect(element.classList.contains("xw-btn")).toBe(true);
    expect(element.classList.contains("xw-btn--compact")).toBe(true);
    expect(element.classList.contains("qhead__kind")).toBe(true);
    expect(element.classList.contains("qhead__kind--error")).toBe(false);
    expect(element.classList.contains("qhead__type")).toBe(false);
    expect(trigger.get(".qhead__kindtext").text()).toBe("Fritext");
  });

  it("marks an unbuilt question with the error class and the blocker glyph", () => {
    const wrapper = mountHead({ unbuilt: true, typeLabel: "Fritext" });
    const element = typeTrigger(wrapper).element;

    expect(element.classList.contains("qhead__kind--error")).toBe(true);
    expect(element.querySelector("svg.lucide-circle-alert")).not.toBeNull();
  });

  it("disables the type button while the question converts and while the header is disabled", () => {
    const converting = mountHead({ converting: true });
    expect(typeTrigger(converting).element.disabled).toBe(true);

    const disabled = mountHead({ disabled: true });
    expect(typeTrigger(disabled).element.disabled).toBe(true);
  });

  it("opens and closes Byt frågetyp from the type button", async () => {
    const wrapper = mountHead();
    const trigger = typeTrigger(wrapper);

    expect(trigger.attributes("aria-expanded")).toBe("false");
    expect(inDocument("exam-workspace-type-menu")).toBeNull();

    await trigger.trigger("click");
    await flushPromises();
    expect(trigger.attributes("aria-expanded")).toBe("true");
    expect(inDocument("exam-workspace-type-menu")).not.toBeNull();

    await trigger.trigger("click");
    await flushPromises();
    expect(trigger.attributes("aria-expanded")).toBe("false");
  });

  it("offers no Gör om till button in the head and still marks the suggested type in the menu", async () => {
    const wrapper = mountHead({ kind: "free_text", suggestedKind: "gap_fill", typeLabel: "Fritext" });

    expect(inDocument("exam-workspace-suggested-type")).toBeNull();
    expect(wrapper.text()).not.toContain("Gör om till");

    await typeTrigger(wrapper).trigger("click");
    await flushPromises();

    const chip = inDocument("exam-workspace-type-suggested");
    expect(chip).not.toBeNull();
    expect(chip!.textContent).toContain("Förslag");
    expect(chip!.closest('[data-test="exam-workspace-type-gap_fill"]')).not.toBeNull();
  });
});
