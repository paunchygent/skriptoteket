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
  DigiExamItemType,
  DigiExamTargetReadinessReport,
  DigiExamTargetReadinessRow,
  SirConvertArtifactAvailability,
  SirConvertArtifactEntry,
  SirConvertArtifactManifest,
  SirConvertArtifactManifestSourceBinding,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
  DIGIEXAM_ITEM_TYPES,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  SIR_CONVERT_ARTIFACT_NOT_REQUESTED,
} from "../../../api/sirConvertGateway/contractValues";
import {
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
} from "../../../api/sirConvertGateway/schemaVersions";
import { digiExamTargetFileLabel, isDigiExamTargetFile } from "./digiexamTargetArtifacts";
import {
  projectQuestionReviewRow,
  type DigiExamIrAlternative,
  type DigiExamIrAnswerKey,
  type DigiExamIrEmbeddedAsset,
  type DigiExamIrEmbeddedAssetReference,
  type DigiExamIrGap,
  type DigiExamIrItem,
  type DigiExamIrManualFollowUp,
  type ExamConverterQuestionReviewRow,
} from "./digiexamIrQuestionReviewProjection";
import type {
  ExamConverterAnswerKeyCompletionReport,
  ExamConverterEffectiveAnswerKeyByItem,
  ExamConverterEffectivePointCorrectionByItem,
  ExamConverterLlmAnswerKeyCandidate,
} from "./digiexamAnswerKeyCompletionReport";

export type {
  ExamConverterLucktextImage,
  ExamConverterLucktextStructure,
  ExamConverterMissingFieldLabel,
  ExamConverterQuestionAlternative,
  ExamConverterQuestionGap,
  ExamConverterQuestionReviewRow,
  ExamConverterQuestionReviewStatus,
} from "./digiexamIrQuestionReviewProjection";

export type ExamConverterInspectionMode = "questions" | "files" | "report";

