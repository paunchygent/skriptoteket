/**
 * Exam workspace export formats.
 *
 * Domain purpose:
 *   The export formats in the order and words the workspace offers them: QTI
 *   for Exam.net, the student print PDF and its facit twin, DOCX for editing
 *   in Word, and last the Exam.net import PDF that stays a fallback for when
 *   the QTI import fails (W1, W11). Exam.net imports a question worth 0 points
 *   as worth 1, so the QTI choice says so while the exam holds one (user ruling
 *   2026-10-17); the export itself still sends 0.
 *
 * Relationships:
 *   - Read by the Exportera menu and drawer.
 */

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";

export type ExamWorkspaceExportFormat = {
  target: ExamWorkspaceExportTarget;
  name: string;
  /** What the file is for, beside the name in the menu; null hides the suffix. */
  use: string | null;
  /** The drawer's hint under the format toggle. */
  hint: string;
};

export const EXAM_WORKSPACE_EXPORT_FORMATS: ExamWorkspaceExportFormat[] = [
  { hint: "För import i Exam.net", name: "QTI", target: "qti", use: "Exam.net" },
  { hint: "Elevexemplar för utskrift", name: "PDF", target: "pdf", use: "utskrift" },
  { hint: "Samma sidor med facit och bedömning", name: "PDF med facit", target: "pdf_facit", use: null },
  { hint: "För redigering i Word", name: "DOCX", target: "docx", use: "Word" },
  { hint: "Reserv om QTI-importen inte fungerar. Inte för utskrift.", name: "PDF för Exam.net", target: "examnet_pdf", use: "reserv" },
];

export const QTI_ZERO_POINTS_NOTE =
  "Exam.net ger frågor med 0 poäng 1 poäng. Ändra poängen i Exam.net efter importen.";
