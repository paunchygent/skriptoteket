/**
 * Classroom planner export API helpers.
 *
 * This module keeps the teacher-facing seating and grouping export job
 * contracts in one frontend seam so the planner view layer can orchestrate
 * artifact flows without embedding raw request paths or payload details inside
 * components.
 */

import { apiFetchBlob, apiGet, apiPost } from "../../api/client";

export type SeatingExportOption = "a3_landscape" | "a4_landscape" | "xlsx";
export type SeatingExportKind = "pdf" | "xlsx";
export type SeatingExportLayoutId = "pretty_brutalist_poster";
export type SeatingExportPaperSize = "a3_landscape" | "a4_landscape";
export type SeatingExportJobStatus = "submitted" | "processing" | "succeeded" | "failed";
export type GroupingExportOption = "xlsx" | "pdf_a4_portrait";
export type GroupingExportKind = "xlsx" | "pdf";
export type GroupingExportPaperSize = "a4_portrait";
export type GroupingExportJobStatus = "submitted" | "processing" | "succeeded" | "failed";

export type SeatingExportVaultArtifact = {
  file_id: string;
  name: string;
  bytes: number;
  created_at: string;
};

export type SeatingExportJob = {
  job_id: string;
  draft_id: string;
  export_kind: SeatingExportKind;
  layout_id: SeatingExportLayoutId | null;
  paper_size: SeatingExportPaperSize | null;
  status: SeatingExportJobStatus;
  created_at: string;
  download_url: string | null;
  vault_artifact: SeatingExportVaultArtifact | null;
  error: string | null;
};

export type GroupingExportVaultArtifact = {
  file_id: string;
  name: string;
  bytes: number;
  created_at: string;
};

export type GroupingExportJob = {
  job_id: string;
  draft_id: string;
  export_kind: GroupingExportKind;
  paper_size: GroupingExportPaperSize | null;
  status: GroupingExportJobStatus;
  created_at: string;
  download_url: string | null;
  vault_artifact: GroupingExportVaultArtifact | null;
  error: string | null;
};

type CreateSeatingPdfExportJobRequest = {
  export_kind: "pdf";
  layout_id: "pretty_brutalist_poster";
  paper_size: SeatingExportPaperSize;
};

type CreateSeatingXlsxExportJobRequest = {
  export_kind: "xlsx";
  layout_id: null;
  paper_size: null;
};

type CreateSeatingExportJobRequest =
  | CreateSeatingPdfExportJobRequest
  | CreateSeatingXlsxExportJobRequest;

type CreateGroupingPdfExportJobRequest = {
  export_kind: "pdf";
  paper_size: GroupingExportPaperSize;
};

type CreateGroupingXlsxExportJobRequest = {
  export_kind: "xlsx";
  paper_size: null;
};

type CreateGroupingExportJobRequest =
  | CreateGroupingPdfExportJobRequest
  | CreateGroupingXlsxExportJobRequest;

const PDF_EXPORT_KIND = "pdf" as const;
const XLSX_EXPORT_KIND = "xlsx" as const;
const LAYOUT_ID = "pretty_brutalist_poster" as const;
const GROUPING_PDF_PAPER_SIZE = "a4_portrait" as const;

export async function createSeatingExportJob(
  draftId: string,
  option: SeatingExportOption,
): Promise<SeatingExportJob> {
  const body = buildCreateSeatingExportJobRequest(option);
  return await apiPost<SeatingExportJob>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${encodeURIComponent(draftId)}/exports/jobs`,
    body,
  );
}

export async function getSeatingExportJob(jobId: string): Promise<SeatingExportJob> {
  return await apiGet<SeatingExportJob>(
    `/api/v1/apps/classroom.group-seating-studio/exports/jobs/${encodeURIComponent(jobId)}`,
  );
}

export async function createGroupingExportJob(
  draftId: string,
  option: GroupingExportOption,
): Promise<GroupingExportJob> {
  const body = buildCreateGroupingExportJobRequest(option);
  return await apiPost<GroupingExportJob>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${encodeURIComponent(draftId)}/exports/jobs`,
    body,
  );
}

export async function getGroupingExportJob(jobId: string): Promise<GroupingExportJob> {
  return await apiGet<GroupingExportJob>(
    `/api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/${encodeURIComponent(jobId)}`,
  );
}

export async function getRecoverableGroupingExportJob(
  draftId: string,
): Promise<GroupingExportJob | null> {
  return await apiGet<GroupingExportJob | null>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${encodeURIComponent(draftId)}/exports/jobs/recover`,
  );
}

export async function downloadGroupingExportJob(jobId: string): Promise<Blob> {
  return await apiFetchBlob(getGroupingExportJobDownloadHref(jobId));
}

export function getGroupingExportJobDownloadHref(jobId: string): string {
  return `/api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/${encodeURIComponent(jobId)}/download`;
}

export async function getRecoverableSeatingExportJob(
  draftId: string,
): Promise<SeatingExportJob | null> {
  return await apiGet<SeatingExportJob | null>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${encodeURIComponent(draftId)}/exports/jobs/recover`,
  );
}

export async function downloadSeatingExportJob(jobId: string): Promise<Blob> {
  return await apiFetchBlob(getSeatingExportJobDownloadHref(jobId));
}

export function getSeatingExportJobDownloadHref(jobId: string): string {
  return `/api/v1/apps/classroom.group-seating-studio/exports/jobs/${encodeURIComponent(jobId)}/download`;
}

function buildCreateSeatingExportJobRequest(
  option: SeatingExportOption,
): CreateSeatingExportJobRequest {
  if (option === "xlsx") {
    return {
      export_kind: XLSX_EXPORT_KIND,
      layout_id: null,
      paper_size: null,
    };
  }
  return {
    export_kind: PDF_EXPORT_KIND,
    layout_id: LAYOUT_ID,
    paper_size: option,
  };
}

function buildCreateGroupingExportJobRequest(
  option: GroupingExportOption,
): CreateGroupingExportJobRequest {
  if (option === "xlsx") {
    return {
      export_kind: XLSX_EXPORT_KIND,
      paper_size: null,
    };
  }
  return {
    export_kind: PDF_EXPORT_KIND,
    paper_size: GROUPING_PDF_PAPER_SIZE,
  };
}
