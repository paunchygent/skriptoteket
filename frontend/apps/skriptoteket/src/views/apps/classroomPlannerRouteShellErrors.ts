/**
 * Classroom planner route-shell error helpers.
 *
 * This module keeps planner-shell UI error normalization in one place so the
 * extracted orchestration modules can share the same user-facing fallback
 * behavior.
 */

import { isApiError } from "../../api/client";

export function normalizeClassroomPlannerUiError(error: unknown, fallbackMessage: string): string {
  if (isApiError(error)) {
    return error.message || fallbackMessage;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}
