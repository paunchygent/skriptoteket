/**
 * Sir Convert user-file save client.
 *
 * Purpose:
 *   Persist authenticated Sir Convert named artifacts through Skriptoteket's
 *   owner-scoped user-file boundary after Gateway-mediated artifact download.
 *
 * Relationships:
 *   - `client.ts` downloads the named artifact through HuleEdu Gateway.
 *   - `saveMetadata.ts` builds provenance metadata for the save request.
 */

import { apiPost } from "../client";
import { buildSirConvertUserFileSaveMetadata } from "./saveMetadata";
import type {
  SirConvertArtifactBlob,
  SirConvertArtifactEntry,
  SirConvertUserFileSaveMetadata,
} from "./types";

export type SirConvertSavedVaultArtifact = {
  file_id: string;
  name: string;
  bytes: number;
  created_at: string;
};

export type SirConvertSavedUserFile = {
  vault_artifact: SirConvertSavedVaultArtifact;
  source_artifact_id: string;
};

const SAVE_ENDPOINT = "/api/v1/apps/documents.conversion_hub/exam-converter/artifacts/save";

export async function saveDigiExamMigrationArtifactToUserFiles(params: {
  jobId: string;
  artifact: SirConvertArtifactEntry;
  artifactBlob: SirConvertArtifactBlob;
  correlationId: string;
  savedAt?: Date;
}): Promise<SirConvertSavedUserFile> {
  const filename = params.artifactBlob.filename ?? params.artifact.filename;
  const metadata = buildSirConvertUserFileSaveMetadata({
    jobId: params.jobId,
    artifact: params.artifact,
    savedDisplayFilename: filename,
    correlationId: params.correlationId,
    savedAt: params.savedAt ?? new Date(),
  });
  const form = new FormData();
  form.append("metadata_json", JSON.stringify(normalizeMetadata(metadata)));
  form.append("artifact", params.artifactBlob.blob, filename);
  return await apiPost<SirConvertSavedUserFile>(SAVE_ENDPOINT, form);
}

function normalizeMetadata(
  metadata: SirConvertUserFileSaveMetadata,
): SirConvertUserFileSaveMetadata {
  return {
    ...metadata,
    content_type: metadata.content_type || "application/octet-stream",
  };
}
