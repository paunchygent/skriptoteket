/**
 * Exam Converter file action state.
 *
 * Domain purpose:
 *   Download and save authenticated Exam Converter target files after the
 *   teacher has resolved export-blocking authoring state and replay returned
 *   artifact references authorized for file actions.
 *
 * Relationships:
 *   - Uses Skriptoteket-owned named artifact endpoints for downloads.
 *   - Uses Skriptoteket's owner-scoped user-file save client for Vault saves.
 *   - Keeps action state local to the current conversion job.
 */

import { ref } from "vue";

import {
  downloadLocalExamConversionArtifact,
  saveLocalExamConversionArtifact,
} from "../../../api/examConverterLocal";
import type {
  ExamConverterArtifactBlob,
  ExamConverterSavedUserFile,
} from "../../../api/examConverterContracts";
import type { ExamConverterReviewFile } from "./digiexamIrReviewParser";

export type ExamConverterFileActionStatus = "idle" | "running" | "done" | "failed";

export type ExamConverterFileActionState = {
  download: ExamConverterFileActionStatus;
  save: ExamConverterFileActionStatus;
  savedFilename: string | null;
};

export type ExamConverterFileActionStates = Record<string, ExamConverterFileActionState>;

type FileActionClient = {
  downloadDigiExamMigrationArtifact: typeof downloadLocalExamConversionArtifact;
  downloadDigiExamMigrationCorrectionReplayArtifact?: (params: {
    artifactKey: string;
    artifactSetId: string;
    contentSha256: string;
    correlationId: string;
    jobId: string;
  }) => Promise<ExamConverterArtifactBlob>;
  saveLocalExamConversionArtifact: typeof saveLocalExamConversionArtifact;
};

type TriggerDownload = (artifact: ExamConverterArtifactBlob, fallbackFilename: string) => void;

export type ExamConverterFileActionOptions = {
  client?: FileActionClient;
  triggerDownload?: TriggerDownload;
};

const DEFAULT_CLIENT: FileActionClient = {
  downloadDigiExamMigrationArtifact: downloadLocalExamConversionArtifact,
  saveLocalExamConversionArtifact: async (params) =>
    await saveLocalExamConversionArtifact(params),
};

function defaultTriggerDownload(
  artifact: ExamConverterArtifactBlob,
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

function withTeacherFacingFilename(
  artifact: ExamConverterArtifactBlob,
  filename: string,
): ExamConverterArtifactBlob {
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
  }): Promise<ExamConverterArtifactBlob> {
    const actionReference = params.file.artifactActionReference;
    if (!actionReference) {
      throw new Error("Exam Converter file action requires an authorized artifact reference.");
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
  }): Promise<ExamConverterSavedUserFile | null> {
    fileActionStates.value = setFileActionState(fileActionStates.value, params.file.artifactKey, {
      save: "running",
    });
    try {
      const actionReference = params.file.artifactActionReference;
      if (!actionReference) {
        throw new Error("Exam Converter file save requires an authorized artifact reference.");
      }
      const saved = await client.saveLocalExamConversionArtifact({
        artifactKey: actionReference.artifactKey,
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
