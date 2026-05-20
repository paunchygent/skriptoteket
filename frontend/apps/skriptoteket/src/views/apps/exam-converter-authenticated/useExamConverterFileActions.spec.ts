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
  SirConvertArtifactBlob,
  SirConvertSavedUserFile,
} from "../../../api/sirConvertGateway";

function replayFile(): ExamConverterReviewFile {
  return {
    artifactActionReference: {
      artifactKey: "correction_replay_qti_package",
      authority: "replay_result",
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

function replayBlob(): SirConvertArtifactBlob {
  return {
    artifactKey: "correction_replay_qti_package",
    blob: new Blob(["qti"], { type: "application/zip" }),
    contentType: "application/zip",
    filename: "correction_replay_qti_package.zip",
  };
}

describe("useExamConverterFileActions", () => {
  it("downloads replay bytes with the teacher-facing target filename", async () => {
    const triggerDownload = vi.fn();
    const downloadDigiExamMigrationArtifact = vi.fn().mockResolvedValue(replayBlob());
    const { downloadFile } = useExamConverterFileActions({
      client: {
        downloadDigiExamMigrationArtifact,
        saveDigiExamMigrationArtifactToUserFiles: vi.fn(),
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
    expect(triggerDownload).toHaveBeenCalledWith(
      expect.objectContaining({
        artifactKey: "correction_replay_qti_package",
        filename: "Ekologiprov_QTI.zip",
      }),
      "Ekologiprov_QTI.zip",
    );
  });

  it("saves replay bytes with the teacher-facing target filename", async () => {
    const saved: SirConvertSavedUserFile = {
      source_artifact_id: "documents.conversion_hub:job-filename:qti_package",
      vault_artifact: {
        bytes: 4,
        created_at: "2026-05-20T00:00:00Z",
        file_id: "vault-qti",
        name: "Ekologiprov_QTI.zip",
      },
    };
    const saveDigiExamMigrationArtifactToUserFiles = vi.fn().mockResolvedValue(saved);
    const { saveFile } = useExamConverterFileActions({
      client: {
        downloadDigiExamMigrationArtifact: vi.fn().mockResolvedValue(replayBlob()),
        saveDigiExamMigrationArtifactToUserFiles,
      },
    });

    await saveFile({
      correlationId: "corr-filename",
      file: replayFile(),
      jobId: "job-filename",
    });

    expect(saveDigiExamMigrationArtifactToUserFiles).toHaveBeenCalledWith(
      expect.objectContaining({
        artifact: expect.objectContaining({
          artifact_key: "correction_replay_qti_package",
          filename: "Ekologiprov_QTI.zip",
        }),
        artifactBlob: expect.objectContaining({
          artifactKey: "correction_replay_qti_package",
          filename: "Ekologiprov_QTI.zip",
        }),
      }),
    );
  });
});
