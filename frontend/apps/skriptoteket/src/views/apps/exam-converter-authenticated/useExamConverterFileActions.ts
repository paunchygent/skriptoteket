/**
 * Exam Converter file action state.
 *
 * Domain purpose:
 *   Download and save authenticated Exam Converter target files after the
 *   teacher has resolved export-blocking authoring state and replay returned
 *   artifact references authorized for file actions.
 *
 * Relationships:
 *   - Uses the HuleEdu Gateway Sir Convert artifact client for named downloads.
 *   - Uses Skriptoteket's owner-scoped user-file save client for Vault saves.
 *   - Keeps action state local to the current conversion job.
 */

import { ref } from "vue";

import {
  downloadDigiExamMigrationArtifact,
  downloadDigiExamMigrationCorrectionReplayArtifact,
  saveDigiExamMigrationArtifactToUserFiles,
} from "../../../api/sirConvertGateway";
import type {
  SirConvertArtifactBlob,
  SirConvertArtifactEntry,
  SirConvertSavedUserFile,
} from "../../../api/sirConvertGateway";
import type { ExamConverterReviewFile } from "./digiexamIrReviewParser";

export type ExamConverterFileActionStatus = "idle" | "running" | "done" | "failed";

export type ExamConverterFileActionState = {
  download: ExamConverterFileActionStatus;
  save: ExamConverterFileActionStatus;
  savedFilename: string | null;
};

export type ExamConverterFileActionStates = Record<string, ExamConverterFileActionState>;

type FileActionClient = {
  downloadDigiExamMigrationArtifact: typeof downloadDigiExamMigrationArtifact;
  downloadDigiExamMigrationCorrectionReplayArtifact:
    typeof downloadDigiExamMigrationCorrectionReplayArtifact;
  saveDigiExamMigrationArtifactToUserFiles: typeof saveDigiExamMigrationArtifactToUserFiles;
};

type TriggerDownload = (artifact: SirConvertArtifactBlob, fallbackFilename: string) => void;

export type ExamConverterFileActionOptions = {
  client?: FileActionClient;
  triggerDownload?: TriggerDownload;
};

const DEFAULT_CLIENT: FileActionClient = {
  downloadDigiExamMigrationArtifact,
  downloadDigiExamMigrationCorrectionReplayArtifact,
  saveDigiExamMigrationArtifactToUserFiles,
};

function defaultTriggerDownload(
  artifact: SirConvertArtifactBlob,
  fallbackFilename: string,
): void {
  const objectUrl = URL.createObjectURL(artifact.blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = artifact.filename ?? fallbackFilename;
  link.rel = "noopener";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function toArtifactEntry(file: ExamConverterReviewFile): SirConvertArtifactEntry {
  const artifactKey = file.artifactActionReference?.artifactKey;
  if (!artifactKey) {
    throw new Error("Exam Converter file save requires an authorized artifact reference.");
  }
  return {
    artifact_key: artifactKey,
    availability: file.availability,
    content_type: file.contentType,
    filename: file.filename,
    sha256: file.sha256,
    size_bytes: file.sizeBytes,
    ...(file.unavailableCode ? { unavailable_code: file.unavailableCode } : {}),
  };
}

function withTeacherFacingFilename(
  artifact: SirConvertArtifactBlob,
  filename: string,
): SirConvertArtifactBlob {
  return {
    ...artifact,
    filename,
  };
}

function initialState(): ExamConverterFileActionState {
  return {
    download: "idle",
    save: "idle",
    savedFilename: null,
  };
}

function setFileActionState(
  states: ExamConverterFileActionStates,
  artifactKey: string,
  patch: Partial<ExamConverterFileActionState>,
): ExamConverterFileActionStates {
  return {
    ...states,
    [artifactKey]: {
      ...(states[artifactKey] ?? initialState()),
      ...patch,
    },
  };
}

export function useExamConverterFileActions(
  options: ExamConverterFileActionOptions = {},
) {
  const client = options.client ?? DEFAULT_CLIENT;
  const triggerDownload = options.triggerDownload ?? defaultTriggerDownload;
  const fileActionStates = ref<ExamConverterFileActionStates>({});

  function resetFileActions(): void {
    fileActionStates.value = {};
  }

  async function fetchArtifact(params: {
    correlationId: string;
    file: ExamConverterReviewFile;
    jobId: string;
  }): Promise<SirConvertArtifactBlob> {
    const actionReference = params.file.artifactActionReference;
    if (!actionReference) {
      throw new Error("Exam Converter file action requires an authorized artifact reference.");
    }
    if (actionReference.authority === "replay_result") {
      return await client.downloadDigiExamMigrationCorrectionReplayArtifact({
        artifactKey: actionReference.artifactKey,
        artifactSetId: actionReference.artifactSetId,
        contentSha256: actionReference.contentSha256,
        correlationId: params.correlationId,
        jobId: actionReference.jobId,
      });
    }
    return await client.downloadDigiExamMigrationArtifact({
      artifactKey: actionReference.artifactKey,
      correlationId: params.correlationId,
      jobId: params.jobId,
    });
  }

  async function downloadFile(params: {
    correlationId: string;
    file: ExamConverterReviewFile;
    jobId: string;
  }): Promise<void> {
    fileActionStates.value = setFileActionState(fileActionStates.value, params.file.artifactKey, {
      download: "running",
    });
    try {
      const artifact = await fetchArtifact(params);
      triggerDownload(
        withTeacherFacingFilename(artifact, params.file.filename),
        params.file.filename,
      );
      fileActionStates.value = setFileActionState(
        fileActionStates.value,
        params.file.artifactKey,
        {
          download: "done",
        },
      );
    } catch {
      fileActionStates.value = setFileActionState(
        fileActionStates.value,
        params.file.artifactKey,
        {
          download: "failed",
        },
      );
    }
  }

  async function saveFile(params: {
    correlationId: string;
    file: ExamConverterReviewFile;
    jobId: string;
  }): Promise<SirConvertSavedUserFile | null> {
    fileActionStates.value = setFileActionState(fileActionStates.value, params.file.artifactKey, {
      save: "running",
    });
    try {
      const artifactBlob = withTeacherFacingFilename(
        await fetchArtifact(params),
        params.file.filename,
      );
      const saved = await client.saveDigiExamMigrationArtifactToUserFiles({
        artifact: toArtifactEntry(params.file),
        artifactBlob,
        correlationId: params.correlationId,
        jobId: params.jobId,
      });
      fileActionStates.value = setFileActionState(
        fileActionStates.value,
        params.file.artifactKey,
        {
          save: "done",
          savedFilename: saved.vault_artifact.name,
        },
      );
      return saved;
    } catch {
      fileActionStates.value = setFileActionState(
        fileActionStates.value,
        params.file.artifactKey,
        {
          save: "failed",
        },
      );
      return null;
    }
  }

  return {
    downloadFile,
    fileActionStates,
    resetFileActions,
    saveFile,
  };
}
