/**
 * Exam workspace item save rules.
 *
 * Expected behavior:
 *   The save refusal copy names every question that breaks a server item
 *   rule, one sentence group per rule in a stable order (partial gap key,
 *   negative or non-finite points, choice without text, criteria that lack
 *   text or points or are not the item's points), and is `null` when
 *   the server would accept every item.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  CRITERIA_ON_WRONG_KIND_GUIDANCE,
  CRITERIA_POINTS_MISMATCH_GUIDANCE,
  examWorkspaceSaveRefusalCopy,
  INVALID_CRITERION_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { INCOMPLETE_MATCH_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import { plainBody } from "./examWorkspaceRichText";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";

function buildChoiceItem(
  sequence: number,
  overrides: Partial<NativeExamItem> = {},
): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: ["choice_001"], match_pairs: [], origin: "teacher_authored" },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Vilket ämne är en gas?" }] }],
    choices: [
      { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
      { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Järn" }] }] },
    ],
    gaps: [],
    item_id: `item_00${sequence}`,
    kind: "single_choice",
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: null,
    ...overrides,
  };
}

const EMPTY_CHOICES = [
  { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
  { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "" }] }] },
] satisfies NativeExamItem["choices"];

describe("examWorkspaceSaveRefusalCopy", () => {
  it("is null when every item can be saved, including missing points", () => {
    expect(
      examWorkspaceSaveRefusalCopy([buildChoiceItem(1), buildChoiceItem(2, { points: null })]),
    ).toBeNull();
  });

  it("accepts zero points", () => {
    expect(examWorkspaceSaveRefusalCopy([buildChoiceItem(1, { points: 0 })])).toBeNull();
  });

  it.each([-1, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    "refuses invalid points %s",
    (points) => {
      expect(examWorkspaceSaveRefusalCopy([buildChoiceItem(1, { points })])).not.toBeNull();
    },
  );

  it("names one question with negative points", () => {
    expect(examWorkspaceSaveRefusalCopy([buildChoiceItem(1, { points: -1 })])).toBe(
      "Fråga 1 har negativa poäng. Poängen kan inte vara negativ.",
    );
  });

  it("names every question in each rule, rule by rule", () => {
    const items = [
      buildChoiceItem(1, { points: -1 }),
      buildChoiceItem(2, { choices: EMPTY_CHOICES }),
      buildChoiceItem(3, { choices: EMPTY_CHOICES, points: -1 }),
    ];

    // An empty choice saves (TASK-SKRIPT-40-04-06 D3); only the negative points refuse.
    expect(examWorkspaceSaveRefusalCopy(items)).toBe(
      "Frågorna 1 och 3 har negativa poäng. Poängen kan inte vara negativ.",
    );
  });
});

describe("examWorkspaceSaveRefusalCopy for matching items", () => {
  it("is null for a fully keyed matching item", () => {
    expect(examWorkspaceSaveRefusalCopy([buildMatchingItem()])).toBeNull();
  });

  it("is null for a keyed matching item with an unpaired right entry", () => {
    expect(examWorkspaceSaveRefusalCopy([buildMatchingItemWithDistractor()])).toBeNull();
  });

  it("is null once every pair is cleared and the key becomes absent", () => {
    const item = buildMatchingItemWithPairs([]);

    expect(
      examWorkspaceSaveRefusalCopy([
        { ...item, points: 0, answer_key: { ...item.answer_key, origin: "absent" } },
      ]),
    ).toBeNull();
  });

  it("refuses a keyed item missing one pair with the matching guidance", () => {
    expect(
      examWorkspaceSaveRefusalCopy([
        buildMatchingItemWithPairs([
          [1, 2],
          [2, 1],
        ]),
      ]),
    ).toBe(
      `Fråga 1 har en kategorisering där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`,
    );
  });

  it("refuses a keyed item with a repeated tick", () => {
    expect(
      examWorkspaceSaveRefusalCopy([
        buildMatchingItemWithPairs([
          [1, 2],
          [1, 2],
          [2, 1],
          [3, 3],
        ]),
      ]),
    ).toBe(
      `Fråga 1 har en kategorisering där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`,
    );
  });

  it("saves an empty left or right entry text", () => {
    const item = buildMatchingItem();
    const emptyLeft = {
      ...item,
      match_left: item.match_left.map((entry) =>
        entry.left_id === "left_002" ? { ...entry, body: plainBody("") } : entry,
      ),
    };

    expect(examWorkspaceSaveRefusalCopy([emptyLeft])).toBeNull();
    expect(examWorkspaceSaveRefusalCopy([{ ...emptyLeft, match_left: emptyLeft.match_left.map((entry) => ({ ...entry, body: [] })) }])).toBeNull();
  });
});

function buildCriteriaItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...buildChoiceItem(1, {
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
      choices: [],
      kind: "free_text",
      points: 3,
    }),
    criteria: [
      { points: 2, text: "Definition" },
      { points: 1, text: "Exempel" },
    ],
    ...overrides,
  };
}

describe("examWorkspaceSaveRefusalCopy for free-text criteria", () => {
  it("is null when a non-empty criteria list sums to the item's points", () => {
    expect(examWorkspaceSaveRefusalCopy([buildCriteriaItem()])).toBeNull();
  });

  it("is null for a free-text item without criteria", () => {
    expect(examWorkspaceSaveRefusalCopy([buildCriteriaItem({ criteria: [] })])).toBeNull();
  });

  it("refuses a criterion whose text is empty or whitespace only", () => {
    const empty = buildCriteriaItem({
      criteria: [
        { points: 2, text: "" },
        { points: 1, text: "Exempel" },
      ],
    });
    const blank = buildCriteriaItem({
      criteria: [
        { points: 2, text: " \n\t " },
        { points: 1, text: "Exempel" },
      ],
      item_id: "item_002",
      sequence: 2,
    });

    expect(examWorkspaceSaveRefusalCopy([empty, blank])).toBe(
      "Frågorna 1 och 2 har ett kriterium utan text. Skriv text i varje kriterium.",
    );
  });

  it("refuses criterion points that are not whole or at least 1", () => {
    const item = buildCriteriaItem({
      criteria: [
        { points: 1.5, text: "Definition" },
        { points: 1.5, text: "Exempel" },
      ],
    });

    expect(examWorkspaceSaveRefusalCopy([item])).toBe(
      `Fråga 1 har ett kriterium med ogiltiga poäng. ${INVALID_CRITERION_POINTS_GUIDANCE}`,
    );
  });

  it("refuses a criteria sum that is not the item's points", () => {
    expect(examWorkspaceSaveRefusalCopy([buildCriteriaItem({ points: 2 })])).toBe(
      `Fråga 1 har kriterier vars poängsumma inte stämmer med frågans poäng. ${CRITERIA_POINTS_MISMATCH_GUIDANCE}`,
    );
  });

  it("refuses criteria on a question that is not free text", () => {
    const item = buildChoiceItem(2, { criteria: [{ points: 1, text: "Definition" }] });

    expect(examWorkspaceSaveRefusalCopy([item])).toBe(
      `Fråga 2 har kriterier men är inte en fritextfråga. ${CRITERIA_ON_WRONG_KIND_GUIDANCE}`,
    );
  });
});
