/**
 * Exam Converter file-action filename authority tests.
 *
 * Domain purpose:
 *   Prove corrected file actions keep teacher-facing target filenames while
 *   fetching bytes through replay-scoped Sir Convert artifact references.
 *
 * Relationships:
 *   - Exercises `useExamConverterFileActions`.
 *   - Complements corrected file-action view tests.
 */

import { describe, expect, it, vi } from "vitest";

import { useExamConverterFileActions } from "./useExamConverterFileActions";
import type { ExamConverterReviewFile } from "./digiexamIrReviewParser";
import type {
  DigiExamAnswerKeyReviewReplayArtifactReference,
  SirConvertArtifactBlob,
  SirConvertSavedUserFile,
} from "../../../api/sirConvertGateway";

function replayReference(): DigiExamAnswerKeyReviewReplayArtifactReference {
  return {
    artifact_key: "correction_replay_qti_package",
    artifact_set_id: "artifact-set-qti",
    content_sha256: "sha256:replay-qti",
    correction_payload_digest: "sha256:correction-payload",
    created_at: "2026-06-29T12:00:00Z",
    job_id: "sir-replay-job",
    replay_profile_version: "correction-replay-v1",
    request_id: "correction-session-replay-session-001-v2",
    schema_version: "correction_replay_artifact_reference_v1",
    source_binding_digest: "sha256:source-binding",
    source_state_sha256: "sha256:source-state",
    target: "qti_package",
    target_set_digest: "sha256:target-set",
  };
}

function replayFile(): ExamConverterReviewFile {
  const reference = replayReference();
  return {
    artifactActionReference: {
      artifactKey: reference.artifact_key,
      artifactSetId: reference.artifact_set_id,
      authority: "replay_result",
      contentSha256: reference.content_sha256,
      jobId: reference.job_id,
      replayArtifactReference: reference,
    },
    artifactKey: "qti_package",
    availability: "available",
    contentType: "application/zip",
    exportEnabled: true,
    filename: "Ekologiprov_QTI.zip",
    kindLabel: "QTI-format",
    reasonCode: "ready",
    readiness: "ready",
    sha256: "sha256:qti",
    sizeBytes: 4,
    sizeLabel: "4 B",
    statusLabel: "Kan hämtas",
    unavailableCode: null,
  };
}

function originalFile(): ExamConverterReviewFile {
  return {
    ...replayFile(),
    artifactActionReference: {
      artifactKey: "qti_package",
      authority: "original_job",
    },
    artifactKey: "qti_package",
    filename: "First-pass_QTI.zip",
    sha256: "sha256:first-pass-qti",
  };
}

function replayBlob(): SirConvertArtifactBlob {
  return {
    artifactKey: "correction_replay_qti_package",
    blob: new Blob(["qti"], { type: "application/zip" }),
    contentType: "application/zip",
    filename: "correction_replay_qti_package.zip",
  };
}

describe("useExamConverterFileActions", () => {
  it("downloads corrected target bytes from the local named-artifact route", async () => {
    const triggerDownload = vi.fn();
    const downloadDigiExamMigrationArtifact = vi.fn().mockResolvedValue(replayBlob());
    const downloadDigiExamMigrationCorrectionReplayArtifact = vi.fn().mockResolvedValue(replayBlob());
    const { downloadFile } = useExamConverterFileActions({
      client: {
        downloadDigiExamMigrationArtifact,
        downloadDigiExamMigrationCorrectionReplayArtifact,
        saveLocalExamConversionArtifact: vi.fn(),
      },
      triggerDownload,
    });

    await downloadFile({
      correlationId: "corr-filename",
      file: replayFile(),
      jobId: "job-filename",
    });

    expect(downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "correction_replay_qti_package",
      correlationId: "corr-filename",
      jobId: "job-filename",
    });
    expect(downloadDigiExamMigrationCorrectionReplayArtifact).not.toHaveBeenCalled();
    expect(triggerDownload).toHaveBeenCalledWith(
      expect.objectContaining({
        artifactKey: "correction_replay_qti_package",
        filename: "Ekologiprov_QTI.zip",
      }),
      "Ekologiprov_QTI.zip",
    );
  });

  it("keeps first-pass original artifacts on the named-artifact route", async () => {
    const downloadDigiExamMigrationArtifact = vi.fn().mockResolvedValue({
      ...replayBlob(),
      artifactKey: "qti_package",
    });
    const downloadDigiExamMigrationCorrectionReplayArtifact = vi.fn();
    const { downloadFile } = useExamConverterFileActions({
      client: {
        downloadDigiExamMigrationArtifact,
        downloadDigiExamMigrationCorrectionReplayArtifact,
        saveLocalExamConversionArtifact: vi.fn(),
      },
      triggerDownload: vi.fn(),
    });

    await downloadFile({
      correlationId: "corr-first-pass",
      file: originalFile(),
      jobId: "job-first-pass",
    });

    expect(downloadDigiExamMigrationArtifact).toHaveBeenCalledWith({
      artifactKey: "qti_package",
      correlationId: "corr-first-pass",
      jobId: "job-first-pass",
    });
    expect(downloadDigiExamMigrationCorrectionReplayArtifact).not.toHaveBeenCalled();
  });

  it("saves corrected local bytes with the teacher-facing target filename", async () => {
    const saved: SirConvertSavedUserFile = {
      source_artifact_id: "documents.conversion_hub:job-filename:qti_package",
      vault_artifact: {
        bytes: 4,
        created_at: "2026-05-20T00:00:00Z",
        file_id: "vault-qti",
        name: "Ekologiprov_QTI.zip",
      },
    };
    const saveLocalExamConversionArtifact = vi.fn().mockResolvedValue(saved);
    const downloadDigiExamMigrationArtifact = vi.fn().mockResolvedValue(replayBlob());
    const downloadDigiExamMigrationCorrectionReplayArtifact = vi.fn();
    const { saveFile } = useExamConverterFileActions({
      client: {
        downloadDigiExamMigrationArtifact,
        downloadDigiExamMigrationCorrectionReplayArtifact,
        saveLocalExamConversionArtifact,
      },
    });

    await saveFile({
      correlationId: "corr-filename",
      file: replayFile(),
      jobId: "job-filename",
    });

    expect(downloadDigiExamMigrationArtifact).not.toHaveBeenCalled();
    expect(downloadDigiExamMigrationCorrectionReplayArtifact).not.toHaveBeenCalled();
    expect(saveLocalExamConversionArtifact).toHaveBeenCalledWith({
      artifactKey: "correction_replay_qti_package",
      jobId: "job-filename",
    });
  });
});
