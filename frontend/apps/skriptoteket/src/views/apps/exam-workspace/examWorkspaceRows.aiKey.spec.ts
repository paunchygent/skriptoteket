/**
 * Exam workspace row mapping for AI-written keys.
 *
 * Expected behavior:
 *   The conversion AI's mark reaches the table rows only when the key origin
 *   says the AI interpreted the teacher's facit ("Tolkad av AI") or invented a
 *   key without one ("Förslag från AI"); every other origin leaves the row
 *   unmarked.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceAiKeyLabel, toExamWorkspaceItemRow } from "./examWorkspaceRows";

const KEY_ORIGINS_WITHOUT_AI_MARK = [
  "absent",
  "not_applicable",
  "source_provided",
  "teacher_authored",
  "reviewed_advisory",
] as const;

function buildItem(origin: NativeExamItem["answer_key"]["origin"]): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    retry_source: null,
    answer_key: { correct_choice_ids: ["choice_001"], match_pairs: [], origin },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Beskriv fotosyntesen." }] }],
    choices: [{ choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Fotosyntes" }] }] }],
    gaps: [],
    item_id: "item_001",
    kind: "single_choice",
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
    suggested_kind: null,
    tick_points: null,
  };
}

describe("examWorkspaceAiKeyLabel", () => {
  it("marks the key the AI read from the facit and the key it invented", () => {
    expect(examWorkspaceAiKeyLabel("ai_interpreted")).toBe("Tolkad av AI");
    expect(examWorkspaceAiKeyLabel("machine_proposed")).toBe("Förslag från AI");
  });

  it("leaves every other key origin unmarked", () => {
    for (const origin of KEY_ORIGINS_WITHOUT_AI_MARK) {
      expect(examWorkspaceAiKeyLabel(origin)).toBeNull();
    }
  });
});

describe("toExamWorkspaceItemRow with an AI-written key", () => {
  it("carries the interpreted label into the row", () => {
    expect(toExamWorkspaceItemRow(buildItem("ai_interpreted")).aiKeyLabel).toBe("Tolkad av AI");
  });

  it("carries the invented label into the row", () => {
    expect(toExamWorkspaceItemRow(buildItem("machine_proposed")).aiKeyLabel).toBe(
      "Förslag från AI",
    );
  });

  it("leaves a teacher-authored key unmarked", () => {
    expect(toExamWorkspaceItemRow(buildItem("teacher_authored")).aiKeyLabel).toBeNull();
  });
});
