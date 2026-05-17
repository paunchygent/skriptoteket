/**
 * Sir Convert Gateway adapter contracts.
 *
 * Purpose:
 *   Define the typed consumer protocol Skriptoteket uses for authenticated
 *   DigiExam migration through HuleEdu's Sir Convert product edge.
 *
 * Relationships:
 *   - `jobSpec.ts` builds the governed request shape.
 *   - `client.ts` transports these envelopes without conversion policy.
 */

import type { components } from "../sirConvertOpenapi";
import {
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_INGESTION_OVERLAY_POLICY_APPLY_TEACHER,
  DIGIEXAM_INGESTION_OVERLAY_POLICY_NONE,
  DIGIEXAM_MANUAL_FOLLOW_UP_POLICY_ITEM_ADDRESSABLE,
  DIGIEXAM_MIGRATION_OUTPUT_FORMAT,
  DIGIEXAM_REMOTE_PROVIDER_POLICY_FORBIDDEN,
  DIGIEXAM_RESULT_PDF_USAGE_CORRECT_MACHINE_MARKED,
  DIGIEXAM_SOURCE_FORMAT,
} from "./contractValues";
import type {
  DigiExamIntermediateExamSchemaVersion,
  DigiExamMigrationBundleSchemaVersion,
} from "./schemaVersions";

type SirConvertOpenApiSchemas = components["schemas"];

export type DigiExamMigrationTarget = SirConvertOpenApiSchemas["ExamMigrationTargetV2"];
export type DigiExamAnswerKeyCompletionMode =
  SirConvertOpenApiSchemas["DigiExamAnswerKeyCompletionModeV2"];
export type DigiExamAnswerKeyCompletionReport =
  SirConvertOpenApiSchemas["DigiExamAnswerKeyCompletionReportV1"];
export type DigiExamAnswerKeyCompletionReportItem =
  SirConvertOpenApiSchemas["DigiExamAnswerKeyCompletionReportItemV1"];
export type DigiExamMigrationArtifactKey =
  SirConvertOpenApiSchemas["DigiExamMigrationArtifactKey"];
export type DigiExamIngestionOverlay = SirConvertOpenApiSchemas["DigiExamIngestionOverlay"];
export type DigiExamEffectiveAnswerKey =
  SirConvertOpenApiSchemas["DigiExamEffectiveAnswerKeyV1"];
export type DigiExamEffectiveExam = SirConvertOpenApiSchemas["DigiExamEffectiveExamV1"];
export type DigiExamItemType = SirConvertOpenApiSchemas["DigiExamItemType"];
export type DigiExamTargetReadiness = SirConvertOpenApiSchemas["DigiExamTargetReadiness"];
export type DigiExamTargetReadinessRow =
  SirConvertOpenApiSchemas["DigiExamTargetReadinessRowV1"];
export type DigiExamTargetReadinessReport =
  SirConvertOpenApiSchemas["DigiExamTargetReadinessReportV1"];

export type SirConvertJobStatus =
  | "submitted"
  | "queued"
  | "running"
  | "processing"
  | "succeeded"
  | "failed"
  | "canceled"
  | "cancelled";

export type SirConvertBundleStatus =
  SirConvertOpenApiSchemas["DigiExamMigrationBundleManifestV2"]["bundle_status"];

export type SirConvertArtifactAvailability =
  SirConvertOpenApiSchemas["DigiExamMigrationArtifactAvailability"];

export type SirConvertDigiExamJobSpec = {
  api_version: "v2";
  source: {
    kind: "upload";
    filename: string;
    format: typeof DIGIEXAM_SOURCE_FORMAT;
  };
  conversion: {
    output_format: typeof DIGIEXAM_MIGRATION_OUTPUT_FORMAT;
    targets: DigiExamMigrationTarget[];
    artifact_language: string;
    reference_docx_filename: null;
  };
  digiexam_migration_options: {
    completion_mode: DigiExamAnswerKeyCompletionMode;
    graded_result_pdf_filename?: string;
    parity_pdf_filename?: string;
    remote_provider_policy: typeof DIGIEXAM_REMOTE_PROVIDER_POLICY_FORBIDDEN;
    result_pdf_usage: typeof DIGIEXAM_RESULT_PDF_USAGE_CORRECT_MACHINE_MARKED;
    manual_follow_up_policy: typeof DIGIEXAM_MANUAL_FOLLOW_UP_POLICY_ITEM_ADDRESSABLE;
    ingestion_overlay_filename?: string;
    ingestion_overlay_policy?:
      | typeof DIGIEXAM_INGESTION_OVERLAY_POLICY_NONE
      | typeof DIGIEXAM_INGESTION_OVERLAY_POLICY_APPLY_TEACHER;
  };
  retention: {
    pin: false;
  };
};

