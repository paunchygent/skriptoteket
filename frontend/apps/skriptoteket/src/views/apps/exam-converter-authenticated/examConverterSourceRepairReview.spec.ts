/**
 * Exam Converter recoverable-source repair projection tests.
 *
 * Slice purpose:
 *   Prove the read-only authenticated review projection carries the
 *   parent-owned canonical Swedish source-repair messages verbatim next to
 *   the affected question and into the report counts and affected-question
 *   labels. This spec renders no UI and invents no copy; every message under
 *   test is the parent-owned canonical text supplied by the payload.
 *
 * Expected behavior:
 *   - A question review row carries the item-bound repair warnings with the
 *     exact canonical Swedish message text and the source-repair codes.
 *   - Unrelated parser warning codes never leak into review warnings.
 *   - The report counts missing titles and missing images per question and
 *     lists the affected questions with sequence, title, and the same exact
 *     messages.
 */

import { describe, expect, it } from "vitest";

import {
  ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  DIGIEXAM_SOURCE_FORMAT,
  DIGIEXAM_TARGET_READY,
  DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE,
  DIGIEXAM_WARNING_MISSING_QUESTION_TITLE,
  EXAM_CONVERTER_BUNDLE_STATUS_COMPLETE,
  parseTargetReadinessReport,
} from "../../../api/examConverterContracts";
import { parseExamConverterReviewProjection } from "./digiexamIrReviewParser";
import {
  isReviewWarningCode,
  projectQuestionReviewRow,
  type DigiExamIrItem,
} from "./digiexamIrQuestionReviewProjection";

// Parent-owned canonical Swedish copy that must cross the projection verbatim.
// `N` is the affected question number (the IR item sequence).
const CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1 =
  "Bilden i fråga 1 saknas. Lägg till den innan du använder provet.";
const CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2 =
  "Fråga 2 saknade titel. Titeln ”Question 2” lades till automatiskt. Kontrollera titeln innan du använder provet.";

const READINESS_SCHEMA_VERSION = "target_readiness_report_v1";

function reviewItem(
  itemId: string,
  warnings: { code: string; message: string; blocking: boolean }[],
): DigiExamIrItem {
  return {
    alternatives: [],
    answerKey: { provenance: "not_applicable" },
    embeddedAssetReferences: [],
    embeddedAssets: [],
    gaps: [],
    itemId,
    itemType: "open_ended",
    maxScore: 2,
    options: [],
    promptHtml: null,
    promptLines: ["Skriv ett svar."],
    sequence: Number(itemId.slice(-1)),
    title: itemId === "item-001" ? "Bild saknas i frågan" : "Question 2",
    warnings,
  };
}

function reviewItemPayload(
  itemId: string,
  warnings: { code: string; message: string; blocking: boolean }[],
): Record<string, unknown> {
  return {
    alternatives: [],
    answer_key: { provenance: "not_applicable" },
    embedded_asset_references: [],
    embedded_assets: [],
    gaps: [],
    item_id: itemId,
    item_type: "open_ended",
    max_score: 2,
    options: [],
    prompt_html: null,
    prompt_lines: ["Skriv ett svar."],
    sequence: Number(itemId.slice(-1)),
    title: itemId === "item-001" ? "Bild saknas i frågan" : "Question 2",
    warnings,
  };
}

