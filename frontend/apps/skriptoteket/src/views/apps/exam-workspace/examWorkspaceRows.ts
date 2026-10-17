/**
 * Exam workspace item-row presentation mapping.
 *
 * Domain purpose:
 *   Map native exam items to the compact teacher-facing table rows with
 *   Swedish type, review-status and AI-key labels, and saved-document
 *   summaries to short list labels.
 *
 * Relationships:
 *   - Pure functions consumed by `ExamWorkspaceView`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type {
  NativeExamAnswerKeyOrigin,
  NativeExamItem,
  NativeExamItemKind,
  NativeExamParent,
  NativeExamReviewState,
} from "../../../api/examWorkspace";
import {
  examWorkspaceParentBlocksByFirstChild,
  examWorkspaceParentChildren,
} from "./examWorkspaceParents";
import type { ExamWorkspaceParentBlock, ExamWorkspaceParentChild } from "./examWorkspaceParents";

const REVIEW_REASON_LABELS: Record<string, string> = {
  machine_proposed_answer_key:
    "Facit är ett maskinellt förslag – kontrollera det innan du godkänner.",
};

const SNAKE_CASE_CODE = /^[a-z0-9]+(?:_[a-z0-9]+)+$/;

export function examWorkspaceReviewReasonLabel(reason: string): string {
  const known = REVIEW_REASON_LABELS[reason];
  if (known !== undefined) {
    return known;
  }
  if (SNAKE_CASE_CODE.test(reason)) {
    return "Kontrollera frågan – tolkningen är osäker.";
  }
  return reason;
}

export type ExamWorkspaceItemRow = {
  itemId: string;
  sequence: number;
  title: string;
  promptExcerpt: string;
  typeLabel: string;
  pointsLabel: string;
  statusLabel: string;
  /**
   * Set when the conversion AI wrote the key: "Tolkad av AI" for a key it
   * interpreted from the facit, "Förslag från AI" for a key it invented
   * without one. Null when the key came from the facit or the teacher.
   */
  aiKeyLabel: string | null;
  reviewRequired: boolean;
  reviewReasons: string[];
  /** Set on a child question: where it sits in its parent. */
  parentChild: ExamWorkspaceParentChild | null;
  /** Set only on a parent's first child: the shared instruction and total points. */
  parentBlock: ExamWorkspaceParentBlock | null;
};

const EXCERPT_MAX_LENGTH = 140;
const CONTAINER_SUFFIX = ".provdokument.zip";

export const EXAM_WORKSPACE_TYPE_LABELS: Record<NativeExamItemKind, string> = {
  free_text: "Fritext",
  gap_fill: "Lucktext",
  inline_choice: "Lucktext med rullista",
  matching: "Kategorisera",
  multiple_response: "Flerval: flera val",
  single_choice: "Flerval: ett val",
};

export function examWorkspaceTypeLabel(kind: NativeExamItemKind): string {
  return EXAM_WORKSPACE_TYPE_LABELS[kind];
}

export function examWorkspaceReviewStatusLabel(state: NativeExamReviewState): string {
  return state === "review_required" ? "Behöver granskas" : "Granskad";
}

/**
 * The AI mark for an item's key: the AI read the teacher's facit, or invented
 * a key without one. Null for every other origin.
 */
export function examWorkspaceAiKeyLabel(origin: NativeExamAnswerKeyOrigin): string | null {
  if (origin === "ai_interpreted") {
    return "Tolkad av AI";
  }
  if (origin === "machine_proposed") {
    return "Förslag från AI";
  }
  return null;
}

export function examWorkspacePointsLabel(points: number | null): string {
  if (points === null) {
    return "–";
  }
  return points.toLocaleString("sv-SE", { maximumFractionDigits: 2 });
}

export function examWorkspacePromptExcerpt(item: NativeExamItem): string {
  const flattened = item.body
    .map((paragraph) =>
      paragraph.segments
        .map((segment) => {
          if (segment.kind === "text") {
            return segment.text;
          }
          if (segment.kind === "gap") {
            return "[___]";
          }
          return "";
        })
        .join(" "),
    )
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();

  if (flattened.length <= EXCERPT_MAX_LENGTH) {
    return flattened;
  }
  return `${flattened.slice(0, EXCERPT_MAX_LENGTH - 1).trimEnd()}…`;
}

/** The row label for a question: its question number. */
export function examWorkspaceQuestionLabel(sequence: number): string {
  return `Fråga ${sequence}`;
}

export function toExamWorkspaceItemRow(
  item: NativeExamItem,
  parentChild: ExamWorkspaceParentChild | null = null,
  parentBlock: ExamWorkspaceParentBlock | null = null,
): ExamWorkspaceItemRow {
  const title = examWorkspaceQuestionLabel(item.sequence);

  return {
    aiKeyLabel: examWorkspaceAiKeyLabel(item.answer_key.origin),
    itemId: item.item_id,
    parentBlock,
    parentChild,
    pointsLabel: examWorkspacePointsLabel(item.points ?? null),
    promptExcerpt: examWorkspacePromptExcerpt(item),
    reviewReasons: item.review.reasons.map(examWorkspaceReviewReasonLabel),
    reviewRequired: item.review.state === "review_required",
    sequence: item.sequence,
    statusLabel: examWorkspaceReviewStatusLabel(item.review.state),
    title,
    typeLabel: examWorkspaceTypeLabel(item.kind),
  };
}

export function toExamWorkspaceItemRows(
  items: NativeExamItem[],
  parents: NativeExamParent[] = [],
  assetUrls: Record<string, string> = {},
): ExamWorkspaceItemRow[] {
  const blocks = examWorkspaceParentBlocksByFirstChild(parents, items, assetUrls);
  const children = examWorkspaceParentChildren(parents);
  return items.map((item) =>
    toExamWorkspaceItemRow(item, children[item.item_id] ?? null, blocks[item.item_id] ?? null),
  );
}

export function examWorkspaceDocumentLabel(name: string): string {
  return name.endsWith(CONTAINER_SUFFIX) ? name.slice(0, -CONTAINER_SUFFIX.length) : name;
}

export function examWorkspaceSavedAtLabel(savedAt: string): string {
  const date = new Date(savedAt);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("sv-SE", { dateStyle: "short", timeStyle: "short" });
}
