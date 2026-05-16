/**
 * DigiExam IR review projection.
 *
 * Domain purpose:
 *   Validate the read-only DigiExam IR artifacts Skriptoteket needs and
 *   project them into a teacher-facing Exam Converter review model.
 *
 * Relationships:
 *   - Consumes Sir Convert `ir_json` and `migration_manifest` named artifacts.
 *   - Feeds authenticated Exam Converter inspection components.
 *   - Does not mutate IR, create local review state, or invent missing data.
 */

import type {
  DigiExamIngestionOverlay,
  DigiExamItemType,
  DigiExamMigrationTarget,
  DigiExamTargetReadinessReport,
  DigiExamTargetReadinessRow,
  SirConvertArtifactAvailability,
  SirConvertArtifactEntry,
  SirConvertArtifactManifest,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ACCEPT_CURRENT_STATE_DECISION_KIND,
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
  DIGIEXAM_ITEM_TYPES,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
  DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  SIR_CONVERT_ARTIFACT_NOT_REQUESTED,
} from "../../../api/sirConvertGateway/contractValues";
import {
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
} from "../../../api/sirConvertGateway/schemaVersions";
import {
  projectQuestionReviewRow,
  type DigiExamIrAlternative,
  type DigiExamIrAnswerKey,
  type DigiExamIrEmbeddedAsset,
  type DigiExamIrEmbeddedAssetReference,
  type DigiExamIrItem,
  type DigiExamIrManualFollowUp,
  type ExamConverterQuestionReviewRow,
} from "./digiexamIrQuestionReviewProjection";

export type {
  ExamConverterLucktextImage,
  ExamConverterLucktextStructure,
  ExamConverterMissingFieldLabel,
  ExamConverterQuestionAlternative,
  ExamConverterQuestionReviewRow,
  ExamConverterQuestionReviewStatus,
} from "./digiexamIrQuestionReviewProjection";

export type ExamConverterInspectionMode = "questions" | "files" | "report";

export type ExamConverterReviewFile = {
  artifactKey: string;
  availability: SirConvertArtifactAvailability;
  contentType: string;
  exportEnabled: boolean;
  filename: string;
  kindLabel: string;
  reasonCode: string | null;
  readiness: DigiExamTargetReadinessRow["readiness"] | null;
  sha256: string | null;
  sizeBytes: number | null;
  sizeLabel: string | null;
  statusLabel: string;
  unavailableCode: string | null;
};

export type ExamConverterReportProjection = {
  attentionQuestionCount: number;
  missingAnswerKeyCount: number;
  missingPointsCount: number;
  warningCount: number;
};

export type ExamConverterReviewProjection = {
  sourceFilename: string;
  questions: ExamConverterQuestionReviewRow[];
  files: ExamConverterReviewFile[];
  report: ExamConverterReportProjection;
  defaultMode: ExamConverterInspectionMode;
  acceptedStateOverlay: DigiExamIngestionOverlay | null;
};

type JsonRecord = Record<string, unknown>;

type DigiExamIntermediateExam = {
  sourceFilename: string;
  items: DigiExamIrItem[];
  warnings: JsonRecord[];
  manualFollowUps: DigiExamIrManualFollowUp[];
};

type DigiExamIrManifest = {
  warningCount: number;
  manualFollowUpCount: number;
  itemSummaries: Map<string, DigiExamIrManifestItemSummary>;
};

type DigiExamIrManifestItemSummary = {
  itemId: string;
  itemType: DigiExamItemType;
  sourceItemFingerprint: string;
};

const IR_SCHEMA_VERSION = DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION;
const MANIFEST_SCHEMA_VERSION = DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION;
const TARGET_FILE_LABELS: Record<string, string> = {
  [DIGIEXAM_TARGET_EXAMNET_PDF]: "PDF",
  [DIGIEXAM_TARGET_QTI_PACKAGE]: "QTI-format",
};

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`DigiExam review artifact field '${fieldName}' is not an object.`);
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`DigiExam review artifact field '${fieldName}' is missing.`);
}

function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`DigiExam review artifact field '${fieldName}' is not a number.`);
}

function readNullableNumber(value: unknown, fieldName: string): number | null {
  if (value === null || value === undefined) return null;
  return readNumber(value, fieldName);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`DigiExam review artifact field '${fieldName}' is not a string.`);
}

