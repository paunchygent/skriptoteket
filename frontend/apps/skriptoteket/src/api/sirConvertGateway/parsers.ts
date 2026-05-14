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
import type {
  SirConvertArtifactAvailability,
  SirConvertArtifactEntry,
  SirConvertArtifactManifest,
  SirConvertBundleStatus,
  SirConvertJob,
  SirConvertJobStatus,
  SirConvertTerminalResult,
} from "./types";

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

function readStatus(value: unknown): SirConvertJobStatus {
  const status = readString(value, "status");
  if (
    status === "submitted" ||
    status === "queued" ||
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
  if (status === "complete" || status === "partial" || status === "blocked") return status;
  throw new Error(`Unknown Sir Convert bundle status '${status}'.`);
}

function readArtifactAvailability(value: unknown): SirConvertArtifactAvailability {
  const availability = readString(value, "availability");
  if (
    availability === "available" ||
    availability === "blocked" ||
    availability === "failed" ||
    availability === "not_requested" ||
    availability === "not_implemented" ||
    availability === "not_supported_by_examnet"
  ) {
    return availability;
  }
  throw new Error(`Unknown Sir Convert artifact availability '${availability}'.`);
}

export function parseJob(payload: unknown): SirConvertJob {
  const root = readRecord(payload, "payload");
  const job = readRecord(root.job, "job");
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
  const blockerCode =
    typeof entry.blocker_code === "string" && entry.blocker_code.length > 0
      ? entry.blocker_code
      : undefined;
  if (
    (availability === "blocked" || availability === "failed" || availability === "not_implemented") &&
    !blockerCode
  ) {
    throw new Error(
      `Sir Convert artifact '${artifactKey}' requires blocker_code for '${availability}' availability.`,
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
    ...(blockerCode ? { blocker_code: blockerCode } : {}),
  };
}

export function parseArtifactManifest(payload: unknown): SirConvertArtifactManifest {
  const root = readRecord(payload, "manifest");
  if (root.schema_version !== "digiexam_migration_bundle_v1") {
    throw new Error("Sir Convert artifact manifest has an unknown schema version.");
  }
  if (!Array.isArray(root.artifacts)) {
    throw new Error("Sir Convert artifact manifest is missing artifacts.");
  }
  const manualFollowUp = root.manual_follow_up;
  const warnings = root.warnings;
  return {
    schema_version: "digiexam_migration_bundle_v1",
    job_id: readString(root.job_id, "job_id"),
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
