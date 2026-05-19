/**
 * Exam Converter correction-session API client.
 *
 * Purpose:
 *   Read and mutate Skriptoteket-owned durable correction-session truth for
 *   authenticated Exam Converter jobs.
 *
 * Relationships:
 *   - Wraps the generated OpenAPI correction-session schemas from PR-0334.
 *   - Consumed by replay orchestration and later UI readback integration.
 */

import { apiGet, apiPost, apiPut } from "./client";
import type { components } from "./openapi";

export type ExamConverterCorrectionIntentResponse =
  components["schemas"]["ExamConverterCorrectionIntentResponse"];
export type ExamConverterCorrectionIntentWrite =
  components["schemas"]["ExamConverterCorrectionIntentWrite"];
export type ExamConverterCorrectionSessionResponse =
  components["schemas"]["ExamConverterCorrectionSessionResponse"];
export type ExamConverterCorrectionSourceBinding =
  components["schemas"]["ExamConverterCorrectionSourceBinding"];
export type UpsertExamConverterCorrectionIntentRequest =
  components["schemas"]["UpsertExamConverterCorrectionIntentRequest"];

export type RegisterExamConverterConversionHubJobRequest =
  components["schemas"]["RegisterExamConverterConversionHubJobRequest"];
export type RegisterExamConverterConversionHubJobResult =
  components["schemas"]["RegisterExamConverterConversionHubJobResult"];

const CORRECTION_SESSION_ROOT =
  "/api/v1/apps/documents.conversion_hub/exam-converter/jobs";

export async function registerExamConverterConversionHubJob(params: {
  request: RegisterExamConverterConversionHubJobRequest;
}): Promise<RegisterExamConverterConversionHubJobResult> {
  return await apiPost<RegisterExamConverterConversionHubJobResult>(
    CORRECTION_SESSION_ROOT,
    params.request,
  );
}

function correctionSessionPath(conversionHubJobId: string): string {
  return `${CORRECTION_SESSION_ROOT}/${encodeURIComponent(conversionHubJobId)}/correction-session`;
}

function correctionSessionIntentsPath(conversionHubJobId: string): string {
  return `${correctionSessionPath(conversionHubJobId)}/intents`;
}

export async function getExamConverterCorrectionSession(params: {
  conversionHubJobId: string;
}): Promise<ExamConverterCorrectionSessionResponse> {
  return await apiGet<ExamConverterCorrectionSessionResponse>(
    correctionSessionPath(params.conversionHubJobId),
  );
}

export async function upsertExamConverterCorrectionIntent(params: {
  conversionHubJobId: string;
  request: UpsertExamConverterCorrectionIntentRequest;
}): Promise<ExamConverterCorrectionSessionResponse> {
  return await apiPut<ExamConverterCorrectionSessionResponse>(
    correctionSessionIntentsPath(params.conversionHubJobId),
    params.request,
  );
}
