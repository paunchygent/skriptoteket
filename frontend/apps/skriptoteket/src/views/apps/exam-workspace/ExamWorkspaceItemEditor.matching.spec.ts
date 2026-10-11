/**
 * Exam workspace item editor, matching fieldset.
 *
 * Expected behavior:
 *   A matching item shows numbered left rows with a text input and a select
 *   of lettered right entries; choosing an answer emits the full pair list in
 *   left order, clearing the last choice emits an empty list, an entry text
 *   edit emits its side and id, an incomplete key shows the inline guidance, a right entry in no pair keeps
 *   the key complete,
 *   and an empty entry text shows the entry hint.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceItemEditor from "./ExamWorkspaceItemEditor.vue";
import { INCOMPLETE_MATCH_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";

function mountEditor(item: NativeExamItem) {
  return mount(ExamWorkspaceItemEditor, {
    props: {
      attentionCount: 0,
      detailsOpen: false,
      item,
      position: 1,
      showNavigation: false,
      total: 1,
    },
  });
}

describe("ExamWorkspaceItemEditor matching fieldset", () => {
  it("renders both lists with the key preselected and the Swedish labels", () => {
    const wrapper = mountEditor(buildMatchingItem());

    expect(wrapper.text()).toContain("Matchning – välj rätt svar för varje rad");
    expect(wrapper.text()).toContain("Fråga 1");
    expect(wrapper.text()).toContain("Matchning");
    const select = wrapper.get<HTMLSelectElement>('[data-test="exam-workspace-match-pair-left_001"]');
    expect(select.attributes("aria-label")).toBe("Rätt svar för rad 1");
    expect(select.element.value).toBe("right_002");
    expect(select.findAll("option").map((option) => option.text())).toEqual([
      "Inget svar valt",
      "A – incarceration",
      "B – truancy",
      "C – disdain",
    ]);
    expect(
      wrapper.get<HTMLInputElement>('[data-test="exam-workspace-match-right-text-right_003"]').element
        .value,
    ).toBe("disdain");
    expect(wrapper.find('[data-test="exam-workspace-match-key-hint"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-match-hint"]').exists()).toBe(false);
  });

  it("emits the full pair list in left order when one answer changes", async () => {
    const wrapper = mountEditor(buildMatchingItem());

    await wrapper.get('[data-test="exam-workspace-match-pair-left_002"]').setValue("right_003");

    expect(wrapper.emitted("updateMatchPairs")).toEqual([
      [
        "item_001",
        [
          { left_id: "left_001", right_id: "right_002" },
          { left_id: "left_002", right_id: "right_003" },
          { left_id: "left_003", right_id: "right_003" },
        ],
      ],
    ]);
  });

  it("emits an empty pair list when the only choice is cleared", async () => {
    const wrapper = mountEditor(buildMatchingItemWithPairs([[2, 1]]));

    await wrapper.get('[data-test="exam-workspace-match-pair-left_002"]').setValue("");

    expect(wrapper.emitted("updateMatchPairs")).toEqual([["item_001", []]]);
  });

  it("shows the key guidance while a keyed item is incomplete", () => {
    const wrapper = mountEditor(
      buildMatchingItemWithPairs([
        [1, 2],
        [2, 2],
        [3, 3],
      ]),
    );

    expect(wrapper.get('[data-test="exam-workspace-match-key-hint"]').text()).toBe(
      INCOMPLETE_MATCH_KEY_GUIDANCE,
    );
  });

  it("offers an unpaired right entry as a choice without flagging the key", () => {
    const wrapper = mountEditor(buildMatchingItemWithDistractor());

    expect(wrapper.find('[data-test="exam-workspace-match-key-hint"]').exists()).toBe(false);
    expect(
      wrapper
        .get('[data-test="exam-workspace-match-pair-left_001"]')
        .findAll("option")
        .map((option) => option.text()),
    ).toContain("D – ferocious");
  });

  it("flags two left entries that choose the same right entry beside a distractor", () => {
    const wrapper = mountEditor(
      buildMatchingItemWithDistractor({
        answer_key: {
          correct_choice_ids: [],
          match_pairs: [
            { left_id: "left_001", right_id: "right_004" },
            { left_id: "left_002", right_id: "right_004" },
            { left_id: "left_003", right_id: "right_003" },
          ],
          origin: "teacher_authored",
        },
      }),
    );

    expect(wrapper.find('[data-test="exam-workspace-match-key-hint"]').exists()).toBe(true);
  });

  it("emits the side and id of an edited entry text", async () => {
    const wrapper = mountEditor(buildMatchingItem());

    await wrapper.get('[data-test="exam-workspace-match-left-text-left_001"]').setValue("skipping class");
    await wrapper.get('[data-test="exam-workspace-match-right-text-right_001"]').setValue("jail time");

    expect(wrapper.emitted("updateMatchEntryText")).toEqual([
      ["item_001", "left", "left_001", "skipping class"],
      ["item_001", "right", "right_001", "jail time"],
    ]);
  });

  it("marks an empty entry text with the hint", () => {
    const item = buildMatchingItem();
    const wrapper = mountEditor({
      ...item,
      match_left: item.match_left.map((entry) =>
        entry.left_id === "left_003" ? { ...entry, text: "" } : entry,
      ),
    });

    expect(wrapper.get('[data-test="exam-workspace-match-hint"]').text()).toBe(
      "En rad eller ett svar i matchningen saknar text.",
    );
    expect(
      wrapper.get('[data-test="exam-workspace-match-left-text-left_003"]').attributes("aria-invalid"),
    ).toBe("true");
  });
});
