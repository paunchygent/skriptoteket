/**
 * Sir Convert Gateway response parsers.
 *
 * Purpose:
 *   Validate Sir Convert Gateway JSON and artifact responses at the frontend
 *   boundary so contract drift is explicit instead of silently tolerated.
 *
 * Relationships:
 *   - `client.ts` delegates all response decoding here.
 *   - `errors.ts` preserves upstream error codes and correlation IDs.
 */

import { SirConvertGatewayError } from "./errors";
import {
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  DIGIEXAM_SOURCE_FORMAT,
  DIGIEXAM_TARGET_READINESS_VALUES,
  SIR_CONVERT_ARTIFACT_AVAILABILITIES,
  SIR_CONVERT_ARTIFACT_FAILED,
  SIR_CONVERT_ARTIFACT_UNAVAILABLE,
  SIR_CONVERT_BUNDLE_STATUSES,
} from "./contractValues";
import type {
  SirConvertArtifactAvailability,
  SirConvertArtifactEntry,
  SirConvertArtifactManifest,
  SirConvertBundleStatus,
  SirConvertArtifactManifestReadiness,
  SirConvertArtifactManifestSource,
  SirConvertArtifactManifestSourceBinding,
  DigiExamTargetReadinessReport,
  DigiExamTargetReadiness,
  SirConvertJob,
  SirConvertJobStatus,
  SirConvertTerminalResult,
} from "./types";
import {
  DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
  TARGET_READINESS_REPORT_SCHEMA_VERSION,
} from "./schemaVersions";

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`Sir Convert response field '${fieldName}' is not an object.`);
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Sir Convert response field '${fieldName}' is missing.`);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`Sir Convert response field '${fieldName}' is not a string.`);
}

function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Sir Convert response field '${fieldName}' is not a number.`);
}

function readNullableNumber(value: unknown, fieldName: string): number | null {
  if (value === null || value === undefined) return null;
  return readNumber(value, fieldName);
}

function readBoolean(value: unknown, fieldName: string): boolean {
  if (typeof value === "boolean") return value;
  throw new Error(`Sir Convert response field '${fieldName}' is not a boolean.`);
}

