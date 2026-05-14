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
import type {
  DigiExamMigrationSubmitParams,
  DigiExamMigrationTarget,
  SirConvertDigiExamJobSpec,
} from "./types";

export const DEFAULT_DIGIEXAM_MIGRATION_TARGETS: DigiExamMigrationTarget[] = [
  "examnet_pdf",
  "qti_package",
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
    result_pdf_usage: "correct_machine_marked_answers_only",
    manual_follow_up_policy: "emit_item_addressable_report",
  };
  if (params.gradedResultPdf) {
    options.graded_result_pdf_filename = params.gradedResultPdf.name;
  }
  if (params.parityPdf) {
    options.parity_pdf_filename = params.parityPdf.name;
  }

  return {
    api_version: "v2",
    source: {
      kind: "upload",
      filename: params.file.name,
      format: "digiexam_dxe",
    },
    conversion: {
      output_format: "examnet_migration_bundle",
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
