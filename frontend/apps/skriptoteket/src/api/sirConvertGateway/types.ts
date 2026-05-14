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

export type DigiExamMigrationTarget = "examnet_pdf" | "qti_package";

export type SirConvertJobStatus =
  | "submitted"
  | "queued"
  | "processing"
  | "succeeded"
  | "failed"
  | "canceled"
  | "cancelled";

export type SirConvertBundleStatus = "complete" | "partial" | "blocked";

export type SirConvertArtifactAvailability =
  | "available"
  | "blocked"
  | "failed"
  | "not_requested"
  | "not_implemented"
  | "not_supported_by_examnet";

export type SirConvertDigiExamJobSpec = {
  api_version: "v2";
  source: {
    kind: "upload";
    filename: string;
    format: "digiexam_dxe";
  };
  conversion: {
    output_format: "examnet_migration_bundle";
    targets: DigiExamMigrationTarget[];
    artifact_language: string;
    reference_docx_filename: null;
  };
  digiexam_migration_options: {
    graded_result_pdf_filename?: string;
    parity_pdf_filename?: string;
    result_pdf_usage: "correct_machine_marked_answers_only";
    manual_follow_up_policy: "emit_item_addressable_report";
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
  artifactLanguage?: string;
  waitSeconds?: number;
  correlationId?: string | null;
  sourceLabel?: string | null;
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
    target_availability: Record<string, SirConvertArtifactAvailability>;
    manual_follow_up_required: boolean;
    warning_count: number;
    artifact_count: number;
  };
};

export type SirConvertArtifactEntry = {
  artifact_key: string;
  filename: string;
  content_type: string;
  availability: SirConvertArtifactAvailability;
  size_bytes: number | null;
  sha256: string | null;
  download_path?: string;
  blocker_code?: string;
};

export type SirConvertArtifactManifest = {
  schema_version: "digiexam_migration_bundle_v1";
  job_id: string;
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
  bundle_schema_version: "digiexam_migration_bundle_v1";
  correlation_id: string;
  saved_at: string;
};
