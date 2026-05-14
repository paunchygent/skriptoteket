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
    sha256: params.artifact.sha256,
    bundle_schema_version: "digiexam_migration_bundle_v1",
    correlation_id: params.correlationId,
    saved_at: params.savedAt.toISOString(),
  };
}

export function isSirConvertArtifactAvailable(entry: SirConvertArtifactEntry): boolean {
  return entry.availability === "available";
}
