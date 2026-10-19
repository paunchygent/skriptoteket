import type { NativeExamItem } from "../api/examWorkspace";

/** A complete current-schema free-text item; callers replace only scenario data. */
export function buildFreeTextItem(sequence: number, overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    import_record: null,
    facit_text: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [
      { heading_level: null, segments: [{ kind: "text", marks: [], text: `Fråga ${sequence}: beskriv med egna ord.` }] },
    ],
    choices: [],
    gaps: [],
    match_left: [],
    match_right: [],
    item_id: `item_${String(sequence).padStart(3, "0")}`,
    kind: "free_text",
    points: 2,
    points_estimated: false,
    review: { confidence: 0.9, parse_origin: "deterministic", reasons: [], state: "review_complete" },
    sequence,
    source_anchor: null,
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
    ...overrides,
  };
}
