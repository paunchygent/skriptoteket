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
  SirConvertArtifactAvailability,
  SirConvertArtifactEntry,
  SirConvertArtifactManifest,
} from "../../../api/sirConvertGateway";

export type ExamConverterInspectionMode = "questions" | "files" | "report";
export type ExamConverterMissingFieldLabel = "Facit" | "Poäng";
export type ExamConverterQuestionReviewStatus = "complete" | "attention";

export type ExamConverterReviewFile = {
  artifactKey: string;
  availability: SirConvertArtifactAvailability;
  contentType: string;
  filename: string;
  kindLabel: string;
  sha256: string | null;
  sizeBytes: number | null;
  sizeLabel: string | null;
  statusLabel: string;
};

export type ExamConverterQuestionReviewRow = {
  itemId: string;
  sequence: number;
  title: string;
  typeLabel: string;
  pointsLabel: string;
  promptText: string;
  missingFields: ExamConverterMissingFieldLabel[];
  status: ExamConverterQuestionReviewStatus;
  manualFollowUpMessages: string[];
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
};

type JsonRecord = Record<string, unknown>;

type DigiExamIrAnswerKey = {
  provenance: string;
};

type DigiExamIrManualFollowUp = {
  itemId: string;
  reason: string;
  message: string;
};

type DigiExamIrItem = {
  itemId: string;
  sequence: number;
  title: string;
  itemType: string;
  promptHtml: string | null;
  promptLines: string[];
  maxScore: number | null;
  answerKey: DigiExamIrAnswerKey;
  warnings: JsonRecord[];
};

type DigiExamIntermediateExam = {
  sourceFilename: string;
  items: DigiExamIrItem[];
  warnings: JsonRecord[];
  manualFollowUps: DigiExamIrManualFollowUp[];
};

type DigiExamIrManifest = {
  warningCount: number;
  manualFollowUpCount: number;
};

