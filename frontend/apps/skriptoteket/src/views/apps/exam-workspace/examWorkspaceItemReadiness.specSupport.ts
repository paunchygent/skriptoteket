import type { NativeExamItem } from "../../../api/examWorkspace";

export function buildChoiceItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
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
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: null,
    leftover_points_text: null,
    ...overrides,
  };
}
