/**
 * Sir Convert user-file metadata mapping.
 *
 * Purpose:
 *   Preserve Sir Convert artifact-bundle provenance when a downloaded named
 *   artifact is handed to Skriptoteket user-file persistence.
 *
 * Relationships:
 *   - `types.ts` defines artifact entries and save metadata.
 *   - Later UI/user-file flows consume this mapper after named downloads.
 */

import type { SirConvertArtifactEntry, SirConvertUserFileSaveMetadata } from "./types";

const SHA256_PREFIX = "sha256:";
const SHA256_HEX_PATTERN = /^[a-f0-9]{64}$/i;

function normalizeSha256(value: string | null): string | null {
  if (value === null) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  const candidate = trimmed.toLowerCase().startsWith(SHA256_PREFIX)
    ? trimmed.slice(SHA256_PREFIX.length)
    : trimmed;
  if (SHA256_HEX_PATTERN.test(candidate)) {
    return candidate.toLowerCase();
  }
  throw new Error("Sir Convert artifact checksum has an unsupported SHA-256 format.");
}

export function buildSirConvertUserFileSaveMetadata(params: {
  jobId: string;
  artifact: SirConvertArtifactEntry;
  savedDisplayFilename?: string | null;
  correlationId: string;
  savedAt: Date;
}): SirConvertUserFileSaveMetadata {
  return {
    sir_convert_job_id: params.jobId,
    artifact_key: params.artifact.artifact_key,
    source_filename: params.artifact.filename,
    saved_display_filename: params.savedDisplayFilename?.trim() || params.artifact.filename,
    content_type: params.artifact.content_type,
    size_bytes: params.artifact.size_bytes,
    sha256: normalizeSha256(params.artifact.sha256),
    bundle_schema_version: "digiexam_migration_bundle_v1",
    correlation_id: params.correlationId,
    saved_at: params.savedAt.toISOString(),
  };
}

export function isSirConvertArtifactAvailable(entry: SirConvertArtifactEntry): boolean {
  return entry.availability === "available";
}
