/**
 * Classroom planner guest controller support helpers.
 *
 * This module keeps the public guest controller small by owning pure
 * snapshot-hydration, overview-selection normalization, and checkpoint-2
 * capability constants. It has no modal or storage side effects.
 */

import type { ClassroomPlannerOverviewCapabilities } from "./classroomPlannerOverviewCapabilities";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import {
  hydrateGuestSnapshot,
  replaceGuestSnapshotUiState,
} from "./classroomPlannerGuestSnapshotMapping";
import type {
  ClassWorkspaceSummary,
  RoomTemplate,
  Roster,
  Student,
} from "./classroomPlannerTypes";

export const PUBLIC_ROSTER_IMPORT_PREVIEW_API_PATH =
  "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview";
export const PUBLIC_GROUPING_SMART_RUN_API_PATH =
  "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run";
export const PUBLIC_SEATING_SMART_RUN_API_PATH =
  "/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run";

export const CHECKPOINT_TWO_OVERVIEW_CAPABILITIES: ClassroomPlannerOverviewCapabilities = {
  show_grouping_option: false,
  show_seating_option: false,
  show_rules_option: false,
  show_roster_actions: true,
  show_template_actions: true,
};

export const CHECKPOINT_THREE_OVERVIEW_CAPABILITIES: ClassroomPlannerOverviewCapabilities = {
  show_grouping_option: true,
  show_seating_option: true,
  show_rules_option: true,
  show_roster_actions: true,
  show_template_actions: true,
};

export type SaveGuestRosterPayload = {
  existingRoster: Roster | null;
  name: string;
  students: Student[];
};

export type SaveGuestTemplatePayload = {
  existingTemplate: RoomTemplate | null;
  name: string;
  grid_cols: number;
  grid_rows: number;
  seats: RoomTemplate["seats"];
  fixtures: RoomTemplate["fixtures"];
};

export type HydratedGuestOverviewState = {
  rosters: Roster[];
  templates: RoomTemplate[];
  normalizedSelectedRosterId: string | null;
  normalizedSelectedTemplateId: string | null;
};

export function buildWorkspaceSummary(selectedRoster: Roster | null): ClassWorkspaceSummary | null {
  if (!selectedRoster) {
    return null;
  }

  return {
    roster: {
      id: selectedRoster.id,
      name: selectedRoster.name,
      student_count: selectedRoster.students.length,
    },
    task_entry_options: [],
    active_grouping_draft: null,
    active_seating_draft: null,
    grouping_history: [],
    seating_history: [],
  };
}

export function resolveExistingId<T extends { id: string }>(
  preferredId: string | null,
  entries: T[],
): string | null {
  if (preferredId && entries.some((entry) => entry.id === preferredId)) {
    return preferredId;
  }

  return entries[0]?.id ?? null;
}

export function sortEntriesByName<T extends { name: string }>(entries: T[]): T[] {
  return [...entries].sort((left, right) => left.name.localeCompare(right.name, "sv"));
}

export function buildOverviewUiState(input: {
  selectedRosterId: string | null;
  selectedTemplateId: string | null;
  updatedAt: string;
  currentScreen?: "class-workspace" | "planner";
  plannerInitialView?: "groups" | "seats" | "rules";
  dismissedGroupingDraftId?: string | null;
  dismissedSeatingDraftId?: string | null;
}) {
  return {
    selected_roster_id: input.selectedRosterId,
    selected_template_id: input.selectedTemplateId,
    current_screen: input.currentScreen ?? ("class-workspace" as const),
    planner_initial_view: input.plannerInitialView ?? ("groups" as const),
    dismissed_grouping_draft_id: input.dismissedGroupingDraftId ?? null,
    dismissed_seating_draft_id: input.dismissedSeatingDraftId ?? null,
    updated_at: input.updatedAt,
  };
}

export function hydrateGuestOverviewSnapshot(
  snapshot: ClassroomPlannerGuestSnapshot,
  options?: {
    preserveExplicitTemplateNull?: boolean;
  },
): HydratedGuestOverviewState {
  const hydratedSnapshot = hydrateGuestSnapshot(snapshot);
  const normalizedSelectedRosterId = resolveExistingId(
    hydratedSnapshot.ui_state.selected_roster_id,
    hydratedSnapshot.rosters,
  );
  const normalizedSelectedTemplateId =
    options?.preserveExplicitTemplateNull && hydratedSnapshot.ui_state.selected_template_id === null
      ? null
      : resolveExistingId(
          hydratedSnapshot.ui_state.selected_template_id,
          hydratedSnapshot.templates,
        );

  return {
    rosters: sortEntriesByName(hydratedSnapshot.rosters),
    templates: sortEntriesByName(hydratedSnapshot.templates),
    normalizedSelectedRosterId,
    normalizedSelectedTemplateId,
  };
}

export function normalizeOverviewSnapshotUiState(
  snapshot: ClassroomPlannerGuestSnapshot,
  input: {
    preferredRosterId: string | null;
    preferredTemplateId: string | null;
    updatedAt: string;
    preserveExplicitTemplateNull?: boolean;
    currentScreen?: "class-workspace" | "planner";
    plannerInitialView?: "groups" | "seats" | "rules";
    dismissedGroupingDraftId?: string | null;
    dismissedSeatingDraftId?: string | null;
  },
): ClassroomPlannerGuestSnapshot {
  const hydratedOverviewState = hydrateGuestOverviewSnapshot(snapshot, {
    preserveExplicitTemplateNull: input.preserveExplicitTemplateNull,
  });
  const normalizedSelectedRosterId = resolveExistingId(
    input.preferredRosterId,
    hydratedOverviewState.rosters,
  );
  const normalizedSelectedTemplateId =
    input.preserveExplicitTemplateNull && input.preferredTemplateId === null
      ? null
      : resolveExistingId(
          input.preferredTemplateId,
          hydratedOverviewState.templates,
        );
  const nextUiState = buildOverviewUiState({
    selectedRosterId: normalizedSelectedRosterId,
    selectedTemplateId: normalizedSelectedTemplateId,
    updatedAt: input.updatedAt,
    currentScreen: input.currentScreen ?? snapshot.ui_state.current_screen,
    plannerInitialView: input.plannerInitialView ?? snapshot.ui_state.planner_initial_view,
    dismissedGroupingDraftId:
      input.dismissedGroupingDraftId ?? snapshot.ui_state.dismissed_grouping_draft_local_id,
    dismissedSeatingDraftId:
      input.dismissedSeatingDraftId ?? snapshot.ui_state.dismissed_seating_draft_local_id,
  });

  const needsNormalization =
    snapshot.ui_state.selected_roster_local_id !== nextUiState.selected_roster_id
    || snapshot.ui_state.selected_template_local_id !== nextUiState.selected_template_id
    || snapshot.ui_state.current_screen !== nextUiState.current_screen
    || snapshot.ui_state.planner_initial_view !== nextUiState.planner_initial_view
    || snapshot.ui_state.dismissed_grouping_draft_local_id !== nextUiState.dismissed_grouping_draft_id
    || snapshot.ui_state.dismissed_seating_draft_local_id !== nextUiState.dismissed_seating_draft_id;

  if (!needsNormalization) {
    return snapshot;
  }

  return replaceGuestSnapshotUiState(snapshot, nextUiState);
}
