/**
 * Klassrumskartan guest-upgrade outcome helpers.
 *
 * This module keeps the authenticated guest-upgrade gate and entry shell
 * aligned on what counts as meaningful browser-owned guest content and what
 * counts as a real import outcome worth surfacing to the teacher.
 */

import type { ClassroomPlannerGuestUpgradeReceipt } from "./classroomPlannerGuestUpgradeApi";
import type { ClassroomPlannerGuestSnapshotSummary } from "./classroomPlannerGuestSnapshot";

export function hasClassroomPlannerGuestSnapshotSummaryContent(
  summary: ClassroomPlannerGuestSnapshotSummary | null,
): boolean {
  if (!summary) {
    return false;
  }

  return (
    summary.roster_count > 0
    || summary.template_count > 0
    || summary.smart_rule_set_count > 0
    || summary.checkpoint_count > 0
    || summary.has_grouping_draft
    || summary.has_seating_draft
  );
}

export function hasClassroomPlannerGuestUpgradeReceiptEffects(
  receipt: ClassroomPlannerGuestUpgradeReceipt | null,
): boolean {
  if (!receipt) {
    return false;
  }

  return (
    receipt.created.length > 0
    || receipt.reused.length > 0
    || receipt.skipped.length > 0
    || receipt.conflicted.length > 0
  );
}
