/**
 * Exam workspace export formats.
 *
 * Domain purpose:
 *   The three export formats in the order and words the workspace offers
 *   them: QTI for Exam.net, PDF for printing, DOCX for editing in Word.
 *   Exam.net imports a question worth 0 points as worth 1, so the QTI
 *   choice says so while the exam holds one (user ruling 2026-10-17); the
 *   export itself still sends 0.
 *
 * Relationships:
 *   - Read by the Exportera menu and drawer.
 */

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspace";

export type ExamWorkspaceExportFormat = {
  target: ExamWorkspaceExportTarget;
  name: string;
  /** What the file is for, beside the name in the menu. */
  use: string;
  /** The drawer's hint under the format toggle. */
  hint: string;
};

export const EXAM_WORKSPACE_EXPORT_FORMATS: ExamWorkspaceExportFormat[] = [
  { hint: "För import i Exam.net", name: "QTI", target: "qti", use: "Exam.net" },
  { hint: "För utskrift", name: "PDF", target: "pdf", use: "utskrift" },
  { hint: "För redigering i Word", name: "DOCX", target: "docx", use: "Word" },
];

export const QTI_ZERO_POINTS_NOTE =
  "Exam.net ger frågor med 0 poäng 1 poäng. Ändra poängen i Exam.net efter importen.";
