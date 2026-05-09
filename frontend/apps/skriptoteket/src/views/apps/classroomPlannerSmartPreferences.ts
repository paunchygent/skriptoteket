/**
 * Classroom planner Smart preferences and draft fallback values.
 *
 * Purpose:
 *   Keeps authenticated profile-backed Smart preferences and public
 *   browser-owned preferences aligned with the draft-local Smart flags used by
 *   seating and grouping workspaces.
 *
 * Relationships:
 *   - read by planner draft persistence, Smart run routing, and workspace
 *     toolbar controls
 *   - writes authenticated preferences through the profile API
 *   - stores public guest preferences in browser storage only
 */

import { apiPatch } from "../../api/client";
import type { components } from "../../api/openapi";
import type { PlanDraft } from "./classroomPlannerTypes";

export const SMART_DISABLED_NOTICE =
  "Smart är avstängt. När du slumpar tas ingen hänsyn till regler, fasta platser, nära läraren eller ihop/isär.";

export type ClassroomPlannerSmartPreferenceKey =
  | "smart_enabled"
  | "use_history"
  | "grouping_seating_distance_enabled";

export type ClassroomPlannerSmartPreferencePatch = Partial<
  Record<ClassroomPlannerSmartPreferenceKey, boolean>
>;

type ProfileResponse = components["schemas"]["ProfileResponse"];
type UpdateClassroomPlannerSettingsRequest =
  components["schemas"]["UpdateClassroomPlannerSettingsRequest"];

const FIRST_TIME_DRAFT_SMART_SETTINGS: Required<ClassroomPlannerSmartPreferencePatch> = {
  smart_enabled: true,
  use_history: true,
  grouping_seating_distance_enabled: false,
};

const FIRST_TIME_GUEST_SMART_SETTINGS: Required<ClassroomPlannerSmartPreferencePatch> = {
  smart_enabled: true,
  use_history: false,
  grouping_seating_distance_enabled: false,
};

const GUEST_SMART_PREFERENCE_STORAGE_KEY =
  "skriptoteket:classroom-planner:smart-preferences:guest:v1";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readGuestSmartPreferenceStorage(): ClassroomPlannerSmartPreferencePatch {
  if (typeof window === "undefined") {
    return {};
  }
  const raw = window.localStorage.getItem(GUEST_SMART_PREFERENCE_STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw);
    if (!isRecord(parsed)) {
      return {};
    }
    const preferences: ClassroomPlannerSmartPreferencePatch = {};
    if (typeof parsed.smart_enabled === "boolean") {
      preferences.smart_enabled = parsed.smart_enabled;
    }
    if (typeof parsed.use_history === "boolean") {
      preferences.use_history = parsed.use_history;
    }
    if (typeof parsed.grouping_seating_distance_enabled === "boolean") {
      preferences.grouping_seating_distance_enabled =
        parsed.grouping_seating_distance_enabled;
    }
    return preferences;
  } catch {
    return {};
  }
}

export function resolveGuestDraftSmartPreferences(): Required<ClassroomPlannerSmartPreferencePatch> {
  return {
    ...FIRST_TIME_GUEST_SMART_SETTINGS,
    ...readGuestSmartPreferenceStorage(),
  };
}

export function rememberGuestSmartPreference(
  key: ClassroomPlannerSmartPreferenceKey,
  enabled: boolean,
): void {
  if (typeof window === "undefined") {
    return;
  }
  const next = {
    ...readGuestSmartPreferenceStorage(),
    [key]: enabled,
  };
  window.localStorage.setItem(GUEST_SMART_PREFERENCE_STORAGE_KEY, JSON.stringify(next));
}

export async function persistAuthenticatedClassroomPlannerSmartPreference(
  patch: ClassroomPlannerSmartPreferencePatch,
): Promise<ProfileResponse> {
  return await apiPatch<ProfileResponse>(
    "/api/v1/profile/classroom-planner-settings",
    patch satisfies UpdateClassroomPlannerSettingsRequest,
  );
}

export function isSmartEnabledByDefault(
  draft: Pick<PlanDraft, "smart_enabled"> | null | undefined,
): boolean {
  return draft?.smart_enabled ?? FIRST_TIME_DRAFT_SMART_SETTINGS.smart_enabled;
}

export function isHistoryEnabledByDefault(
  draft: Pick<PlanDraft, "use_history"> | null | undefined,
): boolean {
  return draft?.use_history ?? FIRST_TIME_DRAFT_SMART_SETTINGS.use_history;
}

export function isGroupingSeatingDistanceEnabledByDefault(
  draft: Pick<PlanDraft, "grouping_seating_distance_enabled"> | null | undefined,
): boolean {
  return (
    draft?.grouping_seating_distance_enabled
    ?? FIRST_TIME_DRAFT_SMART_SETTINGS.grouping_seating_distance_enabled
  );
}
