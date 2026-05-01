/**
 * Classroom planner public guest share-link API helpers.
 *
 * This module keeps ADR-0084 guest `Dela länk` calls on the public helper
 * route family. It deliberately uses the public API client so guest sharing
 * does not bootstrap shared-auth CSRF or call owner-scoped APIs.
 */

import { publicApiPost } from "../../api/client";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { ClassroomPlannerShareArtifact } from "./classroomPlannerShareApi";

type PublicGuestShareRequest = {
  snapshot: ClassroomPlannerGuestSnapshot;
  expected_revision: number;
  client_operation_id: string;
  revoke_secret: string;
  previous_public_path: string | null;
  previous_revoke_secret: string | null;
};

type PublicGuestShareRevokeRequest = {
  public_path: string;
  revoke_secret: string;
};

export type CreatedPublicGuestShare = {
  artifact: ClassroomPlannerShareArtifact;
  public_path: string;
  public_url: string;
  public_revoke_secret: string;
  superseded_previous: boolean;
  reused_client_operation: boolean;
};

export type RevokedPublicGuestShare = {
  artifact: ClassroomPlannerShareArtifact;
  public_path: string;
  public_url: string;
};

export async function createPublicGroupingShare(params: {
  snapshot: ClassroomPlannerGuestSnapshot;
  expectedRevision: number;
  clientOperationId: string;
  revokeSecret: string;
  previousPublicPath: string | null;
  previousRevokeSecret: string | null;
}): Promise<CreatedPublicGuestShare> {
  return await publicApiPost<CreatedPublicGuestShare>(
    "/api/v1/public/apps/classroom.group-seating-studio/grouping/share",
    buildPublicGuestShareRequest(params),
  );
}

export async function createPublicSeatingShare(params: {
  snapshot: ClassroomPlannerGuestSnapshot;
  expectedRevision: number;
  clientOperationId: string;
  revokeSecret: string;
  previousPublicPath: string | null;
  previousRevokeSecret: string | null;
}): Promise<CreatedPublicGuestShare> {
  return await publicApiPost<CreatedPublicGuestShare>(
    "/api/v1/public/apps/classroom.group-seating-studio/seating/share",
    buildPublicGuestShareRequest(params),
  );
}

export async function revokePublicGuestShare(params: {
  publicPath: string;
  revokeSecret: string;
}): Promise<RevokedPublicGuestShare> {
  return await publicApiPost<RevokedPublicGuestShare>(
    "/api/v1/public/apps/classroom.group-seating-studio/share/revoke",
    {
      public_path: params.publicPath,
      revoke_secret: params.revokeSecret,
    } satisfies PublicGuestShareRevokeRequest,
  );
}

function buildPublicGuestShareRequest(params: {
  snapshot: ClassroomPlannerGuestSnapshot;
  expectedRevision: number;
  clientOperationId: string;
  revokeSecret: string;
  previousPublicPath: string | null;
  previousRevokeSecret: string | null;
}): PublicGuestShareRequest {
  return {
    snapshot: params.snapshot,
    expected_revision: params.expectedRevision,
    client_operation_id: params.clientOperationId,
    revoke_secret: params.revokeSecret,
    previous_public_path: params.previousPublicPath,
    previous_revoke_secret: params.previousRevokeSecret,
  };
}
