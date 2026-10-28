/**
 * Exam workspace points field, an ordering question inside a part
 * (TASK-SKRIPT-39-06-11 D1).
 *
 * Expected behavior:
 *   An ordering question inside a part always takes the 1 point Exam.net
 *   gives it: the points input is read-only, its tooltip says why, and a note
 *   beside the field states the rule. The note takes the place of the
 *   estimated-points cue. A standalone ordering question keeps an editable
 *   points field and shows no note.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspacePointsField from "./ExamWorkspacePointsField.vue";
import { PART_ORDERING_POINTS_LOCKED_TITLE, PART_ORDERING_POINTS_NOTE } from "./examWorkspaceItemSaveRules";
import { newTeacherItem } from "./examWorkspaceItemEdits";

const INPUT = '[data-test="exam-workspace-item-points-input"]';
const NOTE = '[data-test="exam-workspace-points-part-ordering"]';
const ESTIMATED = '[data-test="exam-workspace-points-estimated"]';

const mounted: Array<VueWrapper> = [];

function orderingItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return { ...newTeacherItem("item_001", 1, "ordering"), ...overrides };
}

function mountField(item: NativeExamItem, lockedInPart = false): VueWrapper {
  const wrapper = mount(ExamWorkspacePointsField, {
    props: { converting: false, disabled: false, item, lockedInPart },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspacePointsField ordering inside a part", () => {
  it("locks an ordering child's points field with the note and its tooltip", () => {
    const wrapper = mountField(orderingItem({ points: 1 }), true);

    const input = wrapper.get(INPUT);
    expect(input.attributes("readonly")).toBeDefined();
    expect(input.attributes("title")).toBe(PART_ORDERING_POINTS_LOCKED_TITLE);

    const note = wrapper.get(NOTE);
    expect(note.text()).toBe(PART_ORDERING_POINTS_NOTE);
    expect(note.classes()).toContain("xw-hint");
    expect(note.classes()).toContain("pts__msg");
    expect(note.find("svg.lucide-info").exists()).toBe(true);
    expect(input.attributes("aria-describedby")).toBe(note.attributes("id"));
  });

  it("keeps a standalone ordering question's points field editable with no note", () => {
    const wrapper = mountField(orderingItem({ points: 1 }), false);

    const input = wrapper.get(INPUT);
    expect(input.attributes("readonly")).toBeUndefined();
    expect(input.attributes("title")).toBeUndefined();
    expect(wrapper.find(NOTE).exists()).toBe(false);
  });

  it("shows the part note instead of the estimated-points cue", () => {
    const wrapper = mountField(orderingItem({ points: 1, points_estimated: true }), true);

    expect(wrapper.find(NOTE).exists()).toBe(true);
    expect(wrapper.find(ESTIMATED).exists()).toBe(false);
  });

  it("still shows the estimated-points cue for a standalone ordering question", () => {
    const wrapper = mountField(orderingItem({ points: 1, points_estimated: true }), false);

    expect(wrapper.find(ESTIMATED).exists()).toBe(true);
    expect(wrapper.find(NOTE).exists()).toBe(false);
  });
});
