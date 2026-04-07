/**
 * Classroom planner public export API helpers.
 *
 * This module owns the guest-only direct-download export requests that target
 * the public Klassrumskartan namespace. It keeps browser-owned snapshot
 * payloads out of the authenticated export-job seam.
 */

import { apiFetchBlobResponse } from "../../api/client";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type {
  GroupingExportKind,
  GroupingExportPaperSize,
  GroupingExportOption,
  SeatingExportKind,
  SeatingExportLayoutId,
  SeatingExportOption,
  SeatingExportPaperSize,
} from "./classroomPlannerExportApi";

export type PublicExportDownload = {
  blob: Blob;
  filename: string | null;
  mediaType: string | null;
};

type PublicGroupingExportRequest = {
  snapshot: ClassroomPlannerGuestSnapshot;
  expected_revision: number;
  export_kind: GroupingExportKind;
  paper_size: GroupingExportPaperSize | null;
};

type PublicSeatingExportRequest = {
  snapshot: ClassroomPlannerGuestSnapshot;
  expected_revision: number;
  export_kind: SeatingExportKind;
  layout_id: SeatingExportLayoutId | null;
  paper_size: SeatingExportPaperSize | null;
};

const PDF_EXPORT_KIND = "pdf";
const XLSX_EXPORT_KIND = "xlsx";
const LAYOUT_ID = "pretty_brutalist_poster";
const GROUPING_PDF_PAPER_SIZE = "a4_portrait";

export async function exportPublicGroupingSnapshot(
  snapshot: ClassroomPlannerGuestSnapshot,
  expectedRevision: number,
  option: GroupingExportOption,
): Promise<PublicExportDownload> {
  const body = buildPublicGroupingExportRequest(snapshot, expectedRevision, option);
  const response = await apiFetchBlobResponse(
    "/api/v1/public/apps/classroom.group-seating-studio/grouping/export",
    {
      method: "POST",
      body,
    },
  );
  return {
    blob: response.blob,
    filename: response.filename,
    mediaType: response.contentType,
  };
}

export async function exportPublicSeatingSnapshot(
  snapshot: ClassroomPlannerGuestSnapshot,
  expectedRevision: number,
  option: SeatingExportOption,
): Promise<PublicExportDownload> {
  const body = buildPublicSeatingExportRequest(snapshot, expectedRevision, option);
  const response = await apiFetchBlobResponse(
    "/api/v1/public/apps/classroom.group-seating-studio/seating/export",
    {
      method: "POST",
      body,
    },
  );
  return {
    blob: response.blob,
    filename: response.filename,
    mediaType: response.contentType,
  };
}

function buildPublicGroupingExportRequest(
  snapshot: ClassroomPlannerGuestSnapshot,
  expectedRevision: number,
  option: GroupingExportOption,
): PublicGroupingExportRequest {
  if (option === "xlsx") {
    return {
      snapshot,
      expected_revision: expectedRevision,
      export_kind: XLSX_EXPORT_KIND,
      paper_size: null,
    };
  }
  return {
    snapshot,
    expected_revision: expectedRevision,
    export_kind: PDF_EXPORT_KIND,
    paper_size: GROUPING_PDF_PAPER_SIZE,
  };
}

function buildPublicSeatingExportRequest(
  snapshot: ClassroomPlannerGuestSnapshot,
  expectedRevision: number,
  option: SeatingExportOption,
): PublicSeatingExportRequest {
  if (option === "xlsx") {
    return {
      snapshot,
      expected_revision: expectedRevision,
      export_kind: XLSX_EXPORT_KIND,
      layout_id: null,
      paper_size: null,
    };
  }
  return {
    snapshot,
    expected_revision: expectedRevision,
    export_kind: PDF_EXPORT_KIND,
    layout_id: LAYOUT_ID,
    paper_size: option,
  };
}
