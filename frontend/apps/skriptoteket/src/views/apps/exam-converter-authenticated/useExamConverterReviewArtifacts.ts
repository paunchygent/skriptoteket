/**
 * Exam Converter review artifact loader.
 *
 * Domain purpose:
 *   Load the read-only DigiExam review artifacts for one authenticated
 *   conversion job and expose a teacher-facing projection to the workspace.
 *
 * Relationships:
 *   - Uses Skriptoteket-owned named artifact endpoints.
 *   - Delegates IR validation and projection to `digiexamIrReviewParser`.
 *   - Does not download final files, save files, or write review state.
 */

import { ref } from "vue";

import {
  downloadLocalExamConversionArtifact,
  listLocalExamConversionArtifacts,
} from "../../../api/examConverterLocal";
import { parseTargetReadinessReport } from "../../../api/examConverterContracts";
import {
  DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
  DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
  DIGIEXAM_ARTIFACT_EFFECTIVE_IR_JSON,
  DIGIEXAM_ARTIFACT_IR_JSON,
  DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
  DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
  EXAM_CONVERTER_ARTIFACT_AVAILABLE,
} from "../../../api/examConverterContracts";
import type { ExamConverterArtifactBlob, ExamConverterArtifactManifest } from "../../../api/examConverterContracts";
import {
  parseAnswerKeyCompletionReport,
  parseEffectiveItemState,
} from "./digiexamAnswerKeyCompletionReport";
import {
  parseExamConverterReviewProjection,
  type ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";

type ReviewArtifactClient = {
  downloadDigiExamMigrationArtifact: typeof downloadLocalExamConversionArtifact;
  listDigiExamMigrationArtifacts: typeof listLocalExamConversionArtifacts;
};

export type ExamConverterReviewArtifactsStatus = "idle" | "loading" | "ready" | "failed";

export type ExamConverterReviewArtifactsLoadParams = {
  completionReportRequired?: boolean;
  correlationId: string;
  jobId: string;
  preserveCurrentProjection?: boolean;
};

export type ExamConverterReviewArtifactsOptions = {
  client?: ReviewArtifactClient;
};

const DEFAULT_CLIENT: ReviewArtifactClient = {
  downloadDigiExamMigrationArtifact: downloadLocalExamConversionArtifact,
  listDigiExamMigrationArtifacts: listLocalExamConversionArtifacts,
};

async function readArtifactJson(artifact: ExamConverterArtifactBlob): Promise<unknown> {
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

function availableArtifactSha256(params: {
  artifactKey: string;
  artifactManifest: ExamConverterArtifactManifest;
  required: boolean;
}): string | null {
  const entry = params.artifactManifest.artifacts.find(
    (artifact) => artifact.artifact_key === params.artifactKey,
  );
  if (!entry || entry.availability !== EXAM_CONVERTER_ARTIFACT_AVAILABLE) {
    if (params.required) {
      throw new Error(`Exam Converter bundle is missing ${params.artifactKey}.`);
    }
    return null;
  }
  if (!entry.sha256) {
    throw new Error(`Exam Converter bundle artifact ${params.artifactKey} is missing sha256.`);
  }
  return entry.sha256;
}

async function loadOptionalArtifactJson(params: {
  artifactKey: string;
  artifactManifest: ExamConverterArtifactManifest;
  client: ReviewArtifactClient;
  correlationId: string;
  jobId: string;
  required: boolean;
}): Promise<{ payload: unknown; sha256: string } | null> {
  const sha256 = availableArtifactSha256({
    artifactKey: params.artifactKey,
    artifactManifest: params.artifactManifest,
    required: params.required,
  });
  if (!sha256) return null;
  const payload = await params.client
    .downloadDigiExamMigrationArtifact({
      artifactKey: params.artifactKey,
      correlationId: params.correlationId,
      jobId: params.jobId,
    })
    .then(readArtifactJson);
  return { payload, sha256 };
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

  function setReviewArtifactsForInspection(
    inspectionProjection: ExamConverterReviewProjection,
  ): void {
    loadToken.value += 1;
    projection.value = inspectionProjection;
    status.value = "ready";
  }

  async function loadReviewArtifacts(
    params: ExamConverterReviewArtifactsLoadParams,
  ): Promise<ExamConverterReviewProjection | null> {
    const token = loadToken.value + 1;
    loadToken.value = token;
    const isBackgroundRefresh =
      params.preserveCurrentProjection === true && projection.value !== null;
    if (!isBackgroundRefresh) {
      projection.value = null;
      status.value = "loading";
    }

    try {
      const artifactManifest = await client.listDigiExamMigrationArtifacts(params);
      const [
        irJson,
        migrationManifest,
        targetReadinessReport,
        answerKeyReviewStateArtifact,
        completionReportArtifact,
        effectiveIrArtifact,
      ] = await Promise.all([
        client
          .downloadDigiExamMigrationArtifact({
            artifactKey: DIGIEXAM_ARTIFACT_IR_JSON,
            correlationId: params.correlationId,
            jobId: params.jobId,
          })
          .then(readArtifactJson),
        client
          .downloadDigiExamMigrationArtifact({
            artifactKey: DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST,
            correlationId: params.correlationId,
            jobId: params.jobId,
          })
          .then(readArtifactJson),
        client
          .downloadDigiExamMigrationArtifact({
            artifactKey: DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT,
            correlationId: params.correlationId,
            jobId: params.jobId,
          })
          .then(readArtifactJson)
          .then(parseTargetReadinessReport),
        loadOptionalArtifactJson({
          artifactKey: DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT,
          artifactManifest,
          client,
          correlationId: params.correlationId,
          jobId: params.jobId,
          required: true,
        }),
        loadOptionalArtifactJson({
          artifactKey: DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT,
          artifactManifest,
          client,
          correlationId: params.correlationId,
          jobId: params.jobId,
          required: params.completionReportRequired === true,
        }),
        loadOptionalArtifactJson({
          artifactKey: DIGIEXAM_ARTIFACT_EFFECTIVE_IR_JSON,
          artifactManifest,
          client,
          correlationId: params.correlationId,
          jobId: params.jobId,
          required: false,
        }),
      ]);
      if (loadToken.value !== token) {
        return null;
      }
      const answerKeyCompletionReport = completionReportArtifact
        ? parseAnswerKeyCompletionReport({
            completionReportSha256: completionReportArtifact.sha256,
            payload: completionReportArtifact.payload,
          })
        : null;
      const effectiveItemState = effectiveIrArtifact
        ? parseEffectiveItemState(effectiveIrArtifact.payload)
        : null;
      const parsedProjection = parseExamConverterReviewProjection({
        answerKeyCompletionReport,
        answerKeyReviewStateReport: answerKeyReviewStateArtifact?.payload,
        artifactManifest,
        effectiveAnswerKeysByItem: effectiveItemState?.answerKeysByItem ?? null,
        effectivePointCorrectionsByItem: effectiveItemState?.pointCorrectionsByItem ?? null,
        irJson,
        migrationManifest,
        targetReadinessReport,
      });
      projection.value = parsedProjection;
      status.value = "ready";
      return parsedProjection;
    } catch {
      if (loadToken.value === token) {
        if (!isBackgroundRefresh) {
          projection.value = null;
          status.value = "failed";
        }
      }
      return null;
    }
  }

  return {
    loadReviewArtifacts,
    projection,
    resetReviewArtifacts,
    setReviewArtifactsForInspection,
    status,
  };
}
