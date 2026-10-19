/**
 * Keyed item and suggestion fixtures for exam workspace arrival specs.
 *
 * Purpose:
 *   Build multiple-response, single-choice and gap-fill questions with a
 *   chosen key, review state and kept suggestion, and AI suggestions for each
 *   key family, so the whole-key equality and fit specs attack the same
 *   shapes. Matching questions come from `examWorkspaceMatchingItem.specSupport`.
 */

import type {
  NativeAnswerKeySuggestion,
  NativeExamBodySegment,
  NativeExamGap,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { plainBody } from "./examWorkspaceRichText";

/** A text-entry gap; inline-choice scenarios can override its options and key. */
export function buildGap(
  gapId: string,
  acceptedValues: string[] = [],
  overrides: Partial<NativeExamGap> = {},
): NativeExamGap {
  return {
    accepted_values: acceptedValues,
    automatic_values: [],
    correct_option_id: null,
    excluded_automatic_values: [],
    gap_id: gapId,
    options: [],
    ...overrides,
  };
}

export type GapValues = Array<[string, string[]]>;
type Origin = NativeExamItem["answer_key"]["origin"];

export function keyedSuggestion(
  fields: Partial<
    Pick<NativeAnswerKeySuggestion, "correct_choice_ids" | "match_pairs" | "gap_accepted_values">
  >,
): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [],
    fingerprint: "a".repeat(64),
    gap_accepted_values: [],
    match_pairs: [],
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
    ...fields,
  };
}

export function gapSuggestion(values: GapValues): NativeAnswerKeySuggestion {
  return keyedSuggestion({
    gap_accepted_values: values.map(([gap_id, accepted_values]) => ({ gap_id, accepted_values })),
  });
}

export function pairs(entries: Array<[string, string]>): NativeExamMatchPair[] {
  return entries.map(([left_id, right_id]) => ({ left_id, right_id }));
}

export const UNREVIEWED: NativeExamItem["review"] = {
  confidence: null,
  parse_origin: "teacher_created",
  reasons: [],
  state: "review_required",
};

export function choiceItem(
  kind: "single_choice" | "multiple_response",
  origin: Origin,
  key: string[],
  previous: NativeAnswerKeySuggestion | null,
  choiceIds: string[] = ["choice_001", "choice_002", "choice_003"],
): NativeExamItem {
  return {
    ai_suggestion: previous,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: key, match_pairs: [], origin },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Vilka är verb?", kept_gap_id: null }] }],
    choices: choiceIds.map((choice_id) => ({ choice_id, body: plainBody(choice_id) })),
    gaps: [],
    kept_gaps: [],
    item_id: "item_001",
    kind,
    suggested_kind: null,
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: UNREVIEWED,
    sequence: 1,
    source_anchor: null,
    source_points: null,
    tick_points: null,
    writing_lines: null,
  };
}

export function gapItem(
  origin: Origin,
  key: GapValues,
  previous: NativeAnswerKeySuggestion | null,
): NativeExamItem {
  const segments: NativeExamBodySegment[] = [{ kind: "text", marks: [], text: "Hon heter ", kept_gap_id: null }];
  for (const [gap_id] of key) {
    segments.push({ gap_id, kind: "gap" }, { kind: "text", marks: [], text: " och ", kept_gap_id: null });
  }
  return {
    ai_suggestion: previous,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin },
    body: [{ heading_level: null, segments }],
    choices: [],
    gaps: key.map(([gap_id, accepted_values]) => buildGap(gap_id, accepted_values)),
    kept_gaps: [],
    item_id: "item_001",
    kind: "gap_fill",
    suggested_kind: null,
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: UNREVIEWED,
    sequence: 1,
    source_anchor: null,
    source_points: null,
    tick_points: null,
    writing_lines: null,
  };
}
