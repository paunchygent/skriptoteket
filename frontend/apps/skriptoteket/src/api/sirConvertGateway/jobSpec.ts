/**
 * Sir Convert DigiExam migration job-spec builder.
 *
 * Purpose:
 *   Build the governed `digiexam_dxe -> examnet_migration_bundle` JobSpec
 *   without parsing uploaded exam content or applying conversion policy.
 *
 * Relationships:
 *   - `requestContext.ts` hashes this canonical shape for idempotency.
 *   - `client.ts` serializes the shape into multipart `job_spec`.
 */

import { SirConvertGatewayError } from "./errors";
import {
  DIGIEXAM_INGESTION_OVERLAY_FILENAME,
  DIGIEXAM_INGESTION_OVERLAY_POLICY_APPLY_TEACHER,
  DIGIEXAM_MANUAL_FOLLOW_UP_POLICY_ITEM_ADDRESSABLE,
  DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
  DIGIEXAM_MIGRATION_OUTPUT_FORMAT,
  DIGIEXAM_MIGRATION_TARGETS,
  DIGIEXAM_REMOTE_PROVIDER_POLICY_FORBIDDEN,
  DIGIEXAM_RESULT_PDF_USAGE_CORRECT_MACHINE_MARKED,
  DIGIEXAM_SOURCE_FORMAT,
} from "./contractValues";
import type {
  DigiExamMigrationSubmitParams,
  DigiExamMigrationTarget,
  SirConvertDigiExamJobSpec,
} from "./types";

export const DEFAULT_DIGIEXAM_MIGRATION_TARGETS: DigiExamMigrationTarget[] = [
  ...DIGIEXAM_MIGRATION_TARGETS,
];

function validatePrimaryFile(file: File): void {
  if (!file.name.toLowerCase().endsWith(".dxe")) {
    throw new SirConvertGatewayError({
      status: 0,
      code: "INVALID_DIGIEXAM_SOURCE",
      message: "DigiExam migration requires a .dxe source file.",
    });
  }
}

export function buildDigiExamMigrationJobSpec(
  params: DigiExamMigrationSubmitParams,
): SirConvertDigiExamJobSpec {
  validatePrimaryFile(params.file);

  const options: SirConvertDigiExamJobSpec["digiexam_migration_options"] = {
    completion_mode: params.completionMode ?? DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
    remote_provider_policy: DIGIEXAM_REMOTE_PROVIDER_POLICY_FORBIDDEN,
    result_pdf_usage: DIGIEXAM_RESULT_PDF_USAGE_CORRECT_MACHINE_MARKED,
    manual_follow_up_policy: DIGIEXAM_MANUAL_FOLLOW_UP_POLICY_ITEM_ADDRESSABLE,
  };
  if (params.gradedResultPdf) {
    options.graded_result_pdf_filename = params.gradedResultPdf.name;
  }
  if (params.parityPdf) {
    options.parity_pdf_filename = params.parityPdf.name;
  }
  if (params.ingestionOverlay) {
    options.ingestion_overlay_filename = DIGIEXAM_INGESTION_OVERLAY_FILENAME;
    options.ingestion_overlay_policy = DIGIEXAM_INGESTION_OVERLAY_POLICY_APPLY_TEACHER;
  }

  return {
    api_version: "v2",
    source: {
      kind: "upload",
      filename: params.file.name,
      format: DIGIEXAM_SOURCE_FORMAT,
    },
    conversion: {
      output_format: DIGIEXAM_MIGRATION_OUTPUT_FORMAT,
      targets: params.targets ?? DEFAULT_DIGIEXAM_MIGRATION_TARGETS,
      artifact_language: params.artifactLanguage?.trim() || "sv",
      reference_docx_filename: null,
    },
    digiexam_migration_options: options,
    retention: {
      pin: false,
    },
  };
}
