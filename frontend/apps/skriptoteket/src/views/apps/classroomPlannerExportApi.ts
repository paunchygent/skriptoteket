/**
 * Classroom planner seating export API helpers.
 *
 * This module keeps the teacher-facing seating export job contract in one
 * frontend seam so the planner view layer can orchestrate exports without
 * embedding raw request paths or payload details inside components.
 */

import { apiFetchBlob, apiGet, apiPost } from "../../api/client";

export type SeatingExportPaperSize = "a3_landscape" | "a4_landscape";
export type SeatingExportJobStatus = "submitted" | "processing" | "succeeded" | "failed";

export type SeatingExportVaultArtifact = {
  file_id: string;
  name: string;
  bytes: number;
  created_at: string;
};

export type SeatingExportJob = {
  job_id: string;
  draft_id: string;
  export_kind: "pdf";
  layout_id: "pretty_brutalist_poster";
  paper_size: SeatingExportPaperSize;
  status: SeatingExportJobStatus;
  created_at: string;
  download_url: string | null;
  vault_artifact: SeatingExportVaultArtifact | null;
  error: string | null;
};

type CreateSeatingExportJobRequest = {
  export_kind: "pdf";
  layout_id: "pretty_brutalist_poster";
  paper_size: SeatingExportPaperSize;
};

const EXPORT_KIND = "pdf" as const;
const LAYOUT_ID = "pretty_brutalist_poster" as const;

export async function createSeatingExportJob(
  draftId: string,
  paperSize: SeatingExportPaperSize,
): Promise<SeatingExportJob> {
  const body: CreateSeatingExportJobRequest = {
    export_kind: EXPORT_KIND,
    layout_id: LAYOUT_ID,
    paper_size: paperSize,
  };
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

export async function downloadSeatingExportJob(jobId: string): Promise<Blob> {
  return await apiFetchBlob(getSeatingExportJobDownloadHref(jobId));
}

export function getSeatingExportJobDownloadHref(jobId: string): string {
  return `/api/v1/apps/classroom.group-seating-studio/exports/jobs/${encodeURIComponent(jobId)}/download`;
}
