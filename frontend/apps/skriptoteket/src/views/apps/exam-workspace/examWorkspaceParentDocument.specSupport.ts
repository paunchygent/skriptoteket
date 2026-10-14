/**
 * Parent document fixture for exam workspace specs.
 *
 * Purpose:
 *   Build a native document from the real English recording
 *   (`docx_build_v7/bf26_english_1_unit_test_kap_1_2_med_facit/round1.json`):
 *   its first three gap_fill items are the children of one parent that holds
 *   their shared instruction ("Complete each sentence ...") as a canonical
 *   paragraph body; its first single_choice item stays a standalone question
 *   after them.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import recording from "../../../../../../../tests/fixtures/exam_conversion/docx_build_v7/bf26_english_1_unit_test_kap_1_2_med_facit/round1.json";

type RecordedSegment = { kind: string; text: string | null; accepted_values: string[] };
type RecordedItem = (typeof recording.items)[number];

const SHARED_INSTRUCTION_INDEX = 2;
const CHILD_COUNT = 3;

function itemId(sequence: number): string {
  return `item_${String(sequence).padStart(3, "0")}`;
}

function toNativeItem(recorded: RecordedItem, sequence: number): NativeExamItem {
  const gaps: NativeExamItem["gaps"] = [];
  const body = recorded.body.map((paragraph) => ({
    segments: (paragraph.segments as RecordedSegment[]).map((segment) => {
      if (segment.kind !== "gap") {
        return { kind: "text" as const, text: segment.text ?? "" };
      }
      const gapId = `gap_${String(gaps.length + 1).padStart(3, "0")}`;
      gaps.push({ accepted_values: segment.accepted_values, gap_id: gapId });
      return { gap_id: gapId, kind: "gap" as const };
    }),
  }));
  const choices = recorded.choices.map((choice, index) => ({
    choice_id: `choice_${String.fromCharCode(97 + index)}`,
    text: choice.text,
  }));
  return {
    answer_key: {
      correct_choice_ids: recorded.choices.flatMap((choice, index) =>
        choice.correct ? [`choice_${String.fromCharCode(97 + index)}`] : [],
      ),
      match_pairs: [],
      origin: "source_provided",
    },
    body,
    choices,
    gaps,
    item_id: itemId(sequence),
    kind: recorded.kind as NativeExamItem["kind"],
    match_left: [],
    match_right: [],
    points: recorded.points,
    points_estimated: false,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
  };
}

export function buildRecordedParentInstruction(): NativeExamBodyParagraph[] {
  return [
    {
      segments: [
        { kind: "text", text: recording.instructions[SHARED_INSTRUCTION_INDEX]!.text },
      ],
    },
  ];
}

export function buildRecordedParent(): NativeExamParent {
  return {
    instruction: buildRecordedParentInstruction(),
    item_ids: Array.from({ length: CHILD_COUNT }, (_, index) => itemId(index + 1)),
    parent_id: "parent_001",
  };
}

/** Three gap_fill children of `parent_001` (item_001..item_003) and one standalone item_004. */
export function buildParentDocument(): NativeExamDocument {
  const standalone = recording.items.find((recorded) => recorded.kind === "single_choice")!;
  const children = recording.items.slice(0, CHILD_COUNT);
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    instructions: [],
    items: [
      ...children.map((recorded, index) => toNativeItem(recorded, index + 1)),
      toNativeItem(standalone, CHILD_COUNT + 1),
    ],
    origin: { kind: "docx_import" },
    parents: [buildRecordedParent()],
    revision: 1,
    schema_version: "native_exam_document_v1",
    title: "English 1",
  };
}
