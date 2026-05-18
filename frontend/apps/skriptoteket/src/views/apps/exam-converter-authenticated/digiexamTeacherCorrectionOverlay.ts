/**
 * DigiExam teacher correction overlay builder.
 *
 * Domain purpose:
 *   Build source-bound Sir Convert overlays for teacher-owned corrections that
 *   are applied to effective renderer input before PDF/QTI artifacts are used.
 *
 * Relationships:
 *   - Consumes question rows from the Exam Converter review projection.
 *   - Produces `digiexam_ingestion_overlay_v2` payloads for the authenticated
 *     Sir Convert Gateway client.
 *   - Keeps correction overlays separate from advisory AI-facit review state
 *     and accepted-current-state export decisions.
 */

import type { DigiExamIngestionOverlay } from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
} from "../../../api/sirConvertGateway/contractValues";
import { DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION } from "../../../api/sirConvertGateway/schemaVersions";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";

export type ExamConverterManualAnswerKeyCorrection =
  | {
      correctAlternativeIds: number[];
      kind: "choice";
    }
  | {
      gapAnswers: {
        acceptedValues: string[];
        gapId: string;
      }[];
      kind: "gap_fill";
    };

function assertValidPointCorrection(maxScore: number): void {
  if (!Number.isInteger(maxScore) || maxScore <= 0) {
    throw new Error("Point correction requires a positive integer score.");
  }
}

function assertSourceItemFingerprint(
  question: ExamConverterQuestionReviewRow,
): string {
  if (!question.sourceItemFingerprint) {
    throw new Error("Teacher correction overlay requires source item fingerprints.");
  }
  return question.sourceItemFingerprint;
}

function baseOverlay(params: {
  projection: ExamConverterReviewProjection;
}): Pick<DigiExamIngestionOverlay, "schema_version" | "source_binding"> {
  return {
    schema_version: DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
    source_binding: {
      source_file_sha256: params.projection.sourceFileSha256,
      source_ir_schema_version:
        params.projection.artifactSourceBinding.source_ir_schema_version,
      source_ir_sha256: params.projection.artifactSourceBinding.source_ir_sha256,
    },
  };
}

function assertChoiceItem(question: ExamConverterQuestionReviewRow): void {
  if (
    question.itemType !== DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE &&
    question.itemType !== DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE &&
    question.itemType !== DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE
  ) {
    throw new Error("Choice answer-key correction requires a choice item.");
  }
}

function assertGapFillItem(question: ExamConverterQuestionReviewRow): void {
  if (question.itemType !== DIGIEXAM_ITEM_TYPE_GAP_FILL) {
    throw new Error("Gap-fill answer-key correction requires a gap-fill item.");
  }
}

function normalizedChoiceIds(correctAlternativeIds: number[]): number[] {
  const normalized = [...new Set(correctAlternativeIds)].sort((left, right) => left - right);
  if (normalized.length === 0 || normalized.some((id) => !Number.isInteger(id) || id <= 0)) {
    throw new Error("Choice answer-key correction requires one or more alternative ids.");
  }
  return normalized;
}

function normalizedGapAnswers(params: {
  gapAnswers: Extract<ExamConverterManualAnswerKeyCorrection, { kind: "gap_fill" }>["gapAnswers"];
  question: ExamConverterQuestionReviewRow;
}) {
  const expectedGapIds = new Set(params.question.gaps.map((gap) => gap.id));
  const normalized = params.gapAnswers.map((gapAnswer) => ({
    accepted_values: [...new Set(gapAnswer.acceptedValues.map((value) => value.trim()))].filter(
      (value) => value.length > 0,
    ),
    gap_id: gapAnswer.gapId.trim(),
  }));
  const submittedGapIds = normalized.map((gapAnswer) => gapAnswer.gap_id);
  if (
    normalized.length === 0 ||
    normalized.length !== expectedGapIds.size ||
    normalized.some((gapAnswer) => gapAnswer.gap_id.length === 0) ||
    normalized.some((gapAnswer) => gapAnswer.accepted_values.length === 0) ||
    submittedGapIds.some((gapId) => !expectedGapIds.has(gapId)) ||
    new Set(submittedGapIds).size !== submittedGapIds.length
  ) {
    throw new Error("Gap-fill answer-key correction requires accepted values for each source gap.");
  }
  return normalized;
}

export function buildPointCorrectionOverlay(params: {
  maxScore: number;
  projection: ExamConverterReviewProjection;
  question: ExamConverterQuestionReviewRow;
}): DigiExamIngestionOverlay {
  assertValidPointCorrection(params.maxScore);
  return {
    ...baseOverlay({ projection: params.projection }),
    items: [
      {
        effective_item_patch: null,
        item_id: params.question.itemId,
        item_type: params.question.itemType,
        manual_answer_key: null,
        point_correction: {
          kind: "item_points",
          max_score: params.maxScore,
        },
        review_decision: null,
        reviewed_completion_answer_key: null,
        sequence: params.question.sequence,
        source_item_fingerprint: assertSourceItemFingerprint(params.question),
      },
    ],
  };
}

export function buildManualAnswerKeyOverlay(params: {
  answerKey: ExamConverterManualAnswerKeyCorrection;
  projection: ExamConverterReviewProjection;
  question: ExamConverterQuestionReviewRow;
}): DigiExamIngestionOverlay {
  const manualAnswerKey =
    params.answerKey.kind === "choice"
      ? (() => {
          assertChoiceItem(params.question);
          return {
            correct_alternative_ids: normalizedChoiceIds(params.answerKey.correctAlternativeIds),
            kind: "choice" as const,
          };
        })()
      : (() => {
          assertGapFillItem(params.question);
          return {
            gap_answers: normalizedGapAnswers({
              gapAnswers: params.answerKey.gapAnswers,
              question: params.question,
            }),
            kind: "gap_fill" as const,
          };
        })();
  return {
    ...baseOverlay({ projection: params.projection }),
    items: [
      {
        effective_item_patch: null,
        item_id: params.question.itemId,
        item_type: params.question.itemType,
        manual_answer_key: manualAnswerKey,
        point_correction: null,
        review_decision: null,
        reviewed_completion_answer_key: null,
        sequence: params.question.sequence,
        source_item_fingerprint: assertSourceItemFingerprint(params.question),
      },
    ],
  };
}
