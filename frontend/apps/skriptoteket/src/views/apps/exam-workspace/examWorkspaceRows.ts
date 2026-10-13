/**
 * Exam workspace item-row presentation mapping.
 *
 * Domain purpose:
 *   Map native exam items to the compact teacher-facing table rows with
 *   Swedish type and review-status labels, and saved-document summaries to
 *   short list labels.
 *
 * Relationships:
 *   - Pure functions consumed by `ExamWorkspaceView`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type {
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
  matching: "Matchning",
  multiple_response: "Flerval: flera val",
  single_choice: "Flerval: ett val",
};

export function examWorkspaceTypeLabel(kind: NativeExamItemKind): string {
  return EXAM_WORKSPACE_TYPE_LABELS[kind];
}

export function examWorkspaceReviewStatusLabel(state: NativeExamReviewState): string {
  return state === "review_required" ? "Behöver granskas" : "Granskad";
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

/**
 * The title as shown beside its question number. A leading "Fråga N.",
 * "Fråga N:" or "N." that repeats the item's own sequence is dropped so the
 * number is not shown twice; the stored title is never changed. Returns an
 * empty string when nothing else is left.
 */
export function examWorkspaceDisplayTitle(title: string | null | undefined, sequence: number): string {
  const trimmed = (title ?? "").trim();
  const prefix = new RegExp(`^(?:fråga\\s*)?${sequence}(?:\\s*[.:]\\s+|\\s*[.:]$|$)`, "i");
  return trimmed.replace(prefix, "").trim();
}

export function toExamWorkspaceItemRow(
  item: NativeExamItem,
  parentChild: ExamWorkspaceParentChild | null = null,
  parentBlock: ExamWorkspaceParentBlock | null = null,
): ExamWorkspaceItemRow {
  const title =
    examWorkspaceDisplayTitle(item.title, item.sequence) || `Fråga ${item.sequence}`;

  return {
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
): ExamWorkspaceItemRow[] {
  const blocks = examWorkspaceParentBlocksByFirstChild(parents, items);
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