export type DigiExamMigrationSubmitParams = {
  file: File;
  gradedResultPdf?: File | null;
  parityPdf?: File | null;
  targets?: DigiExamMigrationTarget[];
  advisoryRetryAttempt?: number | null;
  artifactLanguage?: string;
  completionMode?: DigiExamAnswerKeyCompletionMode;
  waitSeconds?: number;
  correlationId?: string | null;
  sourceLabel?: string | null;
  ingestionOverlay?: DigiExamIngestionOverlay | null;
};

export type SirConvertRequestContext = {
  correlationId: string;
  idempotencyKey: string;
  jobSpec: SirConvertDigiExamJobSpec;
};

export type SirConvertJob = {
  jobId: string;
  status: SirConvertJobStatus;
};

export type SirConvertSubmittedJob = SirConvertJob & {
  idempotentReplay: boolean;
  requestContext: SirConvertRequestContext;
};

export type SirConvertTerminalResult = {
  job: SirConvertJob;
  artifact: {
    filename: string;
    content_type: string;
    sha256: string | null;
    size_bytes: number | null;
  };
  conversion_metadata: {
    route_key: string;
    bundle_schema_version: string;
    bundle_status: SirConvertBundleStatus;
    source_sha256: string | null;
    target_readiness_report_artifact_key: typeof DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT | null;
    manual_follow_up_required: boolean;
    warning_count: number;
    artifact_count: number;
  };
};

export type SirConvertArtifactEntry = {
  artifact_key: DigiExamMigrationArtifactKey | string;
  filename: string;
  content_type: string;
  availability: SirConvertArtifactAvailability;
  size_bytes: number | null;
  sha256: string | null;
  download_path?: string;
  unavailable_code?: string;
  depends_on?: string;
};

export type SirConvertArtifactManifestSource = {
  filename: string;
  sha256: string;
  format: typeof DIGIEXAM_SOURCE_FORMAT;
};

export type SirConvertArtifactManifestSourceBinding = {
  source_ir_schema_version: DigiExamIntermediateExamSchemaVersion;
  source_ir_sha256: string;
  effective_exam_schema_version: string;
  effective_exam_sha256: string;
};

export type SirConvertArtifactManifestReadiness = {
  artifact_key: typeof DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT;
  exportable_targets: string[];
  review_required: boolean;
};

export type SirConvertArtifactManifest = {
  schema_version: DigiExamMigrationBundleSchemaVersion;
  job_id: string;
  source: SirConvertArtifactManifestSource;
  bundle_status: SirConvertBundleStatus;
  artifacts: SirConvertArtifactEntry[];
  manual_follow_up: {
    required: boolean;
    artifact_key: string;
    count: number;
  } | null;
  warnings: {
    artifact_key: string;
    count: number;
  } | null;
  readiness: SirConvertArtifactManifestReadiness;
  source_binding: SirConvertArtifactManifestSourceBinding;
};

export type SirConvertArtifactBlob = {
  blob: Blob;
  contentType: string | null;
  filename: string | null;
  artifactKey: string;
};

export type SirConvertUserFileSaveMetadata = {
  sir_convert_job_id: string;
  artifact_key: string;
  source_filename: string;
  saved_display_filename: string;
  content_type: string;
  size_bytes: number | null;
  sha256: string | null;
  bundle_schema_version: DigiExamMigrationBundleSchemaVersion;
  correlation_id: string;
  saved_at: string;
};
