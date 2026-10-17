/**
 * Exam workspace import steps.
 *
 * Domain purpose:
 *   What the conversion decided for one question, as numbered lines in the
 *   Import box: the type it read, where the answer key came from, and every
 *   later reconversion with how it ended.
 *
 * Relationships:
 *   - Read by `ExamWorkspaceImportBox` from the item's `import_record`.
 */

import type { NativeExamImportRecord, NativeExamItemKind } from "../../../api/examWorkspace";
import { EXAM_WORKSPACE_TYPE_LABELS } from "./examWorkspaceRows";

type ImportStep = NativeExamImportRecord["steps"][number];
type AnswerKeyOrigin = Extract<ImportStep, { kind: "answer_key" }>["origin"];

/** Where the answer key came from; a kind without a key (free text) says nothing. */
const ANSWER_KEY_STEP: Record<AnswerKeyOrigin, string | null> = {
  absent: "Facit saknades i provfilen",
  ai_interpreted: "Facit: tolkat av AI ur facittexten",
  machine_proposed: "Facit saknades i provfilen; AI föreslog ett",
  not_applicable: null,
  reviewed_advisory: "Facit: AI:s förslag, granskat",
  source_provided: "Facit: kopierat ur provfilen",
  teacher_authored: "Facit: skrivet av läraren",
};

function typeName(kind: NativeExamItemKind): string {
  return EXAM_WORKSPACE_TYPE_LABELS[kind];
}

function stepLine(step: ImportStep): string | null {
  if (step.kind === "chosen_type") {
    return `Typ: ${typeName(step.chosen_kind)}`;
  }
  if (step.kind === "answer_key") {
    return ANSWER_KEY_STEP[step.origin];
  }
  const how = step.reason === "teacher_request" ? "Konverterades igen" : "Skickades om automatiskt";
  const ending = step.outcome === "review_required" ? " – blev granskningsfråga" : "";
  return `${how}: ${typeName(step.from_kind)} → ${typeName(step.chosen_kind)}${ending}`;
}

export function examWorkspaceImportSteps(record: NativeExamImportRecord): string[] {
  return record.steps.map(stepLine).filter((line): line is string => line !== null);
}