function readStringArray(value: unknown, fieldName: string): string[] {
  if (!Array.isArray(value)) {
    throw new Error(`DigiExam review artifact field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readString(entry, `${fieldName}[${index}]`));
}

function readDigiExamItemType(value: unknown, fieldName: string): DigiExamItemType {
  const itemType = readString(value, fieldName);
  if (DIGIEXAM_ITEM_TYPES.includes(itemType as DigiExamItemType)) {
    return itemType as DigiExamItemType;
  }
  throw new Error(`DigiExam review artifact field '${fieldName}' has unknown item type.`);
}

function readRecordArray(value: unknown, fieldName: string): JsonRecord[] {
  if (!Array.isArray(value)) {
    throw new Error(`DigiExam review artifact field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readRecord(entry, `${fieldName}[${index}]`));
}

function readOptionalStringArray(value: unknown, fieldName: string): string[] {
  if (value === null || value === undefined) return [];
  return readStringArray(value, fieldName);
}

function readOptionalRecordArray(value: unknown, fieldName: string): JsonRecord[] {
  if (value === null || value === undefined) return [];
  return readRecordArray(value, fieldName);
}

function parseAnswerKey(value: unknown): DigiExamIrAnswerKey {
  const record = readRecord(value, "item.answer_key");
  return {
    provenance: readString(record.provenance, "item.answer_key.provenance"),
  };
}

function parseAlternative(value: unknown, fieldName: string): DigiExamIrAlternative {
  const record = readRecord(value, fieldName);
  return {
    id: readNumber(record.id, `${fieldName}.id`),
    title: typeof record.title === "string" ? record.title : "",
    about: typeof record.about === "string" ? record.about : "",
  };
}

function parseEmbeddedAsset(value: unknown, fieldName: string): DigiExamIrEmbeddedAsset {
  const record = readRecord(value, fieldName);
  return {
    assetId: readString(record.asset_id, `${fieldName}.asset_id`),
    mediaType: readString(record.media_type, `${fieldName}.media_type`),
    contentBase64: readNullableString(record.content_base64, `${fieldName}.content_base64`),
    sourceImageIndex: readNumber(record.source_image_index, `${fieldName}.source_image_index`),
    widthPx: readNullableNumber(record.width_px, `${fieldName}.width_px`),
    heightPx: readNullableNumber(record.height_px, `${fieldName}.height_px`),
  };
}

function parseEmbeddedAssetReference(
  value: unknown,
  fieldName: string,
): DigiExamIrEmbeddedAssetReference {
  const record = readRecord(value, fieldName);
  return {
    assetId: readString(record.asset_id, `${fieldName}.asset_id`),
    sourceImageIndex: readNumber(record.source_image_index, `${fieldName}.source_image_index`),
    referenceOrder: readNumber(record.reference_order, `${fieldName}.reference_order`),
  };
}

function parseItem(value: unknown): DigiExamIrItem {
  const record = readRecord(value, "item");
  return {
    itemId: readString(record.item_id, "item.item_id"),
    sequence: readNumber(record.sequence, "item.sequence"),
    title: readString(record.title, "item.title"),
    itemType: readDigiExamItemType(record.item_type, "item.item_type"),
    promptHtml: readNullableString(record.prompt_html, "item.prompt_html"),
    promptLines: readStringArray(record.prompt_lines, "item.prompt_lines"),
    maxScore: readNullableNumber(record.max_score, "item.max_score"),
    answerKey: parseAnswerKey(record.answer_key),
    warnings: readRecordArray(record.warnings, "item.warnings"),
    options: readOptionalStringArray(record.options, "item.options"),
    alternatives: readOptionalRecordArray(record.alternatives, "item.alternatives").map(
      (entry, index) => parseAlternative(entry, `item.alternatives[${index}]`),
    ),
    gaps: readOptionalRecordArray(record.gaps, "item.gaps"),
    embeddedAssets: readOptionalRecordArray(
      record.embedded_assets,
      "item.embedded_assets",
    ).map((entry, index) => parseEmbeddedAsset(entry, `item.embedded_assets[${index}]`)),
    embeddedAssetReferences: readOptionalRecordArray(
      record.embedded_asset_references,
      "item.embedded_asset_references",
    ).map((entry, index) =>
      parseEmbeddedAssetReference(entry, `item.embedded_asset_references[${index}]`),
    ),
  };
}

function parseManualFollowUp(value: unknown): DigiExamIrManualFollowUp {
  const record = readRecord(value, "manual_follow_up");
  return {
    itemId: readString(record.item_id, "manual_follow_up.item_id"),
    reason: readString(record.reason, "manual_follow_up.reason"),
    message: typeof record.message === "string" ? record.message : "",
  };
}

function parseIntermediateExam(payload: unknown): DigiExamIntermediateExam {
  const root = readRecord(payload, DIGIEXAM_ARTIFACT_IR_JSON);
  if (root.schema_version !== IR_SCHEMA_VERSION) {
    throw new Error("DigiExam IR artifact has an unsupported schema version.");
  }
  return {
    sourceFilename: readString(root.source_filename, "source_filename"),
    items: readRecordArray(root.items, "items").map(parseItem),
    warnings: readRecordArray(root.warnings, "warnings"),
    manualFollowUps: readRecordArray(root.manual_follow_ups, "manual_follow_ups").map(
      parseManualFollowUp,
    ),
  };
}

function parseIrManifest(payload: unknown): DigiExamIrManifest {
  const root = readRecord(payload, DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST);
  if (root.schema_version !== MANIFEST_SCHEMA_VERSION) {
    throw new Error("DigiExam migration manifest has an unsupported schema version.");
  }
  const itemSummaries = new Map<string, DigiExamIrManifestItemSummary>();
  for (const entry of readRecordArray(root.item_summaries, "item_summaries")) {
    const itemId = readString(entry.item_id, "item_summaries[].item_id");
    itemSummaries.set(itemId, {
      itemId,
      itemType: readDigiExamItemType(entry.item_type, "item_summaries[].item_type"),
      sourceItemFingerprint: readString(
        entry.source_item_fingerprint,
        "item_summaries[].source_item_fingerprint",
      ),
    });
  }
  return {
    warningCount: readNumber(root.warning_count, "warning_count"),
    manualFollowUpCount: readNumber(root.manual_follow_up_count, "manual_follow_up_count"),
    itemSummaries,
  };
}

function sizeLabel(sizeBytes: number | null): string | null {
  if (sizeBytes === null) return null;
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) {
    return `${Math.round(sizeBytes / 1024).toLocaleString("sv-SE")} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toLocaleString("sv-SE", {
    maximumFractionDigits: 1,
  })} MB`;
}

function readinessRowsForTarget(
  report: DigiExamTargetReadinessReport,
  target: string,
): DigiExamTargetReadinessRow[] {
  return report.targets.filter((row) => row.target === target);
}

function primaryReadinessRow(rows: DigiExamTargetReadinessRow[]): DigiExamTargetReadinessRow | null {
  return rows.find((row) => !row.export_enabled) ?? rows[0] ?? null;
}

function exportEnabledForFile(
  entry: SirConvertArtifactEntry,
  rows: DigiExamTargetReadinessRow[],
): boolean {
  return (
    entry.availability === SIR_CONVERT_ARTIFACT_AVAILABLE &&
    rows.some((row) => row.export_enabled)
  );
}

function statusLabelForFile(params: {
  availability: SirConvertArtifactAvailability;
  exportEnabled: boolean;
  readinessRow: DigiExamTargetReadinessRow | null;
  unavailableCode: string | null;
}): string {
  const { availability, exportEnabled, readinessRow, unavailableCode } = params;
  if (exportEnabled) {
    return "Kan hämtas";
  }
  if (availability === SIR_CONVERT_ARTIFACT_AVAILABLE) {
    return "Granska eller godkänn först";
  }
  if (availability === SIR_CONVERT_ARTIFACT_NOT_REQUESTED) {
    return "Inte vald";
  }
  if (
    unavailableCode === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED ||
    readinessRow?.readiness === DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY ||
    readinessRow?.readiness === DIGIEXAM_TARGET_NEEDS_TEACHER_REVIEW_DECISION
  ) {
    return "Granska eller godkänn först";
  }
  return "Kunde inte skapas";
}

function isTargetFile(entry: SirConvertArtifactEntry): boolean {
  return entry.artifact_key in TARGET_FILE_LABELS;
}

function projectFiles(
  artifactManifest: SirConvertArtifactManifest,
  targetReadinessReport: DigiExamTargetReadinessReport,
): ExamConverterReviewFile[] {
  return artifactManifest.artifacts.filter(isTargetFile).map((entry) => {
    const rows = readinessRowsForTarget(targetReadinessReport, entry.artifact_key);
    const readinessRow = primaryReadinessRow(rows);
    const exportEnabled = exportEnabledForFile(entry, rows);
    return {
      artifactKey: entry.artifact_key,
      availability: entry.availability,
      contentType: entry.content_type,
      exportEnabled,
      filename: entry.filename,
      kindLabel: TARGET_FILE_LABELS[entry.artifact_key] ?? entry.artifact_key,
      reasonCode: readinessRow?.reason_code ?? entry.unavailable_code ?? null,
      readiness: readinessRow?.readiness ?? null,
      sha256: entry.sha256,
      sizeBytes: entry.size_bytes,
      sizeLabel: sizeLabel(entry.size_bytes),
      statusLabel: statusLabelForFile({
        availability: entry.availability,
        exportEnabled,
        readinessRow,
        unavailableCode: entry.unavailable_code ?? null,
      }),
      unavailableCode: entry.unavailable_code ?? null,
    };
  });
}

function followUpsByItemId(
  followUps: DigiExamIrManualFollowUp[],
): Map<string, DigiExamIrManualFollowUp[]> {
  const grouped = new Map<string, DigiExamIrManualFollowUp[]>();
  for (const followUp of followUps) {
    const current = grouped.get(followUp.itemId) ?? [];
    current.push(followUp);
    grouped.set(followUp.itemId, current);
  }
  return grouped;
}

export function parseExamConverterReviewProjection(params: {
  artifactManifest: SirConvertArtifactManifest;
  irJson: unknown;
  migrationManifest: unknown;
  targetReadinessReport: DigiExamTargetReadinessReport;
}): ExamConverterReviewProjection {
  const exam = parseIntermediateExam(params.irJson);
  const manifest = parseIrManifest(params.migrationManifest);
  const followUps = followUpsByItemId(exam.manualFollowUps);

  const questions = exam.items.map((item): ExamConverterQuestionReviewRow => {
    const itemFollowUps = followUps.get(item.itemId) ?? [];
    const itemSummary = manifest.itemSummaries.get(item.itemId);
    return projectQuestionReviewRow(
      item,
      itemFollowUps,
      itemSummary?.sourceItemFingerprint ?? null,
    );
  });

  const missingDataQuestionCount = questions.filter(
    (question) => question.missingFields.length > 0,
  ).length;
  const hasQuestionReview = missingDataQuestionCount > 0 || manifest.warningCount > 0;

  return {
    sourceFilename: exam.sourceFilename,
    questions,
    files: projectFiles(params.artifactManifest, params.targetReadinessReport),
    report: {
      attentionQuestionCount: missingDataQuestionCount,
      missingAnswerKeyCount: questions.filter((question) =>
        question.missingFields.includes("Facit"),
      ).length,
      missingPointsCount: questions.filter((question) =>
        question.missingFields.includes("Poäng"),
      ).length,
      warningCount: Math.max(manifest.warningCount, exam.warnings.length),
    },
    defaultMode: hasQuestionReview ? "questions" : "files",
    acceptedStateOverlay: buildAcceptedCurrentStateOverlay({
      artifactManifest: params.artifactManifest,
      questions,
    }),
  };
}

function buildAcceptedCurrentStateOverlay(params: {
  artifactManifest: SirConvertArtifactManifest;
  questions: ExamConverterQuestionReviewRow[];
}): DigiExamIngestionOverlay | null {
  const acceptedTargets = params.artifactManifest.artifacts
    .filter(isTargetFile)
    .filter((entry) => entry.availability !== SIR_CONVERT_ARTIFACT_NOT_REQUESTED)
    .map((entry) => entry.artifact_key as DigiExamMigrationTarget);
  const items = params.questions
    .filter((question) => question.missingFields.length > 0)
    .filter((question) => question.sourceItemFingerprint !== null)
    .map((question) => ({
      effective_item_patch: null,
      item_id: question.itemId,
      manual_answer_key: null,
      sequence: question.sequence,
      item_type: question.itemType,
      source_item_fingerprint: question.sourceItemFingerprint as string,
      review_decision: {
        kind: DIGIEXAM_ACCEPT_CURRENT_STATE_DECISION_KIND,
        decision_id: `accept-current-state-${question.itemId}`,
        note: null,
        accepted_targets: acceptedTargets,
      },
      reviewed_completion_answer_key: null,
    }));

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
