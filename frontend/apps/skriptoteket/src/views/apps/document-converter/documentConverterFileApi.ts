/**
 * Document Converter single-file API client.
 *
 * Domain purpose:
 *   Submit owner-scoped single-file conversion work from either a local upload
 *   or a Mina filer source, then read back teacher-facing job status and
 *   server-owned result artifacts.
 *
 * Relationships:
 *   - Consumed by the Document Converter route state.
 *   - Uses generated OpenAPI types and the protected API client.
 *   - Complements the separate HTML/CSS project-preview API client.
 */

import {
  apiFetchBlobResponse,
  apiGet,
  apiPost,
  type ApiBlobResponse,
} from "../../../api/client";
import type { components } from "../../../api/openapi";

type ConversionRoute = components["schemas"]["ConversionHubRouteV2"];
type ConversionHubJobSpecV2 = components["schemas"]["ConversionHubJobSpecV2"];
type ConversionHubPdfLayoutV2 = components["schemas"]["ConversionHubPdfLayoutV2"];
type ConversionHubSourceFormatV2 = components["schemas"]["ConversionHubSourceFormatV2"];
type ConversionHubOutputFormatV2 = components["schemas"]["ConversionHubOutputFormatV2"];
type DocumentConverterJobStatusResult =
  components["schemas"]["DocumentConverterJobStatusResult"];
type DocumentConverterSavedFileOption =
  components["schemas"]["DocumentConverterSavedFileOption"];
type DocumentConverterSubmitResult = components["schemas"]["DocumentConverterSubmitResult"];
type ListDocumentConverterSavedFilesResult =
  components["schemas"]["ListDocumentConverterSavedFilesResult"];
type SaveDocumentConverterArtifactResult =
  components["schemas"]["SaveDocumentConverterArtifactResult"];

export type DocumentConverterSingleFileRoute = ConversionRoute;
export type DocumentConverterSavedFileSource = DocumentConverterSavedFileOption;
export type DocumentConverterSingleFileJobResult = DocumentConverterSubmitResult;
export type DocumentConverterSingleFileStatusResult = DocumentConverterJobStatusResult;
export type DocumentConverterSingleFileSaveResult = SaveDocumentConverterArtifactResult;

export type SubmitDocumentConverterUploadJobParams = {
  files: File[];
  outputFormat: ConversionHubOutputFormatV2;
  sourceFormat: ConversionHubSourceFormatV2;
};

export type SubmitDocumentConverterSavedFileJobParams = {
  outputFormat: ConversionHubOutputFormatV2;
  sourceFormat: ConversionHubSourceFormatV2;
  sourceRef: string;
};

const DOCUMENT_CONVERTER_ROOT = "/api/v1/apps/documents.conversion_hub/document-converter";

function withFilenameStem(path: string, filenameStem?: string | null): string {
  const trimmed = filenameStem?.trim();
  if (!trimmed) {
    return path;
  }
  const query = new URLSearchParams({ filename_stem: trimmed });
  return `${path}?${query.toString()}`;
}

function buildJobSpec(params: {
  outputFormat: ConversionHubOutputFormatV2;
  sourceFormat: ConversionHubSourceFormatV2;
}): ConversionHubJobSpecV2 {
  const jobSpec: ConversionHubJobSpecV2 = {
    output_format: params.outputFormat,
    source_format: params.sourceFormat,
  };
  if (params.outputFormat === "pdf") {
    const pdfLayout: ConversionHubPdfLayoutV2 = {
      margins_mm: 12,
      orientation: "portrait",
      paper_size: "a4",
    };
    jobSpec.pdf_layout = pdfLayout;
  }
  return jobSpec;
}

export async function listDocumentConverterSingleFileRoutes(): Promise<{
  routes: DocumentConverterSingleFileRoute[];
}> {
  return await apiGet<{ routes: DocumentConverterSingleFileRoute[] }>(
    `${DOCUMENT_CONVERTER_ROOT}/routes`,
  );
}

export async function listDocumentConverterSavedFiles(): Promise<ListDocumentConverterSavedFilesResult> {
  return await apiGet<ListDocumentConverterSavedFilesResult>(
    `${DOCUMENT_CONVERTER_ROOT}/saved-files`,
  );
}

export async function submitDocumentConverterUploadJob(
  params: SubmitDocumentConverterUploadJobParams,
): Promise<DocumentConverterSingleFileJobResult> {
  const form = new FormData();
  form.append("job_spec_json", JSON.stringify(buildJobSpec(params)));
  for (const file of params.files) {
    form.append("files", file, file.name);
  }
  form.append("wait_seconds", "0");
  return await apiPost<DocumentConverterSingleFileJobResult>(
    `${DOCUMENT_CONVERTER_ROOT}/jobs`,
    form,
  );
}

export async function submitDocumentConverterSavedFileJob(
  params: SubmitDocumentConverterSavedFileJobParams,
): Promise<DocumentConverterSingleFileJobResult> {
  return await apiPost<DocumentConverterSingleFileJobResult>(
    `${DOCUMENT_CONVERTER_ROOT}/saved-files/jobs`,
    {
      job_spec: buildJobSpec(params),
      source_ref: params.sourceRef,
      wait_seconds: 0,
    },
  );
}

export async function getDocumentConverterJobStatus(params: {
  jobId: string;
}): Promise<DocumentConverterSingleFileStatusResult> {
  return await apiGet<DocumentConverterSingleFileStatusResult>(
    `${DOCUMENT_CONVERTER_ROOT}/jobs/${encodeURIComponent(params.jobId)}`,
  );
}

export async function downloadDocumentConverterJobArtifact(params: {
  filenameStem?: string | null;
  jobId: string;
}): Promise<ApiBlobResponse> {
  return await apiFetchBlobResponse(
    withFilenameStem(
      `${DOCUMENT_CONVERTER_ROOT}/jobs/${encodeURIComponent(params.jobId)}/artifact`,
      params.filenameStem,
    ),
    { method: "GET" },
  );
}

export async function saveDocumentConverterJobArtifact(params: {
  filenameStem?: string | null;
  jobId: string;
}): Promise<DocumentConverterSingleFileSaveResult> {
  return await apiPost<DocumentConverterSingleFileSaveResult>(
    withFilenameStem(
      `${DOCUMENT_CONVERTER_ROOT}/jobs/${encodeURIComponent(params.jobId)}/artifact/save`,
      params.filenameStem,
    ),
  );
}
