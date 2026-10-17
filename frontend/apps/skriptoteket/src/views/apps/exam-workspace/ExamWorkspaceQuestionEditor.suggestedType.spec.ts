/**
 * Exam workspace question editor, suggested type.
 *
 * Expected behavior:
 *   A stored `suggested_kind` that differs from the question's type shows
 *   "Gör om till [typ]" beside Import, which changes the type in one click,
 *   and marks the same entry Förslag in Byt frågetyp. A suggestion equal to
 *   the current type, or none, shows neither.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const SUGGESTED = '[data-test="exam-workspace-suggested-type"]';

function freeTextItem(suggested: NativeExamItemKind | null): NativeExamItem {
  return {
    ...buildMatchingItem(),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    kind: "free_text",
    match_left: [],
    match_right: [],
    suggested_kind: suggested,
  };
}

const mounted: Array<{ unmount: () => void }> = [];

function mountEditor(item: NativeExamItem) {
  const wrapper = mount(ExamWorkspaceQuestionEditor, {
    attachTo: document.body,
    props: {
      item,
      label: "11",
      origin: "docx_import",
      parent: null,
      child: null,
      converting: false,
      disabled: false,
      notice: null,
      importOpen: false,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

describe("ExamWorkspaceQuestionEditor suggested type", () => {
  it("offers the stored suggested type in one click and marks it Förslag in Byt frågetyp", async () => {
    const wrapper = mountEditor(freeTextItem("gap_fill"));

    const offer = wrapper.get(SUGGESTED);
    expect(offer.text()).toBe("Gör om till Lucktext");
    await offer.trigger("click");
    expect(wrapper.emitted("changeType")).toEqual([["gap_fill"]]);

    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();
    const marked = [...document.querySelectorAll('[data-test="exam-workspace-type-suggested"]')];
    expect(marked).toHaveLength(1);
    expect(marked[0]!.closest('[data-test="exam-workspace-type-gap_fill"]')).not.toBeNull();
  });

  it.each([["free_text" as const], [null]])("offers nothing for the suggestion %s", async (suggested) => {
    const wrapper = mountEditor(freeTextItem(suggested));

    expect(wrapper.find(SUGGESTED).exists()).toBe(false);
    await wrapper.get('[data-test="exam-workspace-type"]').trigger("click");
    await flushPromises();
    expect(document.querySelector('[data-test="exam-workspace-type-suggested"]')).toBeNull();
  });
});
