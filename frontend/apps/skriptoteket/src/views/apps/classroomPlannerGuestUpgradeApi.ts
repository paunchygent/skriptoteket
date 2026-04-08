/**
 * Klassrumskartan authenticated guest-upgrade API helper.
 *
 * This module keeps the authenticated guest-upgrade HTTP contract in one small
 * place so UI composables can trigger preview and commit without duplicating
 * request or receipt typing.
 */

import { apiGet, apiPost } from "../../api/client";

import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { PlanDraftKind } from "./classroomPlannerTypes";

export type ClassroomPlannerGuestUpgradeMode = "preview" | "commit";

export type ClassroomPlannerGuestUpgradeReceiptItem = {
  entity_type: "roster" | "template" | "smart_rule_set" | "draft" | "checkpoint";
  local_id: string;
  draft_kind?: PlanDraftKind | null;
  target_id?: string | null;
  target_name?: string | null;
  message?: string | null;
};

export type ClassroomPlannerGuestUpgradeReceipt = {
  mode: ClassroomPlannerGuestUpgradeMode;
  snapshot_id: string;
  schema_version: number;
  submitted_snapshot_content_hash: string;
  server_snapshot_content_hash: string;
  created: ClassroomPlannerGuestUpgradeReceiptItem[];
  reused: ClassroomPlannerGuestUpgradeReceiptItem[];
  skipped: ClassroomPlannerGuestUpgradeReceiptItem[];
  conflicted: ClassroomPlannerGuestUpgradeReceiptItem[];
};

export type ClassroomPlannerGuestUpgradeConsumptionStatus = {
  consumed: boolean;
};

export async function runClassroomPlannerGuestUpgrade(args: {
  mode: ClassroomPlannerGuestUpgradeMode;
  snapshot: ClassroomPlannerGuestSnapshot;
}): Promise<ClassroomPlannerGuestUpgradeReceipt> {
  return await apiPost<ClassroomPlannerGuestUpgradeReceipt>(
    "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
    {
      mode: args.mode,
      snapshot: args.snapshot,
    },
  );
}

export async function getClassroomPlannerGuestUpgradeConsumptionStatus():
Promise<ClassroomPlannerGuestUpgradeConsumptionStatus> {
  return await apiGet<ClassroomPlannerGuestUpgradeConsumptionStatus>(
    "/api/v1/apps/classroom.group-seating-studio/guest-upgrade/consumption",
  );
}