export type ExamConverterReviewFile = {
  artifactActionReference: ExamConverterReviewFileActionReference | null;
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

export type ExamConverterReviewFileActionReference = {
  artifactKey: string;
  authority: "original_job" | "replay_result";
};

export type ExamConverterAiSuggestionOutcome =
  | "accepted_unchanged"
  | "suppressed"
  | "teacher_edited"
  | "unresolved";

export type ExamConverterAiSuggestionReportItem = {
  itemId: string;
  outcome: ExamConverterAiSuggestionOutcome;
  sequence: number;
  title: string;
};

export type ExamConverterAiSuggestionReport = {
  acceptedUnchangedCount: number;
  items: ExamConverterAiSuggestionReportItem[];
  suppressedCount: number;
  teacherEditedCount: number;
  totalCount: number;
  unresolvedCount: number;
};

export type ExamConverterReportProjection = {
  attentionQuestionCount: number;
  aiSuggestionOutcomes: ExamConverterAiSuggestionReport;
  aiSuggestionCount: number;
  blockedTargetFileCount: number;
  missingAnswerKeyCount: number;
  missingPointsCount: number;
  warningCount: number;
};

export type ExamConverterReviewProjection = {
  sourceFilename: string;
  sourceFileSha256: string;
  artifactSourceBinding: SirConvertArtifactManifestSourceBinding;
  questions: ExamConverterQuestionReviewRow[];
  files: ExamConverterReviewFile[];
  report: ExamConverterReportProjection;
  defaultMode: ExamConverterInspectionMode;
  answerKeyCompletionReport: ExamConverterAnswerKeyCompletionReport | null;
  effectiveAnswerKeysByItem: ExamConverterEffectiveAnswerKeyByItem;
  effectivePointCorrectionsByItem: ExamConverterEffectivePointCorrectionByItem;
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

function parseGap(value: unknown, fieldName: string): DigiExamIrGap {
  const record = readRecord(value, fieldName);
  const gapId = typeof record.gap_id === "string" ? record.gap_id : record.guid;
  return {
    id: readString(gapId, `${fieldName}.gap_id`),
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
    gaps: readOptionalRecordArray(record.gaps, "item.gaps").map((entry, index) =>
      parseGap(entry, `item.gaps[${index}]`),
    ),
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
  artifactActionReference: ExamConverterReviewFileActionReference | null;
  availability: SirConvertArtifactAvailability;
  exportEnabled: boolean;
  readinessRow: DigiExamTargetReadinessRow | null;
  unavailableCode: string | null;
}): string {
  const { artifactActionReference, availability, exportEnabled, readinessRow, unavailableCode } =
    params;
  if (exportEnabled && artifactActionReference) {
    return "Kan hämtas";
  }
  if (exportEnabled && !artifactActionReference) {
    return "Filer kunde inte skapas";
  }
  if (availability === SIR_CONVERT_ARTIFACT_AVAILABLE) {
    return "Granska facit först";
  }
  if (availability === SIR_CONVERT_ARTIFACT_NOT_REQUESTED) {
    return "Inte vald";
  }
  if (
    unavailableCode === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED ||
    readinessRow?.readiness === DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY
  ) {
    return "Granska facit först";
  }
  return "Kunde inte skapas";
}

function projectFiles(
  artifactManifest: SirConvertArtifactManifest,
  targetReadinessReport: DigiExamTargetReadinessReport,
): ExamConverterReviewFile[] {
  return artifactManifest.artifacts.filter(isDigiExamTargetFile).map((entry) => {
    const rows = readinessRowsForTarget(targetReadinessReport, entry.artifact_key);
    const readinessRow = primaryReadinessRow(rows);
    const exportEnabled = exportEnabledForFile(entry, rows);
    const artifactActionReference =
      exportEnabled && entry.availability === SIR_CONVERT_ARTIFACT_AVAILABLE
        ? {
            artifactKey: entry.artifact_key,
            authority: "original_job" as const,
          }
        : null;
    return {
      artifactActionReference,
      artifactKey: entry.artifact_key,
      availability: entry.availability,
      contentType: entry.content_type,
      exportEnabled,
      filename: entry.filename,
      kindLabel: digiExamTargetFileLabel(entry.artifact_key),
      reasonCode: readinessRow?.reason_code ?? entry.unavailable_code ?? null,
      readiness: readinessRow?.readiness ?? null,
      sha256: entry.sha256,
      sizeBytes: entry.size_bytes,
      sizeLabel: sizeLabel(entry.size_bytes),
      statusLabel: statusLabelForFile({
        artifactActionReference,
        availability: entry.availability,
        exportEnabled,
        readinessRow,
        unavailableCode: entry.unavailable_code ?? null,
      }),
      unavailableCode: entry.unavailable_code ?? null,
    };
  });
}

function isTeacherDecisionBlockedFile(file: ExamConverterReviewFile): boolean {
  return (
    !file.exportEnabled &&
    (file.unavailableCode === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED ||
      file.readiness === DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY)
  );
}

function sortedQuestionItems(
  questions: ExamConverterQuestionReviewRow[],
  itemIds: Set<string>,
): ExamConverterQuestionReviewRow[] {
  return questions
    .filter((question) => itemIds.has(question.itemId))
    .sort((left, right) => left.sequence - right.sequence || left.title.localeCompare(right.title));
}

export function buildAiSuggestionReport(params: {
  acceptedUnchangedItemIds?: Set<string>;
  questions: ExamConverterQuestionReviewRow[];
  suppressedItemIds?: Set<string>;
  teacherEditedItemIds?: Set<string>;
}): ExamConverterAiSuggestionReport {
  const acceptedUnchangedItemIds = params.acceptedUnchangedItemIds ?? new Set<string>();
  const teacherEditedItemIds = params.teacherEditedItemIds ?? new Set<string>();
  const suppressedItemIds = params.suppressedItemIds ?? new Set<string>();
  const unresolvedItemIds = new Set(
    params.questions
      .filter(hasUsableCompletionCandidate)
      .map((question) => question.itemId)
      .filter(
        (itemId) =>
          !acceptedUnchangedItemIds.has(itemId) &&
          !teacherEditedItemIds.has(itemId) &&
          !suppressedItemIds.has(itemId),
      ),
  );
  const itemIds = new Set([
    ...acceptedUnchangedItemIds,
    ...teacherEditedItemIds,
    ...suppressedItemIds,
    ...unresolvedItemIds,
  ]);
  const items = sortedQuestionItems(params.questions, itemIds).map((question) => {
    let outcome: ExamConverterAiSuggestionOutcome = "unresolved";
    if (acceptedUnchangedItemIds.has(question.itemId)) {
      outcome = "accepted_unchanged";
    } else if (teacherEditedItemIds.has(question.itemId)) {
      outcome = "teacher_edited";
    } else if (suppressedItemIds.has(question.itemId)) {
      outcome = "suppressed";
    }
    return {
      itemId: question.itemId,
      outcome,
      sequence: question.sequence,
      title: question.title,
    };
  });
  return {
    acceptedUnchangedCount: items.filter((item) => item.outcome === "accepted_unchanged").length,
    items,
    suppressedCount: items.filter((item) => item.outcome === "suppressed").length,
    teacherEditedCount: items.filter((item) => item.outcome === "teacher_edited").length,
    totalCount: items.length,
    unresolvedCount: items.filter((item) => item.outcome === "unresolved").length,
  };
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
  answerKeyCompletionReport?: ExamConverterAnswerKeyCompletionReport | null;
  artifactManifest: SirConvertArtifactManifest;
  effectiveAnswerKeysByItem?: ExamConverterEffectiveAnswerKeyByItem | null;
  effectivePointCorrectionsByItem?: ExamConverterEffectivePointCorrectionByItem | null;
  irJson: unknown;
  migrationManifest: unknown;
  targetReadinessReport: DigiExamTargetReadinessReport;
}): ExamConverterReviewProjection {
  const exam = parseIntermediateExam(params.irJson);
  const manifest = parseIrManifest(params.migrationManifest);
  const followUps = followUpsByItemId(exam.manualFollowUps);
  const candidates = params.answerKeyCompletionReport?.itemsByItemId ?? new Map();

  const questions = exam.items.map((item): ExamConverterQuestionReviewRow => {
    const itemFollowUps = followUps.get(item.itemId) ?? [];
    const itemSummary = manifest.itemSummaries.get(item.itemId);
    return projectQuestionReviewRow(
      item,
      itemFollowUps,
      itemSummary?.sourceItemFingerprint ?? null,
      candidates.get(item.itemId) ?? null,
      params.effectiveAnswerKeysByItem?.get(item.itemId) ?? null,
      params.effectivePointCorrectionsByItem?.get(item.itemId) ?? null,
    );
  });

  const missingDataQuestionCount = questions.filter(
    (question) => question.missingFields.length > 0,
  ).length;
  const validAiSuggestionCount = questions.filter(hasUsableCompletionCandidate).length;
  const hasQuestionReview = missingDataQuestionCount > 0;
  const files = projectFiles(params.artifactManifest, params.targetReadinessReport);

  return {
    sourceFilename: exam.sourceFilename,
    sourceFileSha256: params.artifactManifest.source.sha256,
    artifactSourceBinding: params.artifactManifest.source_binding,
    questions,
    files,
    report: {
      attentionQuestionCount: missingDataQuestionCount,
      aiSuggestionOutcomes: buildAiSuggestionReport({ questions }),
      aiSuggestionCount: validAiSuggestionCount,
      blockedTargetFileCount: files.filter(isTeacherDecisionBlockedFile).length,
      missingAnswerKeyCount: questions.filter((question) =>
        question.missingFields.includes("Facit"),
      ).length,
      missingPointsCount: questions.filter((question) =>
        question.missingFields.includes("Poäng"),
      ).length,
      warningCount: Math.max(manifest.warningCount, exam.warnings.length),
    },
    defaultMode: hasQuestionReview || validAiSuggestionCount > 0 ? "questions" : "files",
    answerKeyCompletionReport: params.answerKeyCompletionReport ?? null,
    effectiveAnswerKeysByItem: params.effectiveAnswerKeysByItem ?? new Map(),
    effectivePointCorrectionsByItem: params.effectivePointCorrectionsByItem ?? new Map(),
  };
}

export function hasUsableCompletionCandidate(question: {
  llmCandidate: ExamConverterLlmAnswerKeyCandidate | null;
}): boolean {
  return (
    question.llmCandidate?.decisionState === "suggested" &&
    question.llmCandidate.validationState === "valid" &&
    question.llmCandidate.answerPayload !== null
  );
}

export function visibleMissingFieldsForQuestion(
  question: ExamConverterQuestionReviewRow,
): ExamConverterQuestionReviewRow["missingFields"] {
  if (!hasUsableCompletionCandidate(question)) return question.missingFields;
  return question.missingFields.filter((field) => field !== "Facit");
}
