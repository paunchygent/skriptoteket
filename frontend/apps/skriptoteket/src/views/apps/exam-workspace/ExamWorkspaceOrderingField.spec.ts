/**
 * Exam workspace ordering field.
 *
 * Expected behavior:
 *   Steps render in key order with their numbers; the Utskriftsordning block
 *   shows the saved print order; add, move, remove and Blanda om emit; the
 *   last step cannot be removed, Blanda om needs two steps, and an empty step
 *   is marked invalid. New-question and change-type menus offer Ordna to a
 *   standalone question only.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import ExamWorkspaceOrderingField from "./ExamWorkspaceOrderingField.vue";
import ExamWorkspaceQuestionHead from "./ExamWorkspaceQuestionHead.vue";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { EXAM_WORKSPACE_TYPE_LABELS } from "./examWorkspaceRows";
import { plainBody } from "./examWorkspaceRichText";

function stepped(texts: string[], printOrder: string[]): NativeExamItem {
  const base = newTeacherItem("item_001", 1, "ordering");
  return {
    ...base,
    choices: texts.map((text, index) => ({
      body: text === "" ? [{ heading_level: null, segments: [{ kind: "text", marks: [], text: " " }] }] : plainBody(text),
      choice_id: `choice_${String(index + 1).padStart(3, "0")}`,
    })),
    print_order: printOrder,
  };
}

function mountField(item: NativeExamItem) {
  return mount(ExamWorkspaceOrderingField, { props: { item } });
}

const three = () => stepped(["Först", "Sedan", "Sist"], ["choice_003", "choice_001", "choice_002"]);

describe("ExamWorkspaceOrderingField", () => {
  it("renders steps in key order and the print block in print order", () => {
    const wrapper = mountField(three());

    expect(wrapper.text()).toContain("Steg i rätt ordning");
    expect(wrapper.text()).toContain("Ordningen i listan är facit.");
    expect(wrapper.findAll(".ord__row").map((row) => row.get(".ord__num").text())).toEqual(["1", "2", "3"]);
    expect(wrapper.find('[data-test="exam-workspace-ordering-step-text-choice_001"]').exists()).toBe(true);
    const printed = wrapper.get('[data-test="exam-workspace-ordering-print-order"]').findAll("li");
    expect(printed.map((entry) => entry.text())).toEqual(["Sist", "Först", "Sedan"]);
    expect(printed[0]!.find(".ord__box").exists()).toBe(true);
  });

  it("emits add, move, remove and shuffle", async () => {
    const wrapper = mountField(three());

    await wrapper.get('[data-test="exam-workspace-ordering-add-step"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-ordering-step-down-choice_001"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-ordering-step-up-choice_003"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-ordering-step-remove-choice_002"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-ordering-shuffle"]').trigger("click");

    expect(wrapper.emitted("addStep")).toHaveLength(1);
    expect(wrapper.emitted("moveStep")).toEqual([["choice_001", 1], ["choice_003", -1]]);
    expect(wrapper.emitted("removeStep")).toEqual([["choice_002"]]);
    expect(wrapper.emitted("shuffle")).toHaveLength(1);
  });

  it("disables moves at the ends", () => {
    const wrapper = mountField(three());

    expect(wrapper.get('[data-test="exam-workspace-ordering-step-up-choice_001"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-ordering-step-down-choice_003"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-ordering-step-down-choice_001"]').attributes("disabled")).toBeUndefined();
  });

  it("disables remove and Blanda om at one step", async () => {
    const wrapper = mountField(stepped(["Ensam"], ["choice_001"]));

    const remove = wrapper.get('[data-test="exam-workspace-ordering-step-remove-choice_001"]');
    expect(remove.attributes("disabled")).toBeDefined();
    const shuffle = wrapper.get('[data-test="exam-workspace-ordering-shuffle"]');
    expect(shuffle.attributes("disabled")).toBeDefined();
    await shuffle.trigger("click");
    await remove.trigger("click");
    expect(wrapper.emitted("shuffle")).toBeUndefined();
    expect(wrapper.emitted("removeStep")).toBeUndefined();
  });

  it("marks an empty step invalid", () => {
    const wrapper = mountField(stepped(["Först", ""], ["choice_002", "choice_001"]));

    expect(wrapper.find('[data-test="exam-workspace-ordering-empty-hint"]').exists()).toBe(true);
    expect(mountField(three()).find('[data-test="exam-workspace-ordering-empty-hint"]').exists()).toBe(false);
  });
});

describe("ordering in the editor and menus", () => {
  it("shows the ordering field and no choice field for an ordering question", () => {
    const wrapper = mount(ExamWorkspaceQuestionEditor, {
      props: {
        item: three(),
        label: "1",
        origin: "created",
        parent: null,
        child: null,
        converting: false,
        disabled: false,
        notice: null,
        importOpen: false,
      },
    });

    expect(wrapper.find('[data-test="exam-workspace-ordering-field"]').exists()).toBe(true);
    expect(wrapper.find('[data-test^="exam-workspace-choice-text-"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Ordna");
  });

  it("creates a keyed one-point ordering question that never equals its key", () => {
    const item = newTeacherItem("item_009", 9, "ordering");

    expect(item.points).toBe(1);
    expect(item.answer_key.origin).toBe("teacher_authored");
    expect(item.tick_points).toBeNull();
    expect(item.choices.map((choice) => choice.choice_id)).toEqual(["choice_001", "choice_002"]);
    expect(item.print_order).not.toEqual(["choice_001", "choice_002"]);
    expect(hasInvalidAnswerKey(item)).toBe(false);
    expect(newTeacherItem("item_010", 10, "free_text").points).toBeNull();
    expect(newTeacherItem("item_010", 10, "single_choice").print_order).toEqual([]);
    expect(EXAM_WORKSPACE_TYPE_LABELS.ordering).toBe("Ordna");
  });

  it("offers Ordna in the new-question menu but not in the deluppgift menu", () => {
    const open = (child: boolean) =>
      mount(ExamWorkspaceNewItemMenu, {
        props: { open: true, anchor: null, child },
        global: { stubs: { ExamWorkspaceMenu: { template: "<div><slot /></div>" } } },
      });

    expect(open(false).find('[data-test="exam-workspace-new-ordering"]').text()).toBe("Ordna");
    expect(open(true).find('[data-test="exam-workspace-new-ordering"]').exists()).toBe(false);
  });
});

describe("Byt frågetyp", () => {
  afterEach(() => {
    document.body.replaceChildren();
  });

  async function openTypeMenu(child: { index: number; count: number } | null) {
    const wrapper = mount(ExamWorkspaceQuestionHead, {
      attachTo: document.body,
      props: {
        label: "1",
        kind: "free_text",
        unbuilt: false,
        converting: false,
        child,
        disabled: false,
        suggestedKind: null,
      },
    });
    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();
    return wrapper;
  }

  it("offers Ordna for a standalone question", async () => {
    const wrapper = await openTypeMenu(null);

    expect(document.querySelector('[data-test="exam-workspace-type-ordering"]')?.textContent).toContain("Ordna");
    wrapper.unmount();
  });

  it("never offers Ordna for a deluppgift", async () => {
    const wrapper = await openTypeMenu({ index: 0, count: 2 });

    expect(document.querySelector('[data-test="exam-workspace-type-matching"]')).not.toBeNull();
    expect(document.querySelector('[data-test="exam-workspace-type-ordering"]')).toBeNull();
    wrapper.unmount();
  });
});
