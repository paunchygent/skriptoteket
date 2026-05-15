/**
 * Exam Converter review artifact loader.
 *
 * Domain purpose:
 *   Load the read-only DigiExam review artifacts for one authenticated
 *   conversion job and expose a teacher-facing projection to the workspace.
 *
 * Relationships:
 *   - Uses the existing Sir Convert Gateway artifact client.
 *   - Delegates IR validation and projection to `digiexamIrReviewParser`.
 *   - Does not download final files, save files, or write review state.
 */

import { ref } from "vue";

import {
  downloadDigiExamMigrationArtifact,
  listDigiExamMigrationArtifacts,
  parseTargetReadinessReport,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
} from "../../../api/sirConvertGateway/contractValues";
import type { SirConvertArtifactBlob } from "../../../api/sirConvertGateway";
import {
  parseExamConverterReviewProjection,
  type ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";

type ReviewArtifactClient = {
  downloadDigiExamMigrationArtifact: typeof downloadDigiExamMigrationArtifact;
  listDigiExamMigrationArtifacts: typeof listDigiExamMigrationArtifacts;
};

export type ExamConverterReviewArtifactsStatus = "idle" | "loading" | "ready" | "failed";

export type ExamConverterReviewArtifactsLoadParams = {
  correlationId: string;
  jobId: string;
};

export type ExamConverterReviewArtifactsOptions = {
  client?: ReviewArtifactClient;
};

const DEFAULT_CLIENT: ReviewArtifactClient = {
  downloadDigiExamMigrationArtifact,
  listDigiExamMigrationArtifacts,
};

async function readArtifactJson(artifact: SirConvertArtifactBlob): Promise<unknown> {
  const text =
    typeof artifact.blob.text === "function"
      ? await artifact.blob.text()
      : await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.addEventListener("load", () => resolve(String(reader.result ?? "")));
          reader.addEventListener("error", () => reject(reader.error ?? new Error("Read failed.")));
          reader.readAsText(artifact.blob);
        });
  return JSON.parse(text) as unknown;
}

export function useExamConverterReviewArtifacts(
  options: ExamConverterReviewArtifactsOptions = {},
) {
  const client = options.client ?? DEFAULT_CLIENT;
  const loadToken = ref(0);
  const projection = ref<ExamConverterReviewProjection | null>(null);
  const status = ref<ExamConverterReviewArtifactsStatus>("idle");

  function resetReviewArtifacts(): void {
    loadToken.value += 1;
    projection.value = null;
    status.value = "idle";
  }

  async function loadReviewArtifacts(
    params: ExamConverterReviewArtifactsLoadParams,
  ): Promise<ExamConverterReviewProjection | null> {
    const token = loadToken.value + 1;
    loadToken.value = token;
    projection.value = null;
    status.value = "loading";

    try {
      const artifactManifest = await client.listDigiExamMigrationArtifacts(params);
      const [irJson, migrationManifest, targetReadinessReport] = await Promise.all([
        client
          .downloadDigiExamMigrationArtifact({
            ...params,
            artifactKey: DIGIEXAM_ARTIFACT_IR_JSON,
          })
          .then(readArtifactJson),
        client
          .downloadDigiExamMigrationArtifact({
            ...params,
            artifactKey: DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
          })
          .then(readArtifactJson),
        client
          .downloadDigiExamMigrationArtifact({
            ...params,
            artifactKey: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
          })
          .then(readArtifactJson)
          .then(parseTargetReadinessReport),
      ]);
      if (loadToken.value !== token) {
        return null;
      }
      const parsedProjection = parseExamConverterReviewProjection({
        artifactManifest,
        irJson,
        migrationManifest,
        targetReadinessReport,
      });
      projection.value = parsedProjection;
      status.value = "ready";
      return parsedProjection;
    } catch {
      if (loadToken.value === token) {
        projection.value = null;
        status.value = "failed";
      }
      return null;
    }
  }

  return {
    loadReviewArtifacts,
    projection,
    resetReviewArtifacts,
    status,
  };
}