function buildSourceRepairProjection() {
  const irJson = {
    items: [
      reviewItemPayload("item-001", [
        { code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE, message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1, blocking: false },
      ]),
      reviewItemPayload("item-002", [
        { code: DIGIEXAM_WARNING_MISSING_QUESTION_TITLE, message: CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2, blocking: false },
      ]),
    ],
    manual_follow_ups: [],
    schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    source_filename: "synthetic-repairs.dxe",
    warnings: [],
  };
  const migrationManifest = {
    asset_count: 0,
    asset_summaries: [],
    item_count: 2,
    item_summaries: [
      { answer_key_provenance: "not_applicable", asset_summaries: [], item_id: "item-001", item_type: "open_ended", manual_follow_up_required: false, sequence: 1, source_item_fingerprint: "sha256:item-001", title: "Bild saknas i frågan" },
      { answer_key_provenance: "not_applicable", asset_summaries: [], item_id: "item-002", item_type: "open_ended", manual_follow_up_required: false, sequence: 2, source_item_fingerprint: "sha256:item-002", title: "Question 2" },
    ],
    manual_follow_up_count: 0,
    parse_status: "success",
    renderer_ready: true,
    schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
    source_filename: "synthetic-repairs.dxe",
    source_producer: null,
    warning_count: 2,
  };
  const targetReadinessReport = parseTargetReadinessReport({
    effective_exam_sha256: "sha256:effective",
    job_id: "job-synthetic",
    schema_version: READINESS_SCHEMA_VERSION,
    source_ir_sha256: "sha256:ir",
    targets: [
      {
        artifact_key: "examnet_pdf",
        export_enabled: true,
        item_id: null,
        message_key: "exam_converter.target.ready",
        reason_code: "target_available",
        readiness: DIGIEXAM_TARGET_READY,
        retryable: false,
        sequence: null,
        source_item_fingerprint: null,
        target: "examnet_pdf",
        teacher_action: "none",
      },
    ],
  });
  const artifactManifest = {
    artifacts: [],
    bundle_status: EXAM_CONVERTER_BUNDLE_STATUS_COMPLETE,
    job_id: "job-synthetic",
    manual_follow_up: { artifact_key: DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT, count: 0, required: false },
    readiness: {
      artifact_key: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
      exportable_targets: ["examnet_pdf"],
      review_required: false,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    source: { filename: "synthetic-repairs.dxe", format: DIGIEXAM_SOURCE_FORMAT, sha256: "sha256:source" },
    source_binding: {
      effective_exam_schema_version: "digiexam_effective_exam_v2",
      effective_exam_sha256: "sha256:effective",
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ir",
    },
    warnings: { artifact_key: DIGIEXAM_ARTIFACT_WARNINGS_REPORT, count: 2 },
  };
  const answerKeyReviewStateReport = {
    items: [
      {
        choice_ids: [],
        correction_affordances: [],
        current_key_origin: "none",
        gap_ids: [],
        item_id: "item-001",
        item_type: "open_ended",
        message_key: "exam_converter.answer_key.not_applicable",
        reasons: ["answer_key_not_applicable"],
        replay_artifact_references: [],
        review_state: "review_complete",
        sequence: 1,
        source_item_fingerprint: "sha256:item-001",
      },
      {
        choice_ids: [],
        correction_affordances: [],
        current_key_origin: "none",
        gap_ids: [],
        item_id: "item-002",
        item_type: "open_ended",
        message_key: "exam_converter.answer_key.not_applicable",
        reasons: ["answer_key_not_applicable"],
        replay_artifact_references: [],
        review_state: "review_complete",
        sequence: 2,
        source_item_fingerprint: "sha256:item-002",
      },
    ],
    schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  };
  return parseExamConverterReviewProjection({
    answerKeyReviewStateReport,
    artifactManifest,
    irJson,
    migrationManifest,
    targetReadinessReport,
  });
}

describe("isReviewWarningCode", () => {
  it("accepts only the two source-repair warning codes", () => {
    expect(isReviewWarningCode(DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE)).toBe(true);
    expect(isReviewWarningCode(DIGIEXAM_WARNING_MISSING_QUESTION_TITLE)).toBe(true);
  });

  it("rejects unrelated parser warning codes and non-string values", () => {
    expect(isReviewWarningCode("missing_embedded_asset_reference")).toBe(false);
    expect(isReviewWarningCode("missing_answer_key_provenance")).toBe(false);
    expect(isReviewWarningCode("")).toBe(false);
    expect(isReviewWarningCode(42)).toBe(false);
    expect(isReviewWarningCode(null)).toBe(false);
    expect(isReviewWarningCode(undefined)).toBe(false);
  });
});

describe("projectQuestionReviewRow", () => {
  it("projects the exact canonical image message onto the affected question", () => {
    const question = projectQuestionReviewRow(
      reviewItem("item-001", [
        { code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE, message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1, blocking: false },
      ]),
      [],
      "sha256:item-001",
      null,
    );

    expect(question.reviewWarnings).toEqual([
      {
        code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE,
        message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1,
      },
    ]);
    expect(question.status).toBe("attention");
  });

  it("projects the exact canonical title message onto the affected question", () => {
    const question = projectQuestionReviewRow(
      reviewItem("item-002", [
        { code: DIGIEXAM_WARNING_MISSING_QUESTION_TITLE, message: CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2, blocking: false },
      ]),
      [],
      "sha256:item-002",
      null,
    );

    expect(question.reviewWarnings).toEqual([
      {
        code: DIGIEXAM_WARNING_MISSING_QUESTION_TITLE,
        message: CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2,
      },
    ]);
    expect(question.reviewWarnings[0].message).toBe(CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2);
  });

  it("keeps payload order and filters out unrelated warning codes", () => {
    const question = projectQuestionReviewRow(
      reviewItem("item-001", [
        {
          code: "missing_embedded_asset_reference",
          message: "En annan parser-varning som inte är en källreparation.",
          blocking: false,
        },
        { code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE, message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1, blocking: false },
      ]),
      [],
      "sha256:item-001",
      null,
    );

    expect(question.reviewWarnings).toEqual([
      {
        code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE,
        message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1,
      },
    ]);
  });
});

describe("parseExamConverterReviewProjection report", () => {
  it("counts affected questions and lists their labels", () => {
    const projection = buildSourceRepairProjection();

    expect(projection.report.missingImageCount).toBe(1);
    expect(projection.report.missingTitleCount).toBe(1);
    expect(projection.report.sourceRepairQuestions).toEqual([
      {
        itemId: "item-001",
        sequence: 1,
        title: "Bild saknas i frågan",
        reviewWarnings: [
          {
            code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE,
            message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1,
          },
        ],
      },
      {
        itemId: "item-002",
        sequence: 2,
        title: "Question 2",
        reviewWarnings: [
          {
            code: DIGIEXAM_WARNING_MISSING_QUESTION_TITLE,
            message: CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2,
          },
        ],
      },
    ]);
    expect(projection.report.warningCount).toBe(2);
  });

  it("preserves the exact canonical strings in the report messages", () => {
    const projection = buildSourceRepairProjection();
    const messages = projection.report.sourceRepairQuestions.flatMap((question) =>
      question.reviewWarnings.map((warning) => warning.message),
    );

    expect(messages).toEqual([
      CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1,
      CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2,
    ]);
  });

  it("associates each warning only with its own question row", () => {
    const projection = buildSourceRepairProjection();
    const questionsById = new Map(
      projection.questions.map((question) => [question.itemId, question]),
    );

    expect(questionsById.get("item-001")?.reviewWarnings).toEqual([
      { code: DIGIEXAM_WARNING_MISSING_PROMPT_IMAGE, message: CANONICAL_IMAGE_MESSAGE_FOR_QUESTION_1 },
    ]);
    expect(questionsById.get("item-002")?.reviewWarnings).toEqual([
      { code: DIGIEXAM_WARNING_MISSING_QUESTION_TITLE, message: CANONICAL_TITLE_MESSAGE_FOR_QUESTION_2 },
    ]);
    expect(questionsById.get("item-002")?.title).toBe("Question 2");
    expect(questionsById.get("item-002")?.manualFollowUpMessages.length).toBe(0);
  });
});