function readStringArray(value: unknown, fieldName: string): string[] {
  if (!Array.isArray(value)) {
    throw new Error(`Sir Convert response field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readString(entry, `${fieldName}[${index}]`));
}

function readStatus(value: unknown): SirConvertJobStatus {
  const status = readString(value, "status");
  if (
    status === "submitted" ||
    status === "queued" ||
    status === "running" ||
    status === "processing" ||
    status === "succeeded" ||
    status === "failed" ||
    status === "canceled" ||
    status === "cancelled"
  ) {
    return status;
  }
  throw new Error(`Unknown Sir Convert job status '${status}'.`);
}

function readBundleStatus(value: unknown): SirConvertBundleStatus {
  const status = readString(value, "bundle_status");
  if (SIR_CONVERT_BUNDLE_STATUSES.includes(status as SirConvertBundleStatus)) {
    return status as SirConvertBundleStatus;
  }
  throw new Error(`Unknown Sir Convert bundle status '${status}'.`);
}

function readArtifactAvailability(value: unknown): SirConvertArtifactAvailability {
  const availability = readString(value, "availability");
  if (SIR_CONVERT_ARTIFACT_AVAILABILITIES.includes(availability as SirConvertArtifactAvailability)) {
    return availability as SirConvertArtifactAvailability;
  }
  throw new Error(`Unknown Sir Convert artifact availability '${availability}'.`);
}

function readTargetReadiness(value: unknown, fieldName: string): DigiExamTargetReadiness {
  const readiness = readString(value, fieldName);
  if (DIGIEXAM_TARGET_READINESS_VALUES.includes(readiness as DigiExamTargetReadiness)) {
    return readiness as DigiExamTargetReadiness;
  }
  throw new Error(`Unknown Sir Convert target readiness '${readiness}'.`);
}

export function parseJob(payload: unknown): SirConvertJob {
  const root = readRecord(payload, "payload");
  const job = isRecord(root.job)
    ? root.job
    : {
        job_id: root.job_id,
        status: root.status,
      };
  return {
    jobId: readString(job.job_id, "job.job_id"),
    status: readStatus(job.status),
  };
}

function parseTargetAvailability(value: unknown): Record<string, SirConvertArtifactAvailability> {
  const availability = readRecord(value, "conversion_metadata.target_availability");
  const result: Record<string, SirConvertArtifactAvailability> = {};
  for (const [key, item] of Object.entries(availability)) {
    result[key] = readArtifactAvailability(item);
  }
  return result;
}

export function parseTerminalResult(payload: unknown): SirConvertTerminalResult {
  const root = readRecord(payload, "payload");
  const result = readRecord(root.result, "result");
  const artifact = readRecord(result.artifact, "result.artifact");
  const metadata = readRecord(result.conversion_metadata, "result.conversion_metadata");
  return {
    job: parseJob(payload),
    artifact: {
      filename: readString(artifact.filename, "result.artifact.filename"),
      content_type: readString(artifact.content_type, "result.artifact.content_type"),
      sha256: readNullableString(artifact.sha256, "result.artifact.sha256"),
      size_bytes: readNullableNumber(artifact.size_bytes, "result.artifact.size_bytes"),
    },
    conversion_metadata: {
      route_key: readString(metadata.route_key, "conversion_metadata.route_key"),
      bundle_schema_version: readString(
        metadata.bundle_schema_version,
        "conversion_metadata.bundle_schema_version",
      ),
      bundle_status: readBundleStatus(metadata.bundle_status),
      source_sha256: readNullableString(metadata.source_sha256, "source_sha256"),
      target_readiness_report_artifact_key: (() => {
        const artifactKey = readNullableString(
          metadata.target_readiness_report_artifact_key,
          "target_readiness_report_artifact_key",
        );
        if (artifactKey !== null && artifactKey !== DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
          throw new Error("Sir Convert terminal result points to an unknown readiness artifact.");
        }
        return artifactKey;
      })(),
      target_availability: parseTargetAvailability(metadata.target_availability),
      manual_follow_up_required: readBoolean(
        metadata.manual_follow_up_required,
        "manual_follow_up_required",
      ),
      warning_count: readNumber(metadata.warning_count, "warning_count"),
      artifact_count: readNumber(metadata.artifact_count, "artifact_count"),
    },
  };
}

function parseArtifactEntry(payload: unknown): SirConvertArtifactEntry {
  const entry = readRecord(payload, "artifact");
  const artifactKey = readString(entry.artifact_key, "artifact_key");
  const availability = readArtifactAvailability(entry.availability);
  const downloadPath =
    typeof entry.download_path === "string" && entry.download_path.length > 0
      ? entry.download_path
      : undefined;
  const unavailableCode =
    typeof entry.unavailable_code === "string" && entry.unavailable_code.length > 0
      ? entry.unavailable_code
      : undefined;
  const dependsOn =
    typeof entry.depends_on === "string" && entry.depends_on.length > 0
      ? entry.depends_on
      : undefined;
  if (
    (availability === SIR_CONVERT_ARTIFACT_UNAVAILABLE ||
      availability === SIR_CONVERT_ARTIFACT_FAILED) &&
    !unavailableCode
  ) {
    throw new Error(
      `Sir Convert artifact '${artifactKey}' requires unavailable_code for '${availability}' availability.`,
    );
  }
  return {
    artifact_key: artifactKey,
    filename: readString(entry.filename, "filename"),
    content_type: readString(entry.content_type, "content_type"),
    availability,
    size_bytes: readNullableNumber(entry.size_bytes, "size_bytes"),
    sha256: readNullableString(entry.sha256, "sha256"),
    ...(downloadPath ? { download_path: downloadPath } : {}),
    ...(unavailableCode ? { unavailable_code: unavailableCode } : {}),
    ...(dependsOn ? { depends_on: dependsOn } : {}),
  };
}

function parseManifestSource(payload: unknown): SirConvertArtifactManifestSource {
  const source = readRecord(payload, "source");
  const format = readString(source.format, "source.format");
  if (format !== DIGIEXAM_SOURCE_FORMAT) {
    throw new Error(`Unknown Sir Convert DigiExam source format '${format}'.`);
  }
  return {
    filename: readString(source.filename, "source.filename"),
    sha256: readString(source.sha256, "source.sha256"),
    format,
  };
}

function parseManifestReadiness(payload: unknown): SirConvertArtifactManifestReadiness {
  const readiness = readRecord(payload, "readiness");
  const artifactKey = readString(readiness.artifact_key, "readiness.artifact_key");
  if (artifactKey !== DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT) {
    throw new Error("Sir Convert readiness summary does not point to target_readiness_report.");
  }
  return {
    artifact_key: artifactKey,
    exportable_targets: readStringArray(readiness.exportable_targets, "readiness.exportable_targets"),
    review_required: readBoolean(readiness.review_required, "readiness.review_required"),
  };
}

function parseManifestSourceBinding(payload: unknown): SirConvertArtifactManifestSourceBinding {
  const sourceBinding = readRecord(payload, "source_binding");
  return {
    source_ir_schema_version: readString(
      sourceBinding.source_ir_schema_version,
      "source_binding.source_ir_schema_version",
    ) as SirConvertArtifactManifestSourceBinding["source_ir_schema_version"],
    source_ir_sha256: readString(sourceBinding.source_ir_sha256, "source_binding.source_ir_sha256"),
    effective_exam_schema_version: readString(
      sourceBinding.effective_exam_schema_version,
      "source_binding.effective_exam_schema_version",
    ),
    effective_exam_sha256: readString(
      sourceBinding.effective_exam_sha256,
      "source_binding.effective_exam_sha256",
    ),
  };
}

export function parseArtifactManifest(payload: unknown): SirConvertArtifactManifest {
  const root = readRecord(payload, "manifest");
  if (root.schema_version !== DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION) {
    throw new Error("Sir Convert artifact manifest has an unknown schema version.");
  }
  if (!Array.isArray(root.artifacts)) {
    throw new Error("Sir Convert artifact manifest is missing artifacts.");
  }
  const manualFollowUp = root.manual_follow_up;
  const warnings = root.warnings;
  return {
    schema_version: DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
    job_id: readString(root.job_id, "job_id"),
    source: parseManifestSource(root.source),
    bundle_status: readBundleStatus(root.bundle_status),
    artifacts: root.artifacts.map((entry) => parseArtifactEntry(entry)),
    manual_follow_up: isRecord(manualFollowUp)
      ? {
          required: readBoolean(manualFollowUp.required, "manual_follow_up.required"),
          artifact_key: readString(manualFollowUp.artifact_key, "manual_follow_up.artifact_key"),
          count: readNumber(manualFollowUp.count, "manual_follow_up.count"),
        }
      : null,
    warnings: isRecord(warnings)
      ? {
          artifact_key: readString(warnings.artifact_key, "warnings.artifact_key"),
          count: readNumber(warnings.count, "warnings.count"),
        }
      : null,
    readiness: parseManifestReadiness(root.readiness),
    source_binding: parseManifestSourceBinding(root.source_binding),
  };
}

export function parseTargetReadinessReport(payload: unknown): DigiExamTargetReadinessReport {
  const root = readRecord(payload, DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT);
  if (root.schema_version !== TARGET_READINESS_REPORT_SCHEMA_VERSION) {
    throw new Error("Sir Convert target readiness report has an unknown schema version.");
  }
  if (!Array.isArray(root.targets)) {
    throw new Error("Sir Convert target readiness report is missing targets.");
  }
  return {
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    job_id: readString(root.job_id, "job_id"),
    source_ir_sha256: readString(root.source_ir_sha256, "source_ir_sha256"),
    effective_exam_sha256: readString(root.effective_exam_sha256, "effective_exam_sha256"),
    targets: root.targets.map((entry, index) => {
      const row = readRecord(entry, `targets[${index}]`);
      return {
        target: readString(row.target, `targets[${index}].target`),
        readiness: readTargetReadiness(row.readiness, `targets[${index}].readiness`),
        export_enabled: readBoolean(row.export_enabled, `targets[${index}].export_enabled`),
        artifact_key: readNullableString(row.artifact_key, `targets[${index}].artifact_key`),
        reason_code: readString(row.reason_code, `targets[${index}].reason_code`),
        teacher_action: readString(row.teacher_action, `targets[${index}].teacher_action`),
        retryable: readBoolean(row.retryable, `targets[${index}].retryable`),
        message_key: readString(row.message_key, `targets[${index}].message_key`),
        item_id: readNullableString(row.item_id, `targets[${index}].item_id`),
        sequence:
          row.sequence === null || row.sequence === undefined
            ? null
            : readNumber(row.sequence, `targets[${index}].sequence`),
        source_item_fingerprint: readNullableString(
          row.source_item_fingerprint,
          `targets[${index}].source_item_fingerprint`,
        ),
      };
    }),
  };
}

export async function toGatewayError(response: Response): Promise<SirConvertGatewayError> {
  const fallbackMessage = response.statusText || `Sir Convert request failed (${response.status})`;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as unknown;
    if (isRecord(payload) && isRecord(payload.error)) {
      return new SirConvertGatewayError({
        status: response.status,
        code: typeof payload.error.code === "string" ? payload.error.code : "SIR_CONVERT_ERROR",
        message:
          typeof payload.error.message === "string" ? payload.error.message : fallbackMessage,
        details: payload.error.details ?? null,
        correlationId: typeof payload.correlation_id === "string" ? payload.correlation_id : null,
      });
    }
  }
  return new SirConvertGatewayError({
    status: response.status,
    code: "HTTP_ERROR",
    message: fallbackMessage,
  });
}

export async function readJsonOrThrow<T>(
  response: Response,
  parser: (payload: unknown) => T,
): Promise<T> {
  if (!response.ok) throw await toGatewayError(response);
  try {
    return parser(await response.json());
  } catch (error: unknown) {
    throw new SirConvertGatewayError({
      status: response.status,
      code: "SIR_CONVERT_CONTRACT_DRIFT",
      message: error instanceof Error ? error.message : "Sir Convert response contract drift.",
    });
  }
}

export function parseContentDispositionFilename(headerValue: string | null): string | null {
  if (!headerValue) return null;
  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const quotedMatch = headerValue.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) return quotedMatch[1];
  const plainMatch = headerValue.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() ?? null;
}
