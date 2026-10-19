/**
 * Exam workspace presentation labels.
 *
 * Domain purpose:
 *   Swedish teacher-facing labels for native exam items and saved documents:
 *   question type, prompt excerpt, question number, review reason, document
 *   name and saved-at time.
 *
 * Relationships:
 *   - Pure functions consumed by the exam workspace question list and views.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type { NativeExamItem, NativeExamItemKind } from "../../../api/examWorkspace";
import { isShortAnswer } from "./examWorkspaceShortAnswer";

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

const EXCERPT_MAX_LENGTH = 140;
const CONTAINER_SUFFIX = ".provdokument.zip";

export const EXAM_WORKSPACE_TYPE_LABELS: Record<NativeExamItemKind, string> = {
  free_text: "Fritext",
  gap_fill: "Lucktext",
  inline_choice: "Lucktext med rullista",
  matching: "Kategorisera",
  multiple_response: "Flerval: flera val",
  ordering: "Ordna",
  single_choice: "Flerval: ett val",
};

export function examWorkspaceTypeLabel(kind: NativeExamItemKind): string {
  return EXAM_WORKSPACE_TYPE_LABELS[kind];
}

/** The teacher-facing type label: "Ej konverterad" while unbuilt, "Kort svar" for that shape, else the kind label. */
export function examWorkspaceItemTypeLabel(item: NativeExamItem, unbuilt: boolean): string {
  if (unbuilt) {
    return "Ej konverterad";
  }
  return isShortAnswer(item) ? "Kort svar" : examWorkspaceTypeLabel(item.kind);
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
