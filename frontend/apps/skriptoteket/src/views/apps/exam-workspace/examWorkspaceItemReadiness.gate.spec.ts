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
 *   questions report nothing.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";

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
        label_kind: "single_choice", key_chunks: [], context_chunks: [], owned_context_anchors: [],
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
});
