/**
 * Exam workspace question editor, Fritext criteria.
 *
 * Expected behavior:
 *   A free-text item shows its criteria with text and whole points. Adding
 *   the first criterion takes the question's whole points, so the total does
 *   not change; later criteria start at 1 point. Editing a text or valid
 *   points emits the full list; points that are not a whole number of at
 *   least 1 are marked and never emitted. While criteria exist, the question
 *   points are read-only. An added row's text field takes focus once the new
 *   list arrives, and leaving invalid points restores the last valid points.
 *   Other kinds show no criteria.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { EMPTY_CRITERION_TEXT_GUIDANCE } from "./examWorkspaceItemSaveRules";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const CRITERIA = '[data-test="exam-workspace-criteria"]';
const ADD = '[data-test="exam-workspace-criterion-add"]';
const POINTS = '[data-test="exam-workspace-item-points-input"]';

function buildFreeTextItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...buildMatchingItem(),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    kind: "free_text",
    match_left: [],
    match_right: [],
    criteria: [],
    points: 4,
    ...overrides,
  };
}

function mountEditor(item: NativeExamItem, options: { attachTo?: HTMLElement } = {}) {
  return mount(ExamWorkspaceQuestionEditor, {
    ...options,
    props: {
      item,
      label: "1",
      origin: "digiexam_import",
      parent: null,
      child: null,
      suggestedKind: null,
      converting: false,
      disabled: false,
      notice: null,
      importOpen: false,
      lastChildDeletable: false,
    },
  });
}

const TWO_CRITERIA = [
  { text: "Nämner orsaken", points: 1 },
  { text: "Förklarar följden", points: 2 },
];

describe("ExamWorkspaceQuestionEditor Fritext criteria", () => {
  it("adds a first criterion worth the question's whole points", async () => {
    const wrapper = mountEditor(buildFreeTextItem());

    expect(wrapper.get<HTMLInputElement>(POINTS).attributes("readonly")).toBeUndefined();
    await wrapper.get(ADD).trigger("click");

    expect(wrapper.emitted("updateCriteria")).toEqual([["item_001", [{ text: "", points: 4 }]]]);
  });

  it("adds a first criterion worth 1 point when the points are not whole", async () => {
    const wrapper = mountEditor(buildFreeTextItem({ points: 2.5 }));

    await wrapper.get(ADD).trigger("click");

    expect(wrapper.emitted("updateCriteria")).toEqual([["item_001", [{ text: "", points: 1 }]]]);
  });

  it("adds later criteria at 1 point and keeps the points read-only", async () => {
    const wrapper = mountEditor(buildFreeTextItem({ criteria: TWO_CRITERIA, points: 3 }));

    expect(wrapper.get(POINTS).attributes("readonly")).toBeDefined();
    await wrapper.get(ADD).trigger("click");

    expect(wrapper.emitted("updateCriteria")).toEqual([
      ["item_001", [...TWO_CRITERIA, { text: "", points: 1 }]],
    ]);
  });

  it("emits the full list when a text or valid points change", async () => {
    const wrapper = mountEditor(buildFreeTextItem({ criteria: TWO_CRITERIA, points: 3 }));

    await wrapper.get('[data-test="exam-workspace-criterion-text-0"]').setValue("Nämner två orsaker");
    await wrapper.get('[data-test="exam-workspace-criterion-points-1"]').setValue("3");

    expect(wrapper.emitted("updateCriteria")).toEqual([
      ["item_001", [{ text: "Nämner två orsaker", points: 1 }, TWO_CRITERIA[1]]],
      ["item_001", [TWO_CRITERIA[0], { text: "Förklarar följden", points: 3 }]],
    ]);
  });

  it("marks points that are not a whole number of at least 1 and emits nothing", async () => {
    const wrapper = mountEditor(buildFreeTextItem({ criteria: TWO_CRITERIA, points: 3 }));
    const points = wrapper.get('[data-test="exam-workspace-criterion-points-0"]');

    await points.setValue("0");
    expect(points.attributes("aria-invalid")).toBe("true");
    await points.setValue("1.5");

    expect(points.attributes("aria-invalid")).toBe("true");
    expect(wrapper.find('[data-test="exam-workspace-criterion-points-hint"]').exists()).toBe(true);
    expect(wrapper.emitted("updateCriteria")).toBeUndefined();
  });

  it("focuses the added row's text field when the new list arrives", async () => {
    const item = buildFreeTextItem({ criteria: TWO_CRITERIA, points: 3 });
    const wrapper = mountEditor(item, { attachTo: document.body });

    await wrapper.get(ADD).trigger("click");
    const [[, criteria]] = wrapper.emitted("updateCriteria") as [[string, typeof TWO_CRITERIA]];
    await wrapper.setProps({ item: { ...item, criteria, points: 4 } });
    await nextTick();

    expect(document.activeElement).toBe(
      wrapper.get('[data-test="exam-workspace-criterion-text-2"]').element,
    );
    wrapper.unmount();
  });

  it("restores the last valid points and clears the mark when invalid points lose focus", async () => {
    const wrapper = mountEditor(buildFreeTextItem({ criteria: TWO_CRITERIA, points: 3 }));
    const points = wrapper.get<HTMLInputElement>('[data-test="exam-workspace-criterion-points-1"]');

    await points.setValue("0");
    await points.trigger("blur");

    expect(points.element.value).toBe("2");
    expect(points.attributes("aria-invalid")).toBeUndefined();
    expect(wrapper.find('[data-test="exam-workspace-criterion-points-hint"]').exists()).toBe(false);
    expect(wrapper.emitted("updateCriteria")).toBeUndefined();
  });

  it("removes one criterion by its trash control", async () => {
    const wrapper = mountEditor(buildFreeTextItem({ criteria: TWO_CRITERIA, points: 3 }));

    const remove = wrapper.get('[data-test="exam-workspace-criterion-remove-0"]');
    expect(remove.attributes("aria-label")).toBe("Ta bort kriterium 1");
    await remove.trigger("click");

    expect(wrapper.emitted("updateCriteria")).toEqual([["item_001", [TWO_CRITERIA[1]]]]);
  });

  it("marks a criterion without text with the hint", () => {
    const wrapper = mountEditor(
      buildFreeTextItem({ criteria: [{ text: " ", points: 1 }], points: 1 }),
    );

    expect(wrapper.get('[data-test="exam-workspace-criterion-text-hint"]').text()).toBe(
      EMPTY_CRITERION_TEXT_GUIDANCE,
    );
  });

  it("shows no criteria on a matching item", () => {
    const wrapper = mountEditor(buildMatchingItem());

    expect(wrapper.find(CRITERIA).exists()).toBe(false);
  });
});
