/**
 * DigiExam accepted-current-state overlay builder.
 *
 * Domain purpose:
 *   Build the explicit teacher decision overlay for exporting the current
 *   conversion state without creating answer-key evidence.
 *
 * Relationships:
 *   - Used by `digiexamIrReviewParser` for the PR-0325 export-current-state
 *     path.
 *   - Stays separate from reviewed AI-facit overlays, which use
 *     `reviewed_completion_answer_key`.
 */

import type {
  DigiExamIngestionOverlay,
  DigiExamMigrationTarget,
  DigiExamTargetReadinessReport,
  SirConvertArtifactManifest,
  SirConvertArtifactEntry,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ACCEPT_CURRENT_STATE_DECISION_KIND,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
  DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  SIR_CONVERT_ARTIFACT_NOT_REQUESTED,
} from "../../../api/sirConvertGateway/contractValues";
import { DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION } from "../../../api/sirConvertGateway/schemaVersions";
import type { ExamConverterQuestionReviewRow } from "./digiexamIrQuestionReviewProjection";

const TARGET_FILE_LABELS: Record<string, string> = {
  [DIGIEXAM_TARGET_EXAMNET_PDF]: "PDF",
  [DIGIEXAM_TARGET_QTI_PACKAGE]: "QTI-format",
};

function isTargetFile(entry: SirConvertArtifactEntry): boolean {
  return entry.artifact_key in TARGET_FILE_LABELS;
}

export function buildAcceptedCurrentStateOverlay(params: {
  artifactManifest: SirConvertArtifactManifest;
  questions: ExamConverterQuestionReviewRow[];
  targetReadinessReport: DigiExamTargetReadinessReport;
}): DigiExamIngestionOverlay | null {
  const acceptedTargets = params.artifactManifest.artifacts
    .filter(isTargetFile)
    .filter((entry) => entry.availability !== SIR_CONVERT_ARTIFACT_NOT_REQUESTED)
    .map((entry) => entry.artifact_key as DigiExamMigrationTarget);
  const acceptedTargetSet = new Set<string>(acceptedTargets);
  const reviewRowsByItemId = new Map(
    params.targetReadinessReport.targets
      .filter((row) => acceptedTargetSet.has(row.target))
      .filter((row) => !row.export_enabled)
      .filter(
        (row) =>
          row.readiness === DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY ||
          row.readiness === DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
      )
      .filter((row) => row.item_id !== null)
      .map((row) => [row.item_id as string, row]),
  );
  const items = params.questions
    .filter(
      (question) =>
        question.missingFields.length > 0 || reviewRowsByItemId.has(question.itemId),
    )
    .flatMap((question) => {
      const readinessRow = reviewRowsByItemId.get(question.itemId);
      const sourceItemFingerprint =
        question.sourceItemFingerprint ?? readinessRow?.source_item_fingerprint ?? null;
      if (sourceItemFingerprint === null) {
        return [];
      }
      return [
        {
          effective_item_patch: null,
          item_id: question.itemId,
          item_type: question.itemType,
          manual_answer_key: null,
          review_decision: {
            kind: DIGIEXAM_ACCEPT_CURRENT_STATE_DECISION_KIND,
            decision_id: `accept-current-state-${question.itemId}`,
            note: null,
            accepted_targets: acceptedTargets,
          },
          reviewed_completion_answer_key: null,
          sequence: question.sequence,
          source_item_fingerprint: sourceItemFingerprint,
        },
      ];
    });

  if (items.length === 0 || acceptedTargets.length === 0) {
    return null;
  }
  return {
    schema_version: DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
    source_binding: {
      source_file_sha256: params.artifactManifest.source.sha256,
      source_ir_schema_version: params.artifactManifest.source_binding.source_ir_schema_version,
      source_ir_sha256: params.artifactManifest.source_binding.source_ir_sha256,
    },
    items,
  };
}

export function isDigiExamTargetFile(entry: SirConvertArtifactEntry): boolean {
  return isTargetFile(entry);
}

export function digiExamTargetFileLabel(artifactKey: string): string {
  return TARGET_FILE_LABELS[artifactKey] ?? artifactKey;
}
