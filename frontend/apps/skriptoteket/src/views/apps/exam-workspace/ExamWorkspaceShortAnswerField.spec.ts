/**
 * Exam workspace Kort svar field.
 *
 * Expected behavior:
 *   A Kort svar question shows exactly two fields: "Fråga" (the rich-text
 *   question without its answer paragraph, with the mark toolbar and no gap
 *   button) and "Svar" (one row per accepted answer, with the automatic
 *   answers under it). No gap chip, no popover, no "Visa som text".
 *   Typing in Fråga re-attaches the gap paragraph, so the gap record never
 *   drops; the store's write-back never resets the Fråga content.
 */

import { mount } from "@vue/test-utils";
import type { Editor } from "@tiptap/core";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceShortAnswerField from "./ExamWorkspaceShortAnswerField.vue";
import { withBody } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import { posIn } from "./ExamWorkspaceBodyEditor.specSupport";

const ITEM_ID = "item_001";
const GAP_ID = "gap_001";
const QUESTION = "Vad heter Sveriges huvudstad?";

function shortAnswerItem(
  accepted: string[] = ["Stockholm"],
  automatic: string[] = [],
): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body: [
      ...plainBody(QUESTION),
      { heading_level: null, segments: [{ kind: "gap", gap_id: GAP_ID }] },
    ],
    choices: [],
    gaps: [buildGap(GAP_ID, accepted, { automatic_values: automatic })],
    item_id: ITEM_ID,
    kind: "gap_fill",
    match_left: [],
    match_right: [],
    points: null,
    points_estimated: false,
    review: { confidence: null, parse_origin: "teacher_created", reasons: [], state: "review_complete" },
    sequence: 1,
    source_anchor: null,
    suggested_kind: null,
    tick_points: null,
  };
}

type FieldWrapper = Awaited<ReturnType<typeof mountField>>;

async function mountField(
  item: NativeExamItem = shortAnswerItem(),
  props: { disabled?: boolean } = {},
) {
  const wrapper = mount(ExamWorkspaceShortAnswerField, {
    props: { item, ...props },
    attachTo: document.body,
  });
  await nextTick();
  await nextTick();
  return wrapper;
}

function questionSurface(wrapper: FieldWrapper): HTMLElement {
  return wrapper.get('[data-test="exam-workspace-short-answer-question"]')
    .element as HTMLElement;
}

function questionEditor(wrapper: FieldWrapper): Editor {
  const { editor } = questionSurface(wrapper) as HTMLElement & { editor?: Editor };
  if (!editor) {
    throw new Error("the Fråga editor did not mount");
  }
  return editor;
}

function svarInputs(wrapper: FieldWrapper): HTMLInputElement[] {
  const rows: HTMLInputElement[] = [];
  wrapper.element
    .querySelectorAll('[data-test="exam-workspace-short-answer-values-input"]')
    .forEach((row: Element) => {
      if (row instanceof HTMLInputElement) {
        rows.push(row);
      }
    });
  return rows;
}

type UpdateBodyEvent = [string, NativeExamBodyParagraph[], boolean];

describe("ExamWorkspaceShortAnswerField", () => {
  it("shows only the question text in Fråga, with no gap chip and no gap button", async () => {
    const wrapper = await mountField();

    expect(wrapper.find('[data-test="exam-workspace-short-answer"]').exists()).toBe(true);
    expect(questionSurface(wrapper).textContent).toContain(QUESTION);
    expect(wrapper.element.querySelector('[data-atom="gap"]')).toBeNull();
    expect(
      wrapper.find('[data-test="exam-workspace-toolbar-make-gap"]').exists(),
    ).toBe(false);
    wrapper.unmount();
  });

  it("emits an updateBody that ends with the unchanged gap paragraph, keeping the gap record", async () => {
    const item = shortAnswerItem();
    const wrapper = await mountField(item);
    const editor = questionEditor(wrapper);

    editor.commands.insertContentAt(posIn(editor, "huvudstad", 9), "!");
    await nextTick();

    const updates = wrapper.emitted("updateBody") as UpdateBodyEvent[] | undefined;
    expect(updates?.length).toBeGreaterThan(0);
    const last = updates?.at(-1);
    expect(last?.[0]).toBe(ITEM_ID);
    expect(last?.[1]).toEqual([
      ...plainBody("Vad heter Sveriges huvudstad!?"),
      { heading_level: null, segments: [{ kind: "gap", gap_id: GAP_ID }] },
    ]);
    const updated = withBody(item, last?.[1] ?? []);
    expect(updated.gaps).toEqual(item.gaps);
    wrapper.unmount();
  });

  it("shows one Svar row per accepted answer and forwards a row change with the gap id", async () => {
    const wrapper = await mountField();

    expect(svarInputs(wrapper).map((row) => row.value)).toEqual(["Stockholm"]);
    const row = wrapper.find<HTMLInputElement>(
      '[data-test="exam-workspace-short-answer-values-input"]',
    );
    row.element.value = "Göteborg";
    await row.trigger("input");
    await row.trigger("change");

    expect(wrapper.emitted("updateGapValues")).toEqual([[ITEM_ID, GAP_ID, ["Göteborg"]]]);
    wrapper.unmount();
  });

  it("keeps an answer with a comma as one value", async () => {
    const wrapper = await mountField(shortAnswerItem(["salt, peppar"]));

    expect(svarInputs(wrapper).map((row) => row.value)).toEqual(["salt, peppar"]);
    wrapper.unmount();
  });

  it("emits removeAutomaticValue when an automatic answer is removed", async () => {
    const wrapper = await mountField(shortAnswerItem(["Stockholm"], ["Stokholm"]));

    await wrapper
      .get('[data-test="exam-workspace-gap-automatic-remove-Stokholm"]')
      .trigger("click");

    expect(wrapper.emitted("removeAutomaticValue")).toEqual([[ITEM_ID, GAP_ID, "Stokholm"]]);
    wrapper.unmount();
  });

  it("emits nothing while disabled", async () => {
    const wrapper = await mountField(shortAnswerItem(["Stockholm"], ["Stokholm"]), {
      disabled: true,
    });

    const row = wrapper.find<HTMLInputElement>(
      '[data-test="exam-workspace-short-answer-values-input"]',
    );
    row.element.value = "Göteborg";
    await row.trigger("input");
    await row.trigger("change");
    await wrapper
      .get('[data-test="exam-workspace-gap-automatic-remove-Stokholm"]')
      .trigger("click");

    expect(wrapper.emitted("updateBody")).toBeUndefined();
    expect(wrapper.emitted("updateGapValues")).toBeUndefined();
    expect(wrapper.emitted("removeAutomaticValue")).toBeUndefined();
    wrapper.unmount();
  });

  it("keeps the Fråga content when the store writes the emitted body back", async () => {
    const item = shortAnswerItem();
    const wrapper = await mountField(item);
    const editor = questionEditor(wrapper);

    editor.commands.insertContentAt(posIn(editor, "huvudstad", 9), "!");
    await nextTick();
    const updates = wrapper.emitted("updateBody") as UpdateBodyEvent[] | undefined;
    const written = updates?.at(-1)?.[1] ?? [];
    const emittedCount = updates?.length ?? 0;

    await wrapper.setProps({ item: { ...item, body: written } });
    await nextTick();
    await nextTick();

    expect(questionEditor(wrapper).getText()).toContain("huvudstad!?");
    expect((wrapper.emitted("updateBody") as UpdateBodyEvent[] | undefined)?.length).toBe(
      emittedCount,
    );
    wrapper.unmount();
  });
});