const IR_SCHEMA_VERSION = "digiexam_intermediate_exam_v2";
const MANIFEST_SCHEMA_VERSION = "digiexam_ir_manifest_v2";
const TARGET_FILE_LABELS: Record<string, string> = {
  examnet_pdf: "PDF",
  qti_package: "QTI-format",
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

function readRecordArray(value: unknown, fieldName: string): JsonRecord[] {
  if (!Array.isArray(value)) {
    throw new Error(`DigiExam review artifact field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readRecord(entry, `${fieldName}[${index}]`));
}

function parseAnswerKey(value: unknown): DigiExamIrAnswerKey {
  const record = readRecord(value, "item.answer_key");
  return {
    provenance: readString(record.provenance, "item.answer_key.provenance"),
  };
}

function parseItem(value: unknown): DigiExamIrItem {
  const record = readRecord(value, "item");
  return {
    itemId: readString(record.item_id, "item.item_id"),
    sequence: readNumber(record.sequence, "item.sequence"),
    title: readString(record.title, "item.title"),
    itemType: readString(record.item_type, "item.item_type"),
    promptHtml: readNullableString(record.prompt_html, "item.prompt_html"),
    promptLines: readStringArray(record.prompt_lines, "item.prompt_lines"),
    maxScore: readNullableNumber(record.max_score, "item.max_score"),
    answerKey: parseAnswerKey(record.answer_key),
    warnings: readRecordArray(record.warnings, "item.warnings"),
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
  const root = readRecord(payload, "ir_json");
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
  const root = readRecord(payload, "migration_manifest");
  if (root.schema_version !== MANIFEST_SCHEMA_VERSION) {
    throw new Error("DigiExam migration manifest has an unsupported schema version.");
  }
  return {
    warningCount: readNumber(root.warning_count, "warning_count"),
    manualFollowUpCount: readNumber(root.manual_follow_up_count, "manual_follow_up_count"),
  };
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function promptTextForItem(item: DigiExamIrItem): string {
  const joinedLines = item.promptLines.join(" ").trim();
  if (joinedLines.length > 0) {
    return joinedLines;
  }
  if (item.promptHtml) {
    return stripHtml(item.promptHtml);
  }
  return item.title;
}

function typeLabelForItemType(itemType: string): string {
  switch (itemType) {
    case "gap_fill":
      return "Lucktext";
    case "matching":
      return "Matchning";
    case "multiple_choice":
    case "multiple_response":
      return "Flerval";
    case "open_ended":
      return "Fritext";
    case "single_choice":
      return "Enval";
    default:
      return "Okänd";
  }
}

function uniqueLabels(labels: ExamConverterMissingFieldLabel[]): ExamConverterMissingFieldLabel[] {
  return [...new Set(labels)];
}

function missingFieldsForItem(
  item: DigiExamIrItem,
  followUps: DigiExamIrManualFollowUp[],
): ExamConverterMissingFieldLabel[] {
  const labels: ExamConverterMissingFieldLabel[] = [];
  if (item.maxScore === null) {
    labels.push("Poäng");
  }
  if (followUps.some((followUp) => followUp.reason === "manual_answer_key_required")) {
    labels.push("Facit");
  }
  return uniqueLabels(labels);
}

function isActionableFollowUp(followUp: DigiExamIrManualFollowUp): boolean {
  return (
    followUp.reason === "manual_answer_key_required" ||
    followUp.reason === "unsupported_item_type" ||
    followUp.reason === "parser_warning_blocks_rendering"
  );
}

function isAttentionRow(params: {
  followUps: DigiExamIrManualFollowUp[];
  item: DigiExamIrItem;
  missingFields: ExamConverterMissingFieldLabel[];
}): boolean {
  return (
    params.missingFields.length > 0 ||
    params.followUps.some(isActionableFollowUp) ||
    params.item.warnings.length > 0
  );
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

function statusLabelForFile(
  availability: SirConvertArtifactAvailability,
  hasQuestionReview: boolean,
): string {
  if (availability === "available") {
    return hasQuestionReview
      ? "Kan hämtas när frågorna har kontrollerats"
      : "Kan hämtas";
  }
  if (availability === "not_requested") {
    return "Inte vald";
  }
  return "Kunde inte skapas";
}

function isTargetFile(entry: SirConvertArtifactEntry): boolean {
  return entry.artifact_key in TARGET_FILE_LABELS;
}

function projectFiles(
  artifactManifest: SirConvertArtifactManifest,
  hasQuestionReview: boolean,
): ExamConverterReviewFile[] {
  return artifactManifest.artifacts.filter(isTargetFile).map((entry) => ({
    artifactKey: entry.artifact_key,
    availability: entry.availability,
    contentType: entry.content_type,
    filename: entry.filename,
    kindLabel: TARGET_FILE_LABELS[entry.artifact_key] ?? entry.artifact_key,
    sha256: entry.sha256,
    sizeBytes: entry.size_bytes,
    sizeLabel: sizeLabel(entry.size_bytes),
    statusLabel: statusLabelForFile(entry.availability, hasQuestionReview),
  }));
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
}): ExamConverterReviewProjection {
  const exam = parseIntermediateExam(params.irJson);
  const manifest = parseIrManifest(params.migrationManifest);
  const followUps = followUpsByItemId(exam.manualFollowUps);

  const questions = exam.items.map((item): ExamConverterQuestionReviewRow => {
    const itemFollowUps = followUps.get(item.itemId) ?? [];
    const missingFields = missingFieldsForItem(item, itemFollowUps);
    const promptText = promptTextForItem(item);
    return {
      itemId: item.itemId,
      sequence: item.sequence,
      title: item.title || promptText,
      typeLabel: typeLabelForItemType(item.itemType),
      pointsLabel: item.maxScore === null ? "—" : `${item.maxScore.toLocaleString("sv-SE")} p`,
      promptText,
      missingFields,
      status: isAttentionRow({ followUps: itemFollowUps, item, missingFields })
        ? "attention"
        : "complete",
      manualFollowUpMessages: itemFollowUps
        .map((followUp) => followUp.message)
        .filter((message) => message.length > 0),
    };
  });

  const missingDataQuestionCount = questions.filter(
    (question) => question.missingFields.length > 0,
  ).length;
  const hasQuestionReview = missingDataQuestionCount > 0 || manifest.warningCount > 0;

  return {
    sourceFilename: exam.sourceFilename,
    questions,
    files: projectFiles(params.artifactManifest, hasQuestionReview),
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
  };
}
