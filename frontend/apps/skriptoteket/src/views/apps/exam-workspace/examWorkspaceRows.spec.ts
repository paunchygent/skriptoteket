/**
 * Exam workspace row-mapping behavior.
 *
 * Expected behavior:
 *   Native exam items map to Swedish type labels, question-number labels and
 *   prompt excerpts that keep gaps visible as fixed chips; review reason codes
 *   map to Swedish text.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspacePromptExcerpt,
  examWorkspaceQuestionLabel,
  examWorkspaceReviewReasonLabel,
  examWorkspaceTypeLabel,
} from "./examWorkspaceRows";

function buildItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv fotosyntesen." }] }],
    choices: [],
    gaps: [],
    item_id: "item_001",
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
    ...overrides,
  };
}

describe("examWorkspaceRows", () => {
  it("maps every item kind to the approved Swedish type label", () => {
    expect(examWorkspaceTypeLabel("free_text")).toBe("Fritext");
    expect(examWorkspaceTypeLabel("single_choice")).toBe("Flerval: ett val");
    expect(examWorkspaceTypeLabel("multiple_response")).toBe("Flerval: flera val");
    expect(examWorkspaceTypeLabel("gap_fill")).toBe("Lucktext");
    expect(examWorkspaceTypeLabel("matching")).toBe("Kategorisera");
    expect(examWorkspaceTypeLabel("inline_choice")).toBe("Lucktext med rullista");
  });

  it("flattens body segments into an excerpt with gap chips", () => {
    const item = buildItem({
      body: [
        { heading_level: null, segments: [
            { kind: "text", marks: [], text: "Vatten kokar vid" },
            { gap_id: "gap_001", kind: "gap" },
            { kind: "text", marks: [], text: "grader." },
          ],
        },
        { heading_level: null, segments: [{ kind: "text", marks: [], text: "Motivera ditt svar." }] },
      ],
      kind: "gap_fill",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspacePromptExcerpt(item)).toBe(
      "Vatten kokar vid [___] grader. Motivera ditt svar.",
    );
  });

  it("truncates long excerpts with an ellipsis", () => {
    const longText = "ord ".repeat(80).trim();
    const item = buildItem({
      body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: longText }] }],
    });

    const excerpt = examWorkspacePromptExcerpt(item);

    expect(excerpt.length).toBeLessThanOrEqual(140);
    expect(excerpt.endsWith("…")).toBe(true);
  });

  it("maps review reason codes to Swedish text and passes prose through", () => {
    expect(examWorkspaceReviewReasonLabel("machine_proposed_answer_key")).toBe(
      "Facit är ett maskinellt förslag – kontrollera det innan du godkänner.",
    );
    expect(examWorkspaceReviewReasonLabel("osäker tolkning av frågetexten")).toBe(
      "osäker tolkning av frågetexten",
    );
    const fallback = examWorkspaceReviewReasonLabel("some_future_code");
    expect(fallback).toBe("Kontrollera frågan – tolkningen är osäker.");
    expect(fallback).not.toContain("_");
  });

  it("labels every question with its question number", () => {
    expect(examWorkspaceQuestionLabel(4)).toBe("Fråga 4");
    expect(examWorkspaceQuestionLabel(12)).toBe("Fråga 12");
  });
});
