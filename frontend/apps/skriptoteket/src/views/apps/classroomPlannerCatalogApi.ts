/**
 * Classroom planner catalog transport helpers.
 *
 * This module centralizes the overview-side roster and classroom catalog calls
 * used by Klassrumskartan's route shell so the root view does not make direct
 * catalog transport requests.
 */

import { apiDelete, apiGet } from "../../api/client";
import type { RoomTemplate, Roster } from "./classroomPlannerTypes";

const CLASSROOM_PLANNER_API_PREFIX = "/api/v1/apps/classroom.group-seating-studio";

export async function fetchClassroomPlannerCatalog(): Promise<{
  rosters: Roster[];
  templates: RoomTemplate[];
}> {
  const [rosters, templates] = await Promise.all([
    apiGet<Roster[]>(`${CLASSROOM_PLANNER_API_PREFIX}/rosters`),
    apiGet<RoomTemplate[]>(`${CLASSROOM_PLANNER_API_PREFIX}/templates`),
  ]);

  return { rosters, templates };
}

export async function deleteClassroomPlannerRoster(rosterId: string): Promise<void> {
  await apiDelete<void>(`${CLASSROOM_PLANNER_API_PREFIX}/rosters/${rosterId}`);
}

export async function deleteClassroomPlannerTemplate(templateId: string): Promise<void> {
  await apiDelete<void>(`${CLASSROOM_PLANNER_API_PREFIX}/templates/${templateId}`);
}
