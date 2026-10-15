/**
 * Classroom planner profile settings API client.
 *
 * Purpose:
 *   Own the wire call that updates the signed-in teacher's classroom planner
 *   settings on the profile: Smart preferences and the tutorial seen-sections
 *   list. The endpoint replaces each field the request carries and leaves the
 *   others unchanged.
 *
 * Relationships:
 *   - used by `views/apps/useClassroomPlannerSmartPreferenceLane.ts`
 *   - used by `components/help/tutorial/useTutorialSeenSections.ts`
 *   - request and response types come from the generated `openapi.d.ts`
 */

import { apiPatch } from "./client";
import type { components } from "./openapi";

const CLASSROOM_PLANNER_SETTINGS_PATH = "/api/v1/profile/classroom-planner-settings";

export type UpdateClassroomPlannerSettingsRequest =
  components["schemas"]["UpdateClassroomPlannerSettingsRequest"];

export type ClassroomPlannerSettingsResponse = components["schemas"]["ProfileResponse"];

export async function updateClassroomPlannerSettings(
  request: UpdateClassroomPlannerSettingsRequest,
): Promise<ClassroomPlannerSettingsResponse> {
  return await apiPatch<ClassroomPlannerSettingsResponse>(
    CLASSROOM_PLANNER_SETTINGS_PATH,
    request,
  );
}
