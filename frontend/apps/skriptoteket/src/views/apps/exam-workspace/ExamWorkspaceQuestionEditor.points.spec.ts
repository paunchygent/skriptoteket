/**
 * Exam workspace question editor, estimated points cue.
 *
 * Expected behavior:
 *   Points the import spread from the section total show an inline,
 *   nonblocking "Uppskattad utifrån avsnittets totalpoäng" cue tied to the
 *   points input. Teacher-set, missing and negative points show none, and the
 *   points a teacher types are emitted so the item stops being an estimate.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { withPoints } from "./examWorkspaceItemEdits";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const CUE = '[data-test="exam-workspace-points-estimated"]';
const INPUT = '[data-test="exam-workspace-item-points-input"]';

function buildItem(overrides: Partial<NativeExamItem>): NativeExamItem {
  return {
    ...buildMatchingItem(),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    kind: "free_text",
    match_left: [],
    match_right: [],
    ...overrides,
  };
}

function mountEditor(item: NativeExamItem) {
  return mount(ExamWorkspaceQuestionEditor, {
    props: { item, label: "1", origin: "digiexam_import", parent: null, child: null, converting: false, disabled: false, notice: null, importOpen: false },
  });
}

describe("ExamWorkspaceQuestionEditor estimated points", () => {
  it("shows the cue, tied to the input, for estimated points", () => {
    const wrapper = mountEditor(buildItem({ points: 2, points_estimated: true }));

    const cue = wrapper.get(CUE);
    expect(cue.text()).toContain("Uppskattad utifrån avsnittets totalpoäng");
    expect(wrapper.get(INPUT).attributes("aria-describedby")).toBe(cue.attributes("id"));
    expect(wrapper.get(INPUT).attributes("aria-invalid")).toBeUndefined();
  });

  it("shows no cue for teacher-set, missing or negative points", () => {
    expect(mountEditor(buildItem({ points: 2, points_estimated: false })).find(CUE).exists()).toBe(false);
    expect(mountEditor(buildItem({ points: null, points_estimated: true })).find(CUE).exists()).toBe(false);
    expect(mountEditor(buildItem({ points: -1, points_estimated: true })).find(CUE).exists()).toBe(false);
  });

  it("emits typed points, which the edit marks as no longer estimated", async () => {
    const item = buildItem({ points: 2, points_estimated: true });
    const wrapper = mountEditor(item);

    await wrapper.get(INPUT).setValue("3");

    const [itemId, points] = wrapper.emitted("updatePoints")![0] as [string, number];
    expect(points).toBe(3);
    const updated = withPoints(item, points);
    expect(itemId).toBe(item.item_id);
    expect(updated.points_estimated).toBe(false);
    await wrapper.setProps({ item: updated });
    expect(wrapper.find(CUE).exists()).toBe(false);
  });
});
