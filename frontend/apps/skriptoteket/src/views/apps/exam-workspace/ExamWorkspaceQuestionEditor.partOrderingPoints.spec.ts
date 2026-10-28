/**
 * Exam workspace question editor, the points field of an ordering question
 * inside a part (TASK-SKRIPT-39-06-11 D1).
 *
 * Expected behavior:
 *   The editor locks the points field of a deluppgift that is an ordering
 *   question, with the note that Exam.net gives it 1 point, and leaves the
 *   field editable for a standalone ordering question and for a child of
 *   another kind. The client computes no points; the command's document
 *   carries the 1 point.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

const INPUT = '[data-test="exam-workspace-item-points-input"]';
const NOTE = '[data-test="exam-workspace-points-part-ordering"]';

const PARENT = { id: "parent_001", label: "2", text: "Delinstruktion" };
const CHILD = { index: 0, count: 2 };

const mounted: Array<VueWrapper> = [];

function mountEditor(
  item: NativeExamItem,
  child: { index: number; count: number } | null,
): VueWrapper {
  const wrapper = mount(ExamWorkspaceQuestionEditor, {
    global: { plugins: [examWorkspaceProvidersPlugin()] },
    props: {
      assetUrls: undefined,
      child,
      converting: false,
      disabled: false,
      importOpen: false,
      item,
      label: "3",
      notice: null,
      origin: "created",
      parent: child === null ? null : PARENT,
    },
  });
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("ExamWorkspaceQuestionEditor ordering points inside a part", () => {
  it("locks the points field of an ordering deluppgift and shows the note", () => {
    const wrapper = mountEditor(newTeacherItem("item_001", 1, "ordering"), CHILD);

    expect(wrapper.get(INPUT).attributes("readonly")).toBeDefined();
    expect(wrapper.find(NOTE).exists()).toBe(true);
  });

  it("keeps a standalone ordering question's points field editable with no note", () => {
    const wrapper = mountEditor(newTeacherItem("item_001", 1, "ordering"), null);

    expect(wrapper.get(INPUT).attributes("readonly")).toBeUndefined();
    expect(wrapper.find(NOTE).exists()).toBe(false);
  });

  it("keeps a deluppgift of another kind editable with no note", () => {
    const wrapper = mountEditor(newTeacherItem("item_001", 1, "free_text"), CHILD);

    expect(wrapper.get(INPUT).attributes("readonly")).toBeUndefined();
    expect(wrapper.find(NOTE).exists()).toBe(false);
  });
});
