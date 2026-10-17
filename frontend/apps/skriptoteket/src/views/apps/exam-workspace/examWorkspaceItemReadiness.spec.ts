/**
 * Exam workspace per-item export readiness.
 *
 * Expected behavior:
 *   Each question reports the same reasons the server export gate refuses
 *   with (unbuilt source fallback or missing picture awaiting review,
 *   unreviewed machine key, keyed question without a key, missing points)
 *   plus the states the save refuses (a partial gap
 *   key, points not greater than zero, a choice without text, criteria
 *   that lack text or points or are not the item's points), in a stable
 *   order; ready
 *   questions report nothing and are left out of the per-item copy map.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspaceItemReadiness,
  examWorkspaceReadinessByItemId,
} from "./examWorkspaceItemReadiness";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import {
  CRITERIA_POINTS_MISMATCH_GUIDANCE,
  INVALID_CRITERION_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { INCOMPLETE_MATCH_KEY_GUIDANCE, PARTIAL_GAP_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import { plainBody } from "./examWorkspaceRichText";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";

function buildChoiceItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
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
    item_id: "item_001",
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
    sequence: 1,
    source_anchor: null,
    suggested_kind: null,
    tick_points: null,
    ...overrides,
  };
}

describe("examWorkspaceItemReadiness", () => {
  it("reports nothing for a reviewed, keyed question with points", () => {
    expect(examWorkspaceItemReadiness(buildChoiceItem())).toEqual([]);
  });

  it("reports every server gate reason in order", () => {
    const item = buildChoiceItem({
      answer_key: { correct_choice_ids: ["choice_001"], match_pairs: [], origin: "machine_proposed" },
      points: null,
      review: {
        confidence: null,
        parse_origin: "source_fallback",
        reasons: [],
        state: "review_required",
      },
    });

    expect(examWorkspaceItemReadiness(item)).toEqual([
      "unbuilt_question",
      "machine_proposed_key_unreviewed",
      "missing_points",
    ]);
  });

  it.each([null, "dxe:item_001"])(
    "does not block deterministic free text needing manual marking with source anchor %s",
    (sourceAnchor) => {
      const item = buildChoiceItem({
        answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
        choices: [],
        kind: "free_text",
        source_anchor: sourceAnchor,
        review: {
          confidence: null,
          parse_origin: "deterministic",
          reasons: ["Frågan kräver manuell rättning."],
          state: "review_required",
        },
      });

      expect(examWorkspaceItemReadiness(item)).toEqual([]);
      expect(examWorkspaceReadinessByItemId([item])).toEqual({});
    },
  );

  it("reports only the missing key for a deterministic keyed question needing review", () => {
    const item = buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
      source_anchor: "dxe:item_001",
      review: {
        confidence: null,
        parse_origin: "deterministic",
        reasons: ["Frågan behöver en manuell facitkontroll."],
        state: "review_required",
      },
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["missing_answer_key"]);
  });

  it("does not block a converted question that only needs review", () => {
    const item = buildChoiceItem({
      review: {
        confidence: 0.4,
        parse_origin: "llm_parsed",
        reasons: ["AI-tolkningen markerade frågan för granskning: oklar instruktion"],
        state: "review_required",
      },
    });

    expect(examWorkspaceItemReadiness(item)).toEqual([]);
  });

  it.each(["chunks", "key_chunks", "context_chunks"] as const)(
    "blocks a named missing picture in %s until the teacher marks it reviewed", (part) => {
      const source: NonNullable<NativeExamItem["retry_source"]> = {
        label_kind: "single_choice", key_chunks: [], context_chunks: [],
        chunks: [{anchor: "body:0001", kind: "paragraph", text: "Question", marked_text: "Question", images: [], missing_images: [], paragraphs: [], runs: []}],
      };
      source[part] = [{
        anchor: part === "chunks" ? "body:0001" : "body:0008", kind: "drawing",
        text: "", marked_text: "", images: [], missing_images: [{reference: "image3.emf", media_type: "image/x-emf", offset: 0, marked_offset: 0}],
        paragraphs: [], runs: [],
      }];
      const item = buildChoiceItem({retry_source: source, review: {
        confidence: 0.95, parse_origin: "llm_parsed", reasons: ["Bild saknas: image3.emf"],
        state: "review_required",
      }});
      expect(examWorkspaceItemReadiness(item)).toEqual(["unbuilt_question"]);
      const reviewed = {...item, review: {...item.review, state: "review_complete" as const}};
      expect(examWorkspaceItemReadiness(reviewed)).toEqual([]);
    },
  );

  it("blocks a source fallback with estimated points until it is marked reviewed", () => {
    const unbuilt = buildChoiceItem({
      points: 2,
      points_estimated: true,
      review: { confidence: null, parse_origin: "source_fallback", reasons: [], state: "review_required" },
    });
    const reviewed = { ...unbuilt, review: { ...unbuilt.review, state: "review_complete" as const } };

    expect(examWorkspaceItemReadiness(unbuilt)).toEqual(["unbuilt_question"]);
    expect(examWorkspaceItemReadiness(reviewed)).toEqual([]);
  });

  it("reports a missing key only for keyed kinds", () => {
    const keyed = buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    });
    const freeText = buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
      choices: [],
      kind: "free_text",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspaceItemReadiness(keyed)).toEqual(["missing_answer_key"]);
    expect(examWorkspaceItemReadiness(freeText)).toEqual([]);
  });

  it("reports a partial gap key", () => {
    const item = buildChoiceItem({
      choices: [],
      gaps: [
        buildGap("gap_001", ["100"]),
        buildGap("gap_002"),
      ],
      kind: "gap_fill",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["partial_gap_key"]);
  });

  it("accepts zero points and positive fractions, but reports negative points", () => {
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: 0 }))).toEqual([]);
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: -2 }))).toEqual([
      "negative_points",
    ]);
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: 0.5 }))).toEqual([]);
  });

  it.each([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    "reports non-finite points %s",
    (points) => {
      expect(examWorkspaceItemReadiness(buildChoiceItem({ points }))).toEqual([
        "negative_points",
      ]);
    },
  );

  it("reports choices without exportable text, including whitespace", () => {
    const empty = buildChoiceItem({
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "" }] }] },
      ],
    });
    const blank = buildChoiceItem({
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: " " }] }] },
      ],
    });

    expect(examWorkspaceItemReadiness(empty)).toEqual(["empty_choice"]);
    expect(examWorkspaceItemReadiness(blank)).toEqual(["empty_choice"]);
  });
});

describe("export-only content readiness", () => {
  function dropdown(): NativeExamItem {
    return buildChoiceItem({
      kind: "inline_choice",
      choices: [],
      answer_key: { origin: "teacher_authored", correct_choice_ids: [], match_pairs: [] },
      body: [{ heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] }],
      gaps: [buildGap("gap_001", [], {
        correct_option_id: "option_001",
        options: [
          { choice_id: "option_001", body: plainBody("Syre") },
          { choice_id: "option_002", body: plainBody("Järn") },
        ],
      })],
    });
  }

  it("blocks a dropdown without a key but accepts the keyed dropdown", () => {
    const item = dropdown();
    expect(examWorkspaceItemReadiness(item)).toEqual([]);
    item.answer_key.origin = "absent";
    item.gaps[0]!.correct_option_id = null;
    expect(examWorkspaceItemReadiness(item)).toEqual(["missing_answer_key"]);
  });

  it("blocks a heading in any paragraph of any dropdown option", () => {
    const item = dropdown();
    item.gaps[0]!.options[1]!.body.push({
      heading_level: 2, segments: [{ kind: "text", marks: [], text: "Rubrik" }],
    });
    expect(examWorkspaceItemReadiness(item)).toEqual(["inline_choice_option_heading"]);
    item.gaps[0]!.options[1]!.body[1]!.heading_level = null;
    expect(examWorkspaceItemReadiness(item)).toEqual([]);
  });

  it.each(["", " \n\t "])("blocks a blank dropdown option %j", (text) => {
    const item = dropdown();
    item.gaps[0]!.options[1]!.body = plainBody(text);
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_gap_option"]);
    expect(examWorkspaceReadinessByItemId([item])[item.item_id]).toEqual([
      "Ett alternativ i en lucka saknar text.",
    ]);
  });

  it.each(["single_choice", "multiple_response"] as const)(
    "blocks whitespace-only %s choices but accepts text after a blank paragraph", (kind) => {
      const item = buildChoiceItem({ kind });
      item.choices[1]!.body = plainBody(" \n\t ");
      expect(examWorkspaceItemReadiness(item)).toEqual(["empty_choice"]);
      item.choices[1]!.body.push(...plainBody(" Järn "));
      expect(examWorkspaceItemReadiness(item)).toEqual([]);
    },
  );

  it.each(["match_left", "match_right"] as const)(
    "blocks whitespace-only entries in %s but accepts nonblank text", (side) => {
      const item = buildMatchingItem();
      item[side][0]!.body = plainBody(" \n\t ");
      expect(examWorkspaceItemReadiness(item)).toEqual(["empty_match_entry"]);
      expect(examWorkspaceReadinessByItemId([item])[item.item_id]).toEqual([
        "En del i matchningen saknar text.",
      ]);
      item[side][0]!.body.push(...plainBody(" Text "));
      expect(examWorkspaceItemReadiness(item)).toEqual([]);
    },
  );
});

describe("examWorkspaceReadinessByItemId", () => {
  it("maps only questions that stop an export to Swedish copy", () => {
    const ready = buildChoiceItem();
    const partial = buildChoiceItem({
      choices: [],
      gaps: [buildGap("gap_001")],
      item_id: "item_002",
      kind: "gap_fill",
      match_left: [],
      match_right: [],
      points: null,
      sequence: 2,
    });

    expect(examWorkspaceReadinessByItemId([ready, partial])).toEqual({
      item_002: [PARTIAL_GAP_KEY_GUIDANCE, "Poäng saknas."],
    });
  });

  it("maps the save-refused states to their Swedish copy", () => {
    const item = buildChoiceItem({
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "" }] }] },
      ],
      points: -1,
    });

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      item_001: ["Poängen kan inte vara negativ.", "Ett svarsalternativ saknar text."],
    });
  });
});

describe("examWorkspaceItemReadiness for matching items", () => {
  it("reports nothing for a fully keyed matching item", () => {
    expect(examWorkspaceItemReadiness(buildMatchingItem())).toEqual([]);
  });

  it("reports an absent key as a missing answer key, not as an incomplete one", () => {
    const item = buildMatchingItemWithPairs([]);

    expect(
      examWorkspaceItemReadiness({
        ...item,
        answer_key: { ...item.answer_key, origin: "absent" },
      }),
    ).toEqual(["missing_answer_key"]);
  });

  it("reports a keyed item missing one pair", () => {
    const reasons = examWorkspaceItemReadiness(
      buildMatchingItemWithPairs([
        [1, 2],
        [2, 1],
      ]),
    );

    expect(reasons).toEqual(["incomplete_match_key"]);
  });

  it("reports a keyed item with a repeated tick", () => {
    const reasons = examWorkspaceItemReadiness(
      buildMatchingItemWithPairs([
        [1, 2],
        [1, 2],
        [2, 1],
        [3, 3],
      ]),
    );

    expect(reasons).toEqual(["incomplete_match_key"]);
  });

  it("reports nothing for a keyed item with an unpaired right entry", () => {
    expect(examWorkspaceItemReadiness(buildMatchingItemWithDistractor())).toEqual([]);
  });

  it("reports an entry without text", () => {
    const item = buildMatchingItem();

    expect(
      examWorkspaceItemReadiness({
        ...item,
        match_right: item.match_right.map((entry) =>
          entry.right_id === "right_003" ? { ...entry, body: plainBody("") } : entry,
        ),
      }),
    ).toEqual(["empty_match_entry"]);
  });

  it("maps the incomplete key to its Swedish guidance by item id", () => {
    const item = buildMatchingItemWithPairs([[1, 2]]);

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      [item.item_id]: [INCOMPLETE_MATCH_KEY_GUIDANCE],
    });
  });
});

function buildCriteriaItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...buildChoiceItem({
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

describe("examWorkspaceItemReadiness for free-text criteria", () => {
  it("reports nothing when a non-empty criteria list sums to the item's points", () => {
    expect(examWorkspaceItemReadiness(buildCriteriaItem())).toEqual([]);
  });

  it("reports a criterion whose text is empty or whitespace only", () => {
    const blank = buildCriteriaItem({
      criteria: [
        { points: 2, text: " \n\t " },
        { points: 1, text: "Exempel" },
      ],
    });

    expect(examWorkspaceItemReadiness(blank)).toEqual(["empty_criterion_text"]);
  });

  it("reports criteria reasons in a stable order", () => {
    const item = buildCriteriaItem({
      criteria: [{ points: 1.5, text: "" }],
    });

    expect(examWorkspaceItemReadiness(item)).toEqual([
      "empty_criterion_text",
      "invalid_criterion_points",
      "criteria_points_mismatch",
    ]);
  });

  it("reports criteria on a question that is not free text", () => {
    const item = buildChoiceItem({ criteria: [{ points: 1, text: "Definition" }] });

    expect(examWorkspaceItemReadiness(item)).toEqual(["criteria_on_wrong_kind"]);
  });

  it("maps the criteria reasons to their Swedish copy by item id", () => {
    const item = buildCriteriaItem({ points: 2 });

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      item_001: [CRITERIA_POINTS_MISMATCH_GUIDANCE],
    });
  });

  it("maps invalid criterion points to their Swedish copy by item id", () => {
    const item = buildCriteriaItem({
      criteria: [
        { points: 1.5, text: "Definition" },
        { points: 1.5, text: "Exempel" },
      ],
    });

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      item_001: [INVALID_CRITERION_POINTS_GUIDANCE],
    });
  });
});

describe("ordering readiness", () => {
  function ordering(texts: string[], printOrder: string[] = []): NativeExamItem {
    const choices = texts.map((text, index) => ({
      choice_id: `choice_00${index + 1}`,
      body: plainBody(text),
    }));
    return buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
      choices,
      kind: "ordering",
      print_order: printOrder,
    });
  }

  it("accepts two or more filled steps with any print order and never asks for a key", () => {
    expect(examWorkspaceItemReadiness(ordering(["Först", "Sedan"], ["choice_002", "choice_001"]))).toEqual([]);
    expect(examWorkspaceItemReadiness(ordering(["A", "B", "C"], ["choice_001", "choice_002", "choice_003"]))).toEqual([]);
    expect(examWorkspaceItemReadiness(ordering(["A", "B"]))).toEqual([]);
  });

  it.each([[[]], [["Ensam"]]])("blocks an ordering question with %j steps as too few", (texts) => {
    const reasons = examWorkspaceItemReadiness(ordering(texts));
    expect(reasons).toEqual(["ordering_too_few_steps"]);
    expect(examWorkspaceReadinessByItemId([ordering(texts)]).item_001).toEqual([
      "Ordningsfrågan behöver minst två steg.",
    ]);
  });

  it.each(["", " \n\t "])("names an empty step %j as an ordering step, not a choice", (blank) => {
    const item = ordering(["Först", blank, "Sist"]);
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_ordering_step"]);
    expect(examWorkspaceReadinessByItemId([item]).item_001).toEqual([
      "Ett steg i ordningsfrågan saknar text.",
    ]);
  });

  it("reports both reasons for a single blank step and never missing_answer_key", () => {
    const item = ordering([" "]);
    item.answer_key.origin = "teacher_authored";
    expect(examWorkspaceItemReadiness(item)).toEqual(["ordering_too_few_steps", "empty_ordering_step"]);
    expect(examWorkspaceItemReadiness(item)).not.toContain("missing_answer_key");
  });

  it("keeps empty_choice for a single_choice question", () => {
    const item = buildChoiceItem();
    item.choices[1]!.body = plainBody(" ");
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_choice"]);
  });
});
