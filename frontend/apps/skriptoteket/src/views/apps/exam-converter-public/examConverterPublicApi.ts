/**
 * Public Exam Converter API boundary.
 *
 * Domain purpose:
 *   Keep the anonymous Exam Converter transport contract in one place so the
 *   browser view never owns public route construction, multipart payload shape,
 *   or artifact download calls directly.
 *
 * Relationships:
 *   - Uses credential-omitting public API helpers from `api/client`.
 *   - Consumed by `usePublicExamConverterRuntime` for state orchestration.
 */

import {
  publicApiFetchBlobResponse,
  publicApiGet,
  publicApiPost,
  type ApiBlobResponse,
} from "../../../api/client";
import type { ExamConverterTarget } from "../exam-converter/types";

export type { ExamConverterTarget };

export type PublicJobStatus =
  | "submitted"
  | "queued"
  | "processing"
  | "succeeded"
  | "failed"
  | "canceled"
  | "expired";

export type SubmitResponse = {
  public_job_id: string;
  status: PublicJobStatus;
  requested_targets: ExamConverterTarget[];
  expires_at: string;
  poll_url: string;
  result_url: string;
  artifact_manifest_url: string;
};

export type StatusResponse = {
  public_job_id: string;
  status: PublicJobStatus;
  expires_at: string;
  error: string | null;
};

export type ArtifactEntry = {
  artifact_key: string;
  filename: string | null;
  content_type: string | null;
  availability: string;
  download_url: string | null;
  blocker_code: string | null;
};

export type ArtifactManifest = {
  status: PublicJobStatus;
  artifacts: ArtifactEntry[];
  manual_follow_up: Record<string, unknown> | null;
  warnings: Record<string, unknown> | null;
};

export type SubmitPublicExamConverterJobParams = {
  sourceDxe: File;
  gradedResultPdf: File | null;
  targets: ExamConverterTarget[];
};

const EXAM_CONVERTER_PUBLIC_API_NAMESPACE =
  "/api/v1/public/apps/documents.conversion_hub/exam-converter";

export async function submitPublicExamConverterJob(
  params: SubmitPublicExamConverterJobParams,
): Promise<SubmitResponse> {
  const form = new FormData();
  form.append("source_dxe", params.sourceDxe);
  if (params.gradedResultPdf) {
    form.append("graded_result_pdf", params.gradedResultPdf);
  }
  form.append("targets_json", JSON.stringify(params.targets));

  return await publicApiPost<SubmitResponse>(
    `${EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/jobs`,
    form,
  );
}

export async function getPublicExamConverterStatus(
  pollUrl: string,
): Promise<StatusResponse> {
  return await publicApiGet<StatusResponse>(pollUrl);
}

export async function getPublicExamConverterArtifactManifest(
  manifestUrl: string,
): Promise<ArtifactManifest> {
  return await publicApiGet<ArtifactManifest>(manifestUrl);
}

export async function downloadPublicExamConverterArtifact(
  downloadUrl: string,
): Promise<ApiBlobResponse> {
  return await publicApiFetchBlobResponse(downloadUrl);
}
