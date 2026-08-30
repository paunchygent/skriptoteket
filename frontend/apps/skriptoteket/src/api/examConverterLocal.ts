/** Skriptoteket-owned authenticated Exam Converter transport. */

import {
  apiFetch,
  apiFetchBlobResponse,
  apiGet,
  apiPost,
} from "./client";
import { prepareDigiExamMigrationRequestContext } from "./sirConvertGateway/requestContext";
import type {
  DigiExamMigrationSubmitParams,
  ExamAuthoringCorrectionSourceStateIssueResult,
  SirConvertArtifactBlob,
  SirConvertArtifactManifest,
  SirConvertJob,
  SirConvertSubmittedJob,
  SirConvertTerminalResult,
} from "./sirConvertGateway";

const ROOT = "/api/v1/apps/documents.conversion_hub/exam-converter";

type LocalSubmitResult = {
  error: string | null;
  job_id: string;
  status: SirConvertJob["status"];
};

type LocalResult = {
  artifact_count: number;
  bundle_status: "complete" | "needs_review" | null;
  error: string | null;
  job_id: string;
  manual_follow_up_required: boolean;
  status: SirConvertJob["status"];
  warning_count: number;
};

function jobPath(jobId: string): string {
  return `${ROOT}/jobs/${encodeURIComponent(jobId)}`;
}

export async function submitLocalExamConversion(
  params: DigiExamMigrationSubmitParams,
): Promise<SirConvertSubmittedJob> {
  const requestContext = await prepareDigiExamMigrationRequestContext(params);
  const form = new FormData();
  form.append("file", params.file, params.file.name);
  if (params.ingestionOverlay) {
    form.append(
      "ingestion_overlay",
      new Blob([JSON.stringify(params.ingestionOverlay)], { type: "application/json" }),
      "ingestion-overlay.json",
    );
  }
  const result = await apiFetch<LocalSubmitResult>(`${ROOT}/conversions`, {
    body: form,
    method: "POST",
  });
  return {
    idempotentReplay: false,
    jobId: result.job_id,
    requestContext,
    status: result.status,
  };
}

export async function getLocalExamConversionJob(params: {
  correlationId?: string;
  jobId: string;
}): Promise<SirConvertJob> {
  const result = await apiGet<{ error: string | null; job_id: string; status: SirConvertJob["status"] }>(
    `/api/v1/apps/documents.conversion_hub/jobs/${encodeURIComponent(params.jobId)}`,
  );
  return { jobId: result.job_id, status: result.status };
}

export async function getLocalExamConversionResult(params: {
  correlationId?: string;
  jobId: string;
}): Promise<SirConvertTerminalResult> {
  const result = await apiGet<LocalResult>(`${jobPath(params.jobId)}/result`);
  if (result.status !== "succeeded" || !result.bundle_status) {
    throw new Error(result.error ?? "Exam Converter job did not finish.");
  }
  return {
    artifact: {
      content_type: "application/zip",
      filename: "examnet-bundle.zip",
      sha256: null,
      size_bytes: null,
    },
    conversion_metadata: {
      artifact_count: result.artifact_count,
      bundle_schema_version: "digiexam_migration_bundle_v3",
      bundle_status: result.bundle_status,
      manual_follow_up_required: result.manual_follow_up_required,
      route_key: "digiexam_dxe_to_examnet_bundle",
      source_sha256: null,
      target_readiness_report_artifact_key: "target_readiness_report",
      warning_count: result.warning_count,
    },
    job: { jobId: result.job_id, status: result.status },
  };
}

export async function listLocalExamConversionArtifacts(params: {
  correlationId?: string;
  jobId: string;
}): Promise<SirConvertArtifactManifest> {
  return await apiGet<SirConvertArtifactManifest>(`${jobPath(params.jobId)}/artifacts`);
}

export async function downloadLocalExamConversionArtifact(params: {
  artifactKey: string;
  correlationId?: string;
  jobId: string;
}): Promise<SirConvertArtifactBlob> {
  const response = await apiFetchBlobResponse(
    `${jobPath(params.jobId)}/artifacts/${encodeURIComponent(params.artifactKey)}`,
  );
  return {
    artifactKey: params.artifactKey,
    blob: response.blob,
    contentType: response.contentType,
    filename: response.filename,
  };
}

export async function getLocalExamConversionSourceState(params: {
  correlationId?: string;
  jobId: string;
}): Promise<ExamAuthoringCorrectionSourceStateIssueResult> {
  return await apiGet<ExamAuthoringCorrectionSourceStateIssueResult>(
    `${jobPath(params.jobId)}/source-state`,
  );
}

export async function replayLocalExamConversion(params: {
  correlationId?: string;
  jobId: string;
}): Promise<SirConvertArtifactManifest> {
  return await apiPost<SirConvertArtifactManifest>(`${jobPath(params.jobId)}/replay`);
}
