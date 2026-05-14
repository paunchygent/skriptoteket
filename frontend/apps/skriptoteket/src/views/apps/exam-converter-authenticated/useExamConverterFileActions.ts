/**
 * Exam Converter file action state.
 *
 * Domain purpose:
 *   Download and save authenticated Exam Converter target files after the
 *   teacher has either resolved or accepted the current review state.
 *
 * Relationships:
 *   - Uses the HuleEdu Gateway Sir Convert artifact client for named downloads.
 *   - Uses Skriptoteket's owner-scoped user-file save client for Vault saves.
 *   - Keeps action state local to the current conversion job.
 */

import { ref } from "vue";

import {
  downloadDigiExamMigrationArtifact,
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
  saveDigiExamMigrationArtifactToUserFiles: typeof saveDigiExamMigrationArtifactToUserFiles;
};

type TriggerDownload = (artifact: SirConvertArtifactBlob, fallbackFilename: string) => void;

export type ExamConverterFileActionOptions = {
  client?: FileActionClient;
  triggerDownload?: TriggerDownload;
};

const DEFAULT_CLIENT: FileActionClient = {
  downloadDigiExamMigrationArtifact,
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
  return {
    artifact_key: file.artifactKey,
    availability: file.availability,
    content_type: file.contentType,
    filename: file.filename,
    sha256: file.sha256,
    size_bytes: file.sizeBytes,
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
    return await client.downloadDigiExamMigrationArtifact({
      artifactKey: params.file.artifactKey,
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
      triggerDownload(artifact, params.file.filename);
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
      const artifactBlob = await fetchArtifact(params);
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
