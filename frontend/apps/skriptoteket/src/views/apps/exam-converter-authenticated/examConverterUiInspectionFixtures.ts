/**
 * Exam Converter UI inspection fixtures.
 *
 * Domain purpose:
 *   Provide governed dev/test-only post-conversion Exam Converter states that
 *   the Codex internal browser can inspect without native file upload.
 *
 * Relationships:
 *   - Used only by the authenticated Exam Converter UI-inspection route.
 *   - Builds the same review projection consumed by production components.
 *   - Does not submit, poll, download, save, or unlock real artifacts.
 */

import type {
  DigiExamItemType,
  DigiExamTargetReadinessReport,
  SirConvertArtifactAvailability,
  SirConvertArtifactManifest,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
  DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  DIGIEXAM_SOURCE_FORMAT,
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
  DIGIEXAM_TARGET_QTI_PACKAGE,
  DIGIEXAM_TARGET_READY,
  DIGIEXAM_TARGET_UNSUPPORTED_TARGET_SHAPE,
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  SIR_CONVERT_ARTIFACT_UNAVAILABLE,
  SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
  SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
} from "../../../api/sirConvertGateway/contractValues";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
  DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "../../../api/sirConvertGateway/schemaVersions";
import {
  parseAnswerKeyCompletionReport,
  type ExamConverterAnswerKeyCompletionReport,
  type ExamConverterEffectiveAnswerKeyByItem,
  type ExamConverterEffectivePointCorrectionByItem,
} from "./digiexamAnswerKeyCompletionReport";
import {
  parseExamConverterReviewProjection,
  type ExamConverterInspectionMode,
  type ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import type { ExamConverterRuntimeOutcome } from "./useExamConverterConversionState";

export type ExamConverterUiInspectionFixtureId =
  | "complete-qti-ready"
  | "complete-qti-blocked"
  | "missing-facit"
  | "persisted-corrections"
  | "ai-facit-review"
  | "provider-only-advisory-failure";

export type ExamConverterUiInspectionFixture = {
  activeInspectionMode: ExamConverterInspectionMode;
  id: ExamConverterUiInspectionFixtureId;
  projection: ExamConverterReviewProjection;
  runtimeOutcome: ExamConverterRuntimeOutcome;
  sourceFile: File;
};

type ImportMetaEnvLike = {
  DEV?: boolean;
  MODE?: string;
};

type FixtureQuestion = {
  alternatives?: string[];
  answerKeyProvenance: string;
  gaps?: string[];
  itemId: string;
  itemType: DigiExamItemType;
  maxScore: number | null;
  prompt: string;
  sequence: number;
  title: string;
};

type FixtureOptions = {
  activeInspectionMode: ExamConverterInspectionMode;
  answerCompletionReport?: ExamConverterAnswerKeyCompletionReport | null;
  effectiveAnswerKeysByItem?: ExamConverterEffectiveAnswerKeyByItem | null;
  effectivePointCorrectionsByItem?: ExamConverterEffectivePointCorrectionByItem | null;
  id: ExamConverterUiInspectionFixtureId;
  qtiAvailability: SirConvertArtifactAvailability;
  qtiExportEnabled: boolean;
  qtiReasonCode: string;
  qtiReadiness: DigiExamTargetReadinessReport["targets"][number]["readiness"];
  questions: FixtureQuestion[];
};

const SOURCE_FILENAME = "exam-converter-ui-inspection.dxe";
const COMPLETE_QUESTIONS: FixtureQuestion[] = [
  completeQuestion(1, "item-001", "Stämmer det att nervtrådar leder elektriska impulser?"),
  completeQuestion(2, "item-002", "Vad kallas den del av hjärnan som vi tänker med?"),
  completeQuestion(3, "item-003", "Måste nervsignaler som utlöser reflexer kopplas om i hjärnan?"),
  completeQuestion(4, "item-004", "Hur fungerar en nervimpuls?", 2),
  completeQuestion(5, "item-005", "Ge exempel på något som styrs av nervsystemet."),
  completeQuestion(6, "item-006", "Nämn en orsak till att yngre vuxna tar större risker."),
  completeQuestion(7, "item-007", "Vad är myelin och hur påverkar det nervtrådarna?", 2),
  completeQuestion(8, "item-008", "Varför kan samma doft väcka olika minnen?"),
  completeQuestion(9, "item-009", "Varför smakar maten så lite när du är förkyld?", 2),
  completeQuestion(10, "item-010", "Var på kroppen har du flest känselkroppar?", 2),
  completeQuestion(11, "item-011", "Vilka symptom kan ökad sköldkörtelhormonproduktion orsaka?"),
  completeQuestion(12, "item-012", "Nämn tre körtlar som tillverkar hormoner."),
];

export const EXAM_CONVERTER_UI_INSPECTION_FIXTURE_IDS: readonly ExamConverterUiInspectionFixtureId[] =
  [
    "complete-qti-ready",
    "complete-qti-blocked",
    "missing-facit",
    "persisted-corrections",
    "ai-facit-review",
    "provider-only-advisory-failure",
  ] as const;

export function isExamConverterUiInspectionEnabled(
  env: ImportMetaEnvLike = import.meta.env,
): boolean {
  return env.DEV === true || env.MODE === "test";
}

export function getExamConverterUiInspectionFixture(
  fixtureId: string,
): ExamConverterUiInspectionFixture | null {
  if (!isExamConverterUiInspectionEnabled()) {
    return null;
  }
  if (!isExamConverterUiInspectionFixtureId(fixtureId)) {
    return null;
  }
  return buildFixture(FIXTURE_OPTIONS[fixtureId]);
}

function isExamConverterUiInspectionFixtureId(
  value: string,
): value is ExamConverterUiInspectionFixtureId {
  return EXAM_CONVERTER_UI_INSPECTION_FIXTURE_IDS.includes(
    value as ExamConverterUiInspectionFixtureId,
  );
}

function completeQuestion(
  sequence: number,
  itemId: string,
  prompt: string,
  maxScore = 1,
): FixtureQuestion {
  return {
    answerKeyProvenance: "dxe_populated_key",
    itemId,
    itemType: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
    maxScore,
    prompt,
    sequence,
    title: `Fråga ${sequence}`,
  };
}

function missingFacitQuestion(): FixtureQuestion {
  return {
    alternatives: [
      "DNA bär det genetiska materialet.",
      "Proteiner lagras i cellkärnan.",
      "Syre bildas när nervceller delar sig.",
      "Hormoner skapar kromosomer.",
    ],
    answerKeyProvenance: "absent",
    itemId: "item-001",
    itemType: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
    maxScore: 1,
    prompt: "Vilket påstående beskriver DNA bäst?",
    sequence: 1,
    title: "Fråga 1",
  };
}

function persistedCorrectionQuestions(): FixtureQuestion[] {
  return [
    {
      alternatives: [
        "DNA bär det genetiska materialet.",
        "Proteiner lagras i cellkärnan.",
        "Syre bildas när nervceller delar sig.",
        "Hormoner skapar kromosomer.",
      ],
      answerKeyProvenance: "absent",
      itemId: "item-001",
      itemType: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
      maxScore: 1,
      prompt: "Vilket påstående beskriver DNA bäst?",
      sequence: 1,
      title: "Fråga 1",
    },
    {
      answerKeyProvenance: "absent",
      gaps: ["gap-001", "gap-002"],
      itemId: "item-002",
      itemType: DIGIEXAM_ITEM_TYPE_GAP_FILL,
      maxScore: 1,
      prompt: "Fyll i luckorna om ekosystem.",
      sequence: 2,
      title: "Fråga 2",
    },
    {
      answerKeyProvenance: "dxe_populated_key",
      itemId: "item-003",
      itemType: DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
      maxScore: null,
      prompt: "Beskriv fotosyntesens delar.",
      sequence: 3,
      title: "Fotosyntesens delar",
    },
  ];
}

function persistedCorrectionAnswerKeys(): ExamConverterEffectiveAnswerKeyByItem {
  const gapAnswers: Record<string, string>[] = [
    { "gap-001": "kretslopp" },
    { "gap-002": "näringsväv" },
  ];
  return new Map([
    [
      "item-001",
      {
        correct_alternative_ids: [2],
        lineage: null,
        provenance: "teacher_provided",
      },
    ],
    [
      "item-002",
      {
        correct_gap_answers: gapAnswers,
        lineage: null,
        provenance: "teacher_provided",
      },
    ],
  ]);
}

function persistedCorrectionPointCorrections(): ExamConverterEffectivePointCorrectionByItem {
  return new Map([
    [
      "item-003",
      {
        effective_max_score: 3,
        kind: "item_points",
        source_item_fingerprint: "sha256:item-003",
        source_max_score: null,
      },
    ],
  ]);
}

function unresolvedAnswerKeyQuestionCount(options: FixtureOptions): number {
  return options.questions.filter(
    (question) =>
      question.answerKeyProvenance === "absent" &&
      !options.effectiveAnswerKeysByItem?.has(question.itemId),
  ).length;
}

function buildFixture(options: FixtureOptions): ExamConverterUiInspectionFixture {
  const projection = parseExamConverterReviewProjection({
    answerKeyCompletionReport: options.answerCompletionReport ?? null,
    artifactManifest: buildArtifactManifest(options),
    effectiveAnswerKeysByItem: options.effectiveAnswerKeysByItem ?? null,
    effectivePointCorrectionsByItem: options.effectivePointCorrectionsByItem ?? null,
    irJson: buildIrPayload(options.questions),
    migrationManifest: buildMigrationManifest(options.questions),
    targetReadinessReport: buildTargetReadinessReport(options),
  });
  return {
    activeInspectionMode: options.activeInspectionMode,
    id: options.id,
    projection,
    runtimeOutcome: {
      artifactCount: projection.files.length,
      bundleStatus:
        projection.report.attentionQuestionCount > 0 ||
        projection.report.blockedTargetFileCount > 0
          ? SIR_CONVERT_BUNDLE_STATUS_PARTIAL
          : SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
      manualFollowUpCount: projection.report.attentionQuestionCount,
      manualFollowUpRequired:
        projection.report.attentionQuestionCount > 0 ||
        projection.report.blockedTargetFileCount > 0,
      warningCount: projection.report.warningCount,
    },
    sourceFile: new File(["inspection"], SOURCE_FILENAME, {
      type: "application/octet-stream",
    }),
  };
}

function buildArtifactManifest(options: FixtureOptions): SirConvertArtifactManifest {
  return {
    artifacts: [
      artifact(DIGIEXAM_TARGET_EXAMNET_PDF, "exam-converter-ui-inspection.pdf"),
      artifact(DIGIEXAM_TARGET_QTI_PACKAGE, "exam-converter-ui-inspection-qti.zip", {
        availability: options.qtiAvailability,
        unavailableCode: options.qtiExportEnabled ? undefined : options.qtiReasonCode,
      }),
    ],
    bundle_status: SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
    job_id: `job_${options.id}`,
    manual_follow_up: {
      artifact_key: DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT,
      count: unresolvedAnswerKeyQuestionCount(options),
      required: unresolvedAnswerKeyQuestionCount(options) > 0,
    },
    readiness: {
      artifact_key: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
      exportable_targets: options.qtiExportEnabled
        ? [DIGIEXAM_TARGET_EXAMNET_PDF, DIGIEXAM_TARGET_QTI_PACKAGE]
        : [DIGIEXAM_TARGET_EXAMNET_PDF],
      review_required: unresolvedAnswerKeyQuestionCount(options) > 0,
    },
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    source: {
      filename: SOURCE_FILENAME,
      format: DIGIEXAM_SOURCE_FORMAT,
      sha256: "sha256:ui-inspection-source",
    },
    source_binding: {
      effective_exam_schema_version: DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
      effective_exam_sha256: "sha256:ui-inspection-effective",
      source_ir_schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
      source_ir_sha256: "sha256:ui-inspection-ir",
    },
    warnings: {
      artifact_key: DIGIEXAM_ARTIFACT_WARNINGS_REPORT,
      count: 0,
    },
  };
}

function artifact(
  artifactKey: string,
  filename: string,
  options: {
    availability?: SirConvertArtifactAvailability;
    unavailableCode?: string;
  } = {},
) {
  const availability = options.availability ?? SIR_CONVERT_ARTIFACT_AVAILABLE;
  return {
    artifact_key: artifactKey,
    availability,
    content_type: artifactKey === DIGIEXAM_TARGET_QTI_PACKAGE ? "application/zip" : "application/pdf",
    filename,
    sha256: availability === SIR_CONVERT_ARTIFACT_AVAILABLE ? `sha256:${artifactKey}` : null,
    size_bytes: availability === SIR_CONVERT_ARTIFACT_AVAILABLE ? 128_000 : null,
    ...(options.unavailableCode ? { unavailable_code: options.unavailableCode } : {}),
  };
}

function buildTargetReadinessReport(options: FixtureOptions): DigiExamTargetReadinessReport {
  return {
    effective_exam_sha256: "sha256:ui-inspection-effective",
    job_id: `job_${options.id}`,
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    source_ir_sha256: "sha256:ui-inspection-ir",
    targets: [
      targetRow(DIGIEXAM_TARGET_EXAMNET_PDF, DIGIEXAM_TARGET_READY, true, "target_available"),
      targetRow(
        DIGIEXAM_TARGET_QTI_PACKAGE,
        options.qtiReadiness,
        options.qtiExportEnabled,
        options.qtiReasonCode,
      ),
    ],
  };
}

function targetRow(
  target: string,
  readiness: DigiExamTargetReadinessReport["targets"][number]["readiness"],
  exportEnabled: boolean,
  reasonCode: string,
) {
  return {
    artifact_key: exportEnabled ? target : null,
    export_enabled: exportEnabled,
    item_id: exportEnabled ? null : "item-001",
    message_key: `exam_converter.target.${reasonCode}`,
    reason_code: reasonCode,
    readiness,
    retryable: false,
    sequence: exportEnabled ? null : 1,
    source_item_fingerprint: exportEnabled ? null : "sha256:item-001",
    target,
    teacher_action: exportEnabled ? "none" : "review_target_reason",
  };
}

function buildIrPayload(questions: FixtureQuestion[]) {
  return {
    items: questions.map((question) => ({
      alternatives: question.alternatives?.map((title, index) => ({
        about: "",
        id: index + 1,
        right: false,
        title,
      })) ?? [],
      answer_key: { provenance: question.answerKeyProvenance },
      embedded_asset_references: [],
      embedded_assets: [],
      gaps: question.gaps?.map((gapId) => ({ gap_id: gapId })) ?? [],
      item_id: question.itemId,
      item_type: question.itemType,
      max_score: question.maxScore,
      options: [],
      prompt_html: null,
      prompt_lines: [question.prompt],
      sequence: question.sequence,
      title: question.title,
      warnings: [],
    })),
    manual_follow_ups: questions
      .filter((question) => question.answerKeyProvenance === "absent")
      .map((question) => ({
        item_id: question.itemId,
        message: "Manual answer key is required.",
        reason: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
        source_span: null,
      })),
    schema_version: DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    source_filename: SOURCE_FILENAME,
    warnings: [],
  };
}

function buildMigrationManifest(questions: FixtureQuestion[]) {
  return {
    item_count: questions.length,
    item_summaries: questions.map((question) => ({
      answer_key_provenance: question.answerKeyProvenance,
      asset_summaries: [],
      item_id: question.itemId,
      item_type: question.itemType,
      manual_follow_up_required: question.answerKeyProvenance === "absent",
      sequence: question.sequence,
      source_item_fingerprint: `sha256:${question.itemId}`,
      title: question.title,
    })),
    manual_follow_up_count: questions.filter((question) => question.answerKeyProvenance === "absent")
      .length,
    parse_status: "success",
    renderer_ready: true,
    schema_version: DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
    source_filename: SOURCE_FILENAME,
    source_producer: null,
    warning_count: 0,
  };
}

function completionReportForMissingFacit(): ExamConverterAnswerKeyCompletionReport {
  return parseAnswerKeyCompletionReport({
    completionReportSha256: "sha256:ui-inspection-completion-report",
    payload: {
      completion_mode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      items: [
        {
          answer_payload: {
            correct_alternative_ids: [1],
            kind: "choice",
          },
          backend_failure_code: null,
          backend_status: "completed",
          candidate_id: "candidate-item-001",
          candidate_payload_digest: "sha256:candidate-item-001",
          decision_state: "suggested",
          item_id: "item-001",
          item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
          model_profile: "local-ui-inspection",
          prompt_template_version: "ui-inspection-v1",
          provider_profile_id: "local-fixture",
          schema_name: "digiexam_answer_key_completion",
          schema_version: "v1",
          sequence: 1,
          validation_state: "valid",
        },
      ],
      schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
    },
  });
}

function providerOnlyFailureCompletionReport(): ExamConverterAnswerKeyCompletionReport {
  return parseAnswerKeyCompletionReport({
    completionReportSha256: "sha256:ui-inspection-provider-failure-report",
    payload: {
      completion_mode: DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
      items: [
        {
          answer_payload: null,
          backend_failure_code: "provider_request_failed",
          backend_status: "failed",
          candidate_id: null,
          candidate_payload_digest: null,
          decision_state: "manual_follow_up_required",
          item_id: "item-001",
          item_type: DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
          model_profile: null,
          prompt_template_version: null,
          provider_profile_id: null,
          schema_name: null,
          schema_version: null,
          sequence: 1,
          validation_state: "manual_follow_up_required",
        },
      ],
      schema_version: ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
    },
  });
}

const MISSING_FACIT_QUESTIONS = [missingFacitQuestion(), ...COMPLETE_QUESTIONS.slice(1, 8)];

const FIXTURE_OPTIONS: Record<ExamConverterUiInspectionFixtureId, FixtureOptions> = {
  "ai-facit-review": {
    activeInspectionMode: "questions",
    answerCompletionReport: completionReportForMissingFacit(),
    id: "ai-facit-review",
    qtiAvailability: SIR_CONVERT_ARTIFACT_UNAVAILABLE,
    qtiExportEnabled: false,
    qtiReadiness: DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
    qtiReasonCode: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
    questions: MISSING_FACIT_QUESTIONS,
  },
  "complete-qti-blocked": {
    activeInspectionMode: "files",
    id: "complete-qti-blocked",
    qtiAvailability: SIR_CONVERT_ARTIFACT_UNAVAILABLE,
    qtiExportEnabled: false,
    qtiReadiness: DIGIEXAM_TARGET_UNSUPPORTED_TARGET_SHAPE,
    qtiReasonCode: "qti_package_export_disabled",
    questions: COMPLETE_QUESTIONS,
  },
  "complete-qti-ready": {
    activeInspectionMode: "questions",
    id: "complete-qti-ready",
    qtiAvailability: SIR_CONVERT_ARTIFACT_AVAILABLE,
    qtiExportEnabled: true,
    qtiReadiness: DIGIEXAM_TARGET_READY,
    qtiReasonCode: "target_available",
    questions: COMPLETE_QUESTIONS,
  },
  "missing-facit": {
    activeInspectionMode: "questions",
    id: "missing-facit",
    qtiAvailability: SIR_CONVERT_ARTIFACT_UNAVAILABLE,
    qtiExportEnabled: false,
    qtiReadiness: DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
    qtiReasonCode: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
    questions: MISSING_FACIT_QUESTIONS,
  },
  "persisted-corrections": {
    activeInspectionMode: "questions",
    effectiveAnswerKeysByItem: persistedCorrectionAnswerKeys(),
    effectivePointCorrectionsByItem: persistedCorrectionPointCorrections(),
    id: "persisted-corrections",
    qtiAvailability: SIR_CONVERT_ARTIFACT_AVAILABLE,
    qtiExportEnabled: true,
    qtiReadiness: DIGIEXAM_TARGET_READY,
    qtiReasonCode: "target_available",
    questions: persistedCorrectionQuestions(),
  },
  "provider-only-advisory-failure": {
    activeInspectionMode: "questions",
    answerCompletionReport: providerOnlyFailureCompletionReport(),
    id: "provider-only-advisory-failure",
    qtiAvailability: SIR_CONVERT_ARTIFACT_UNAVAILABLE,
    qtiExportEnabled: false,
    qtiReadiness: DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
    qtiReasonCode: DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
    questions: MISSING_FACIT_QUESTIONS,
  },
};
