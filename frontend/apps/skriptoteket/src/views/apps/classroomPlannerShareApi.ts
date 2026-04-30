/**
 * Classroom planner share-link API helpers.
 *
 * This module keeps authenticated Klassrumskartan share endpoints beside the
 * existing export API seam while staying separate from export jobs. It exposes
 * create/list/revoke helpers for the route-shell share flow and relies on the
 * generated OpenAPI schema for response types.
 */

import { apiGet, apiPost } from "../../api/client";
import type { components } from "../../api/openapi";

export type ClassroomPlannerShareArtifact =
  components["schemas"]["ClassroomPlannerShareArtifactDto"];

export type CreatedClassroomPlannerShare =
  components["schemas"]["CreatedClassroomPlannerShareDto"];

type CreateClassroomPlannerShareRequest =
  components["schemas"]["CreateClassroomPlannerShareRequest"];

export async function createGroupingShare(params: {
  draftId: string;
  expectedRevision: number;
}): Promise<CreatedClassroomPlannerShare> {
  return await apiPost<CreatedClassroomPlannerShare>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${encodeURIComponent(params.draftId)}/share`,
    buildCreateShareRequest(params.expectedRevision),
  );
}

export async function createSeatingShare(params: {
  draftId: string;
  expectedRevision: number;
}): Promise<CreatedClassroomPlannerShare> {
  return await apiPost<CreatedClassroomPlannerShare>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${encodeURIComponent(params.draftId)}/share`,
    buildCreateShareRequest(params.expectedRevision),
  );
}

export async function listGroupingShares(
  draftId: string,
): Promise<ClassroomPlannerShareArtifact[]> {
  return await apiGet<ClassroomPlannerShareArtifact[]>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${encodeURIComponent(draftId)}/shares`,
  );
}

export async function listSeatingShares(
  draftId: string,
): Promise<ClassroomPlannerShareArtifact[]> {
  return await apiGet<ClassroomPlannerShareArtifact[]>(
    `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${encodeURIComponent(draftId)}/shares`,
  );
}

export async function revokeClassroomPlannerShare(
  shareId: string,
): Promise<ClassroomPlannerShareArtifact> {
  return await apiPost<ClassroomPlannerShareArtifact>(
    `/api/v1/apps/classroom.group-seating-studio/shares/${encodeURIComponent(shareId)}/revoke`,
  );
}

function buildCreateShareRequest(expectedRevision: number): CreateClassroomPlannerShareRequest {
  return {
    expected_revision: expectedRevision,
  };
}
