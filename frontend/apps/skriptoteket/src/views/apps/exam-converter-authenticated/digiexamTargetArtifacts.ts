/**
 * DigiExam target artifact helpers.
 *
 * Domain purpose:
 *   Identify and label teacher-facing DigiExam export artifacts in the Exam
 *   Converter inspection model.
 *
 * Relationships:
 *   - Used by `digiexamIrReviewParser` when projecting Exam Converter artifact
 *     manifests into downloadable file rows.
 *   - Keeps target labels independent from correction-session authoring state.
 */

import type { ExamConverterArtifactEntry } from "../../../api/examConverterContracts";
import {
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
} from "../../../api/examConverterContracts";

const TARGET_FILE_LABELS: Record<string, string> = {
  [DIGIEXAM_TARGET_EXAMNET_PDF]: "PDF",
  [DIGIEXAM_TARGET_QTI_PACKAGE]: "QTI-format",
};

export function isDigiExamTargetFile(entry: ExamConverterArtifactEntry): boolean {
  return entry.artifact_key in TARGET_FILE_LABELS;
}

export function digiExamTargetFileLabel(artifactKey: string): string {
  return TARGET_FILE_LABELS[artifactKey] ?? artifactKey;
}
