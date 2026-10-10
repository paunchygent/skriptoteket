/**
 * Exam workspace row-mapping behavior.
 *
 * Expected behavior:
 *   Native exam items map to teacher-facing table rows with Swedish type and
 *   review-status labels, locale-formatted points, title fallbacks, and prompt
 *   excerpts that keep gaps visible as fixed chips.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspacePointsLabel,
  examWorkspacePromptExcerpt,
  examWorkspaceReviewReasonLabel,
  examWorkspaceReviewStatusLabel,
  examWorkspaceTypeLabel,
  toExamWorkspaceItemRow,
  toExamWorkspaceItemRows,
} from "./examWorkspaceRows";

function buildItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: [], origin: "not_applicable" },
    body: [{ segments: [{ kind: "text", text: "Beskriv fotosyntesen." }] }],
    choices: [],
    gaps: [],
    item_id: "item_001",
    kind: "free_text",
    points: 2,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    title: "Fotosyntes",
    ...overrides,
  };
}

describe("examWorkspaceRows", () => {
  it("maps every item kind to the approved Swedish type label", () => {
    expect(examWorkspaceTypeLabel("free_text")).toBe("Fritext");
    expect(examWorkspaceTypeLabel("single_choice")).toBe("Flerval: ett val");
    expect(examWorkspaceTypeLabel("multiple_response")).toBe("Flerval: flera val");
    expect(examWorkspaceTypeLabel("gap_fill")).toBe("Lucktext");
  });

  it("maps review states to Swedish status labels", () => {
    expect(examWorkspaceReviewStatusLabel("review_required")).toBe("Behöver granskas");
    expect(examWorkspaceReviewStatusLabel("review_complete")).toBe("Granskad");
  });

  it("formats points with Swedish decimals and a dash for missing points", () => {
    expect(examWorkspacePointsLabel(null)).toBe("–");
    expect(examWorkspacePointsLabel(3)).toBe("3");
    expect(examWorkspacePointsLabel(2.5)).toBe("2,5");
  });

  it("flattens body segments into an excerpt with gap chips", () => {
    const item = buildItem({
      body: [
        {
          segments: [
            { kind: "text", text: "Vatten kokar vid" },
            { gap_id: "gap_001", kind: "gap" },
            { kind: "text", text: "grader." },
          ],
        },
        { segments: [{ kind: "text", text: "Motivera ditt svar." }] },
      ],
      kind: "gap_fill",
    });

    expect(examWorkspacePromptExcerpt(item)).toBe(
      "Vatten kokar vid [___] grader. Motivera ditt svar.",
    );
  });

  it("truncates long excerpts with an ellipsis", () => {
    const longText = "ord ".repeat(80).trim();
    const item = buildItem({
      body: [{ segments: [{ kind: "text", text: longText }] }],
    });

    const excerpt = examWorkspacePromptExcerpt(item);

    expect(excerpt.length).toBeLessThanOrEqual(140);
    expect(excerpt.endsWith("…")).toBe(true);
  });

  it("maps review reason codes to Swedish text and passes prose through", () => {
    expect(examWorkspaceReviewReasonLabel("long_answer_key")).toBe(
      "Facit är längre än vanligt – kontrollera att det bara innehåller svaret.",
    );
    expect(examWorkspaceReviewReasonLabel("missing_points")).toBe(
      "Poäng saknas – ange poäng för frågan.",
    );
    expect(examWorkspaceReviewReasonLabel("osäker tolkning av frågetexten")).toBe(
      "osäker tolkning av frågetexten",
    );
    const fallback = examWorkspaceReviewReasonLabel("some_future_code");
    expect(fallback).toBe("Kontrollera frågan – tolkningen är osäker.");
    expect(fallback).not.toContain("_");
  });

  it("builds a complete row and falls back to a sequence title", () => {
    const row = toExamWorkspaceItemRow(
      buildItem({
        points: null,
        review: {
          confidence: 0.4,
          parse_origin: "llm_parsed",
          reasons: ["osäker tolkning av frågetexten"],
          state: "review_required",
        },
        sequence: 4,
        title: null,
      }),
    );

    expect(row).toEqual({
      itemId: "item_001",
      pointsLabel: "–",
      promptExcerpt: "Beskriv fotosyntesen.",
      reviewReasons: ["osäker tolkning av frågetexten"],
      reviewRequired: true,
      sequence: 4,
      statusLabel: "Behöver granskas",
      title: "Fråga 4",
      typeLabel: "Fritext",
    });
  });

  it("maps item lists in order", () => {
    const rows = toExamWorkspaceItemRows([
      buildItem(),
      buildItem({ item_id: "item_002", kind: "single_choice", sequence: 2 }),
    ]);

    expect(rows.map((row) => row.itemId)).toEqual(["item_001", "item_002"]);
    expect(rows[1]?.typeLabel).toBe("Flerval: ett val");
  });
});
