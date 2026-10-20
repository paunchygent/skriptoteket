/**
 * Question editor for a Lucktext retyped from an unconverted question
 * (TASK-SKRIPT-39-05-15 D9, staging 99378586 exam 996a684f item_006).
 *
 * Expected behavior:
 *   The item the server returns after retyping a free_text source_fallback
 *   question ("Ange bisatsens typ") to Lucktext — kind gap_fill, the
 *   `single_text_paragraph_gets_separator` expected body from the shared
 *   placement table, no answers, and review {review_required,
 *   teacher_retyped} — shows ExamWorkspaceBodyEditor with the gap tools
 *   (Luckverktyg and Tom lucka), not ExamWorkspaceShortAnswerField, and the
 *   type label reads "Lucktext" (not "Kort svar", not "Ej konverterad").
 *   The contrast is the staging failure mode: the same text with the gap
 *   alone in its own last paragraph is a Kort svar, so it renders the Kort
 *   svar field and no Luckverktyg.
 */

import { mount } from "@vue/test-utils";
import type { VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import placementTable from "../../../../../../../tests/fixtures/exam_workspace/gap_text_placement_cases.json";

import type {
  NativeExamBodyParagraph,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";
import { settleEditors } from "./ExamWorkspaceRichTextEntry.specSupport";
import { isShortAnswer } from "./examWorkspaceShortAnswer";

const GAP_TOOL = '[data-test="exam-workspace-toolbar-gap-tool"]';
const EMPTY_GAP = '[data-test="exam-workspace-toolbar-empty-gap"]';
const BODY_EDITOR = '[data-test="exam-workspace-body-editor"]';
const SHORT_ANSWER = '[data-test="exam-workspace-short-answer"]';
const TYPE_BUTTON = '[data-test="exam-workspace-type"]';

// The shared placement table arrives as a JSON module import (resolveJsonModule
// is on); the type guard below validates it at the boundary.
const fixtureTable: unknown = placementTable;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isParagraph(value: unknown): value is NativeExamBodyParagraph {
  return isRecord(value) && Array.isArray(value.segments);
}

function toParagraphs(value: unknown): NativeExamBodyParagraph[] | null {
  if (!Array.isArray(value) || !value.every(isParagraph)) {
    return null;
  }
  return value.filter(isParagraph);
}

function readCase(caseName: string): {
  question: NativeExamBodyParagraph[];
  expected: NativeExamBodyParagraph[];
} {
  const parsed: unknown = fixtureTable;
  if (!isRecord(parsed) || !Array.isArray(parsed.cases)) {
    throw new Error("invalid gap placement case table at gap_text_placement_cases.json");
  }
  for (const entry of parsed.cases) {
    if (!isRecord(entry) || entry.name !== caseName) {
      continue;
    }
    const question = toParagraphs(entry.question);
    const expected = toParagraphs(entry.expected);
    if (question !== null && expected !== null) {
      return { expected, question };
    }
  }
  throw new Error(`missing case ${caseName} in the gap placement case table`);
}

const SINGLE_CASE = readCase("single_text_paragraph_gets_separator");

/** The server's retyped item: a gap_fill Lucktext with no answers awaiting review. */
function retypedGapTextItem(body: NativeExamBodyParagraph[]): NativeExamItem {
  return {
    ...gapItem("absent", [["gap_001", []]], null),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body,
    kind: "gap_fill",
    review: { confidence: null, parse_origin: "teacher_retyped", reasons: [], state: "review_required" },
  };
}

function mountEditor(item: NativeExamItem): Promise<VueWrapper> {
  const wrapper = mount(ExamWorkspaceQuestionEditor, {
    attachTo: document.body,
    global: { plugins: [examWorkspaceProvidersPlugin()] },
    props: {
      item,
      label: "3a",
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

describe("ExamWorkspaceQuestionEditor retyped gap text (D9 staging case)", () => {
  it("shows the body editor with the gap tools and the Lucktext label for the retyped item", async () => {
    const item = retypedGapTextItem(SINGLE_CASE.expected);
    expect(isShortAnswer(item)).toBe(false);
    expect(examWorkspaceItemReadiness(item)).toContain("unreviewed_retyped_question");
    expect(examWorkspaceItemReadiness(item)).not.toContain("unbuilt_question");

    const wrapper = (mounted = await mountEditor(item));

    expect(wrapper.get(TYPE_BUTTON).text()).toContain("Lucktext");
    expect(wrapper.get(TYPE_BUTTON).text()).not.toContain("Kort svar");
    expect(wrapper.get(TYPE_BUTTON).text()).not.toContain("Ej konverterad");
    expect(wrapper.find(".qhead__unbuilt").exists()).toBe(false);
    expect(wrapper.find(BODY_EDITOR).exists()).toBe(true);
    expect(wrapper.find(SHORT_ANSWER).exists()).toBe(false);
    expect(wrapper.find(GAP_TOOL).exists()).toBe(true);
    expect(wrapper.find(EMPTY_GAP).exists()).toBe(true);
  });

  it("renders the Kort svar field with no Luckverktyg when the gap stands alone in its own last paragraph", async () => {
    const item = retypedGapTextItem([
      ...SINGLE_CASE.question,
      { heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] },
    ]);
    expect(isShortAnswer(item)).toBe(true);

    const wrapper = (mounted = await mountEditor(item));

    expect(wrapper.find(SHORT_ANSWER).exists()).toBe(true);
    expect(wrapper.find(BODY_EDITOR).exists()).toBe(false);
    expect(wrapper.find(GAP_TOOL).exists()).toBe(false);
  });
});
