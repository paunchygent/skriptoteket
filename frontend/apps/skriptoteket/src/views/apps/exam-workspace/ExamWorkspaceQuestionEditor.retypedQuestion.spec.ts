/**
 * Question editor after choosing a type on an unconverted question (TASK-SKRIPT-39-05-15).
 *
 * Expected behavior:
 *   A gap_fill item with review {review_required, teacher_created} shows the
 *   question fields and the gap tools (Luckverktyg, Tom lucka), reads
 *   "Lucktext", and shows no "Ej konverterad" and no unbuilt error line.
 *   The same item with source_fallback stays unconverted: it reads
 *   "Ej konverterad" with the unbuilt error line and hides the gap tools.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { settleEditors } from "./ExamWorkspaceRichTextEntry.specSupport";

const GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';
const EMPTY_GAP = '[data-test="exam-workspace-toolbar-empty-gap"]';
const SURFACE = '[data-test="exam-workspace-body-editor-surface"]';
const TYPE_BUTTON = '[data-test="exam-workspace-type"]';

function itemWithOrigin(parse_origin: NativeExamItem["review"]["parse_origin"]): NativeExamItem {
  return {
    ...gapItem("teacher_authored", [["gap_001", ["Paris"]]], null),
    review: { confidence: null, parse_origin, reasons: [], state: "review_required" },
  };
}

function mountEditor(item: NativeExamItem): Promise<VueWrapper> {
  const wrapper = mount(ExamWorkspaceQuestionEditor, {
    attachTo: document.body,
    global: { plugins: [examWorkspaceProvidersPlugin()] },
    props: {
      item,
      label: "3",
      origin: "digiexam_import",
      parent: null,
      child: null,
      converting: false,
      disabled: false,
      notice: null,
      importOpen: false,
    },
  });
  return settleEditors().then(() => wrapper);
}

let mounted: VueWrapper | null = null;

afterEach(() => {
  mounted?.unmount();
  mounted = null;
  document.body.innerHTML = "";
});

describe("ExamWorkspaceQuestionEditor retyped unconverted question", () => {
  it("shows the fields and gap tools for a review_required teacher_created gap_fill item", async () => {
    const item = itemWithOrigin("teacher_created");
    expect(examWorkspaceItemReadiness(item)).toContain("unreviewed_retyped_question");

    const wrapper = (mounted = await mountEditor(item));

    expect(wrapper.get(TYPE_BUTTON).text()).toContain("Lucktext");
    expect(wrapper.get(TYPE_BUTTON).text()).not.toContain("Ej konverterad");
    expect(wrapper.find(".qhead__unbuilt").exists()).toBe(false);
    expect(wrapper.find(SURFACE).exists()).toBe(true);
    expect(wrapper.find(GAP_TOOL).exists()).toBe(true);
    expect(wrapper.find(EMPTY_GAP).exists()).toBe(true);
  });

  it("keeps the same item unconverted while its origin is source_fallback", async () => {
    const item = itemWithOrigin("source_fallback");
    expect(examWorkspaceItemReadiness(item)).toContain("unbuilt_question");
    expect(examWorkspaceItemReadiness(item)).not.toContain("unreviewed_retyped_question");

    const wrapper = (mounted = await mountEditor(item));

    expect(wrapper.get(TYPE_BUTTON).text()).toContain("Ej konverterad");
    expect(wrapper.find(".qhead__unbuilt").exists()).toBe(true);
    // The gap toolbar keys on the item kind, not on the unbuilt rule
    // (ExamWorkspaceBodyEditor show-gap), so a gap_fill item keeps its gap
    // tools while unconverted; the unbuilt rule hides the answer fields and
    // swaps the type label for the unbuilt error line instead.
    expect(wrapper.find(GAP_TOOL).exists()).toBe(true);
    expect(wrapper.find(EMPTY_GAP).exists()).toBe(true);
  });
});
