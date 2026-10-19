/**
 * Question editor facit line on an unbuilt item.
 *
 * Expected behavior:
 *   An unbuilt (review_required + source_fallback) item that carries
 *   facit_text shows the existing facit line while the teacher reviews.
 *   The line stays hidden while the item converts and when there is no
 *   facit text. A built item with facit text keeps showing the line.
 */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import ExamWorkspaceQuestionEditor from "./ExamWorkspaceQuestionEditor.vue";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";

const FACIT_LINE = '[data-test="exam-workspace-original-facit"]';
const CRITERIA = '[data-test="exam-workspace-criteria"]';
const FACIT = "a) Svar: snö (R) + boll (R)\nb) Svar: skriv (R) + bar (A) + het (A)";

function unbuiltItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return buildFreeTextItem(1, {
    facit_text: FACIT,
    review: { confidence: null, parse_origin: "source_fallback", reasons: [], state: "review_required" },
    ...overrides,
  });
}

function mountEditor(item: NativeExamItem, converting = false) {
  return mount(ExamWorkspaceQuestionEditor, {
    props: {
      item,
      label: "1",
      origin: "digiexam_import",
      parent: null,
      child: null,
      converting,
      disabled: false,
      notice: null,
      importOpen: false,
    },
  });
}

describe("ExamWorkspaceQuestionEditor unbuilt facit line", () => {
  it("shows the facit line on an unbuilt item that has facit text", () => {
    const item = unbuiltItem();
    expect(examWorkspaceItemReadiness(item)).toContain("unbuilt_question");

    const wrapper = mountEditor(item);
    expect(wrapper.find(CRITERIA).exists()).toBe(false);
    expect(wrapper.find(FACIT_LINE).exists()).toBe(true);
    expect(wrapper.get(FACIT_LINE).text()).toContain("Facit ur provfilen:");
    expect(wrapper.get(FACIT_LINE).text()).toContain("snö (R) + boll (R)");
    expect(wrapper.get(FACIT_LINE).text()).toContain("skriv (R) + bar (A) + het (A)");
  });

  it("hides the facit line while an unbuilt item converts", () => {
    const wrapper = mountEditor(unbuiltItem(), true);
    expect(wrapper.find(FACIT_LINE).exists()).toBe(false);
  });

  it("hides the facit line on an unbuilt item without facit text", () => {
    const wrapper = mountEditor(unbuiltItem({ facit_text: null }));
    expect(wrapper.find(FACIT_LINE).exists()).toBe(false);
  });

  it("keeps the facit line on a built item with facit text", () => {
    const item = unbuiltItem({
      review: { confidence: 0.9, parse_origin: "deterministic", reasons: [], state: "review_complete" },
    });
    expect(examWorkspaceItemReadiness(item)).not.toContain("unbuilt_question");

    const wrapper = mountEditor(item);
    expect(wrapper.get(FACIT_LINE).text()).toContain("Facit ur provfilen:");
    expect(wrapper.get(FACIT_LINE).text()).toContain("snö (R) + boll (R)");
  });
});
