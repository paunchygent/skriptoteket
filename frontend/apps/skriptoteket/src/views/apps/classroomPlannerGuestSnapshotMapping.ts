/**
 * Klassrumskartan guest snapshot mapping seam.
 *
 * This module translates between current frontend planner entities and the
 * browser-owned guest snapshot contract so later authenticated import flows
 * can reuse one stable representation without leaking owner-scoped semantics
 * into public guest state.
 */

import type {
  DraftWorkspaceResponse,
  GroupAssignment,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  SeatAssignment,
} from "./classroomPlannerTypes";
import type {
  ClassroomPlannerGuestCheckpointDescriptor,
  ClassroomPlannerGuestDraft,
  ClassroomPlannerGuestPlannerInitialView,
  ClassroomPlannerGuestPlannerScreen,
  ClassroomPlannerGuestRoomTemplate,
  ClassroomPlannerGuestRoster,
  ClassroomPlannerGuestSmartRuleSet,
  ClassroomPlannerGuestSnapshot,
  ClassroomPlannerGuestUiState,
} from "./classroomPlannerGuestSnapshot";
import {
  createClassroomPlannerGuestContentHash,
  createClassroomPlannerGuestFingerprint,
} from "./classroomPlannerGuestFingerprint";

export type ClassroomPlannerGuestCheckpointSeed = {
  local_id: string;
  draft_kind: "grouping" | "seating";
  created_at: string;
  label: string | null;
  template_local_id: string | null;
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
};

export type ClassroomPlannerGuestSnapshotSeed = {
  snapshot_id: string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  rosters: Roster[];
  templates: RoomTemplate[];
  smart_rule_sets: RosterSmartRulesResponse[];
  grouping_draft: DraftWorkspaceResponse | null;
  seating_draft: DraftWorkspaceResponse | null;
  checkpoint_descriptors: ClassroomPlannerGuestCheckpointSeed[];
  ui_state: {
    selected_roster_id: string | null;
    selected_template_id: string | null;
    current_screen: ClassroomPlannerGuestPlannerScreen;
    planner_initial_view: ClassroomPlannerGuestPlannerInitialView;
    dismissed_grouping_draft_id: string | null;
    dismissed_seating_draft_id: string | null;
  };
};

export type ClassroomPlannerGuestHydratedWorkspace = {
  rosters: Roster[];
  templates: RoomTemplate[];
  smart_rule_sets: RosterSmartRulesResponse[];
  grouping_draft: DraftWorkspaceResponse | null;
  seating_draft: DraftWorkspaceResponse | null;
  checkpoint_descriptors: ClassroomPlannerGuestCheckpointDescriptor[];
  ui_state: {
    selected_roster_id: string | null;
    selected_template_id: string | null;
    current_screen: ClassroomPlannerGuestPlannerScreen;
    planner_initial_view: ClassroomPlannerGuestPlannerInitialView;
    dismissed_grouping_draft_id: string | null;
    dismissed_seating_draft_id: string | null;
  };
};

export function mapRosterToGuestSnapshot(roster: Roster): ClassroomPlannerGuestRoster {
  const students = roster.students.map((student) => ({
    local_id: student.id,
    display_name: student.display_name,
  }));
  return {
    local_id: roster.id,
    name: roster.name,
    students,
    fingerprint: createClassroomPlannerGuestFingerprint({
      name: roster.name,
      students,
    }),
  };
}

export function mapTemplateToGuestSnapshot(template: RoomTemplate): ClassroomPlannerGuestRoomTemplate {
  return {
    local_id: template.id,
    name: template.name,
    grid_cols: template.grid_cols ?? null,
    grid_rows: template.grid_rows ?? null,
    seats: template.seats,
    fixtures: template.fixtures,
    fingerprint: createClassroomPlannerGuestFingerprint({
      name: template.name,
      grid_cols: template.grid_cols ?? null,
      grid_rows: template.grid_rows ?? null,
      seats: template.seats,
      fixtures: template.fixtures,
    }),
  };
}

export function mapSmartRulesToGuestSnapshot(
  smartRules: RosterSmartRulesResponse,
): ClassroomPlannerGuestSmartRuleSet {
  return {
    roster_local_id: smartRules.roster_id,
    revision: smartRules.revision,
    seating_preferences: smartRules.seating_preferences,
    relationship_rules: smartRules.relationship_rules,
    fingerprint: createClassroomPlannerGuestFingerprint({
      seating_preferences: smartRules.seating_preferences,
      relationship_rules: smartRules.relationship_rules,
    }),
  };
}

export function mapDraftWorkspaceToGuestSnapshot(
  workspace: DraftWorkspaceResponse,
): ClassroomPlannerGuestDraft {
  return {
    local_id: workspace.draft.id,
    draft_kind: workspace.draft.draft_kind,
    roster_local_id: workspace.roster.id,
    template_local_id: workspace.template?.id ?? null,
    task_entry_classroom_selection_mode:
      workspace.draft.task_entry_classroom_selection_mode ??
      (workspace.template ? "optional" : "required"),
    smart_enabled: workspace.draft.smart_enabled ?? false,
    use_history: workspace.draft.use_history ?? false,
    grouping_seating_distance_enabled:
      workspace.draft.grouping_seating_distance_enabled ?? false,
    revision: workspace.draft.revision,
    last_opened_at: workspace.draft.last_opened_at,
    groups: workspace.groups,
    group_assignments: workspace.group_assignments,
    seat_assignments: workspace.seat_assignments,
    fingerprint: createClassroomPlannerGuestFingerprint({
      draft_kind: workspace.draft.draft_kind,
      roster_local_id: workspace.roster.id,
      template_local_id: workspace.template?.id ?? null,
      smart_enabled: workspace.draft.smart_enabled ?? false,
      use_history: workspace.draft.use_history ?? false,
      grouping_seating_distance_enabled:
        workspace.draft.grouping_seating_distance_enabled ?? false,
      groups: workspace.groups,
      group_assignments: workspace.group_assignments,
      seat_assignments: workspace.seat_assignments,
    }),
  };
}

export function mapUiStateToGuestSnapshot(input: {
  selected_roster_id: string | null;
  selected_template_id: string | null;
  current_screen: ClassroomPlannerGuestPlannerScreen;
  planner_initial_view: ClassroomPlannerGuestPlannerInitialView;
  dismissed_grouping_draft_id: string | null;
  dismissed_seating_draft_id: string | null;
}): ClassroomPlannerGuestUiState {
  return {
    selected_roster_local_id: input.selected_roster_id,
    selected_template_local_id: input.selected_template_id,
    current_screen: input.current_screen,
    planner_initial_view: input.planner_initial_view,
    dismissed_grouping_draft_local_id: input.dismissed_grouping_draft_id,
    dismissed_seating_draft_local_id: input.dismissed_seating_draft_id,
    fingerprint: createClassroomPlannerGuestFingerprint(input),
  };
}

export function createClassroomPlannerGuestSnapshotFromSeed(
  seed: ClassroomPlannerGuestSnapshotSeed,
): ClassroomPlannerGuestSnapshot {
  const snapshot = {
    schema_version: 1 as const,
    profile: "public_browser_workspace_with_upgrade" as const,
    snapshot_id: seed.snapshot_id,
    created_at: seed.created_at,
    updated_at: seed.updated_at,
    expires_at: seed.expires_at,
    rosters: seed.rosters.map(mapRosterToGuestSnapshot),
    templates: seed.templates.map(mapTemplateToGuestSnapshot),
    smart_rule_sets: seed.smart_rule_sets.map(mapSmartRulesToGuestSnapshot),
    grouping_draft: seed.grouping_draft ? mapDraftWorkspaceToGuestSnapshot(seed.grouping_draft) : null,
    seating_draft: seed.seating_draft ? mapDraftWorkspaceToGuestSnapshot(seed.seating_draft) : null,
    checkpoint_descriptors: seed.checkpoint_descriptors.map((checkpoint) => ({
      local_id: checkpoint.local_id,
      draft_kind: checkpoint.draft_kind,
      created_at: checkpoint.created_at,
      label: checkpoint.label,
      source: "export" as const,
      template_local_id: checkpoint.template_local_id,
      group_assignments: checkpoint.group_assignments,
      seat_assignments: checkpoint.seat_assignments,
      fingerprint: createClassroomPlannerGuestFingerprint(checkpoint),
    })),
    ui_state: mapUiStateToGuestSnapshot(seed.ui_state),
  };

  return {
    ...snapshot,
    snapshot_content_hash: createClassroomPlannerGuestContentHash(snapshot),
  };
}

export function hydrateGuestSnapshot(
  snapshot: ClassroomPlannerGuestSnapshot,
): ClassroomPlannerGuestHydratedWorkspace {
  return {
    rosters: snapshot.rosters.map((roster) => ({
      id: roster.local_id,
      name: roster.name,
      students: roster.students.map((student) => ({
        id: student.local_id,
        display_name: student.display_name,
      })),
    })),
    templates: snapshot.templates.map((template) => ({
      id: template.local_id,
      name: template.name,
      grid_cols: template.grid_cols ?? undefined,
      grid_rows: template.grid_rows ?? undefined,
      seats: template.seats,
      fixtures: template.fixtures,
    })),
    smart_rule_sets: snapshot.smart_rule_sets.map((smartRules) => ({
      roster_id: smartRules.roster_local_id,
      revision: smartRules.revision,
      seating_preferences: smartRules.seating_preferences,
      relationship_rules: smartRules.relationship_rules,
    })),
    grouping_draft: hydrateGuestDraft(snapshot.grouping_draft, snapshot),
    seating_draft: hydrateGuestDraft(snapshot.seating_draft, snapshot),
    checkpoint_descriptors: snapshot.checkpoint_descriptors,
    ui_state: {
      selected_roster_id: snapshot.ui_state.selected_roster_local_id,
      selected_template_id: snapshot.ui_state.selected_template_local_id,
      current_screen: snapshot.ui_state.current_screen,
      planner_initial_view: snapshot.ui_state.planner_initial_view,
      dismissed_grouping_draft_id: snapshot.ui_state.dismissed_grouping_draft_local_id,
      dismissed_seating_draft_id: snapshot.ui_state.dismissed_seating_draft_local_id,
    },
  };
}

function hydrateGuestDraft(
  draft: ClassroomPlannerGuestDraft | null,
  snapshot: ClassroomPlannerGuestSnapshot,
): DraftWorkspaceResponse | null {
  if (!draft) {
    return null;
  }

  const roster = snapshot.rosters.find((entry) => entry.local_id === draft.roster_local_id);
  if (!roster) {
    return null;
  }
  const template = draft.template_local_id
    ? (snapshot.templates.find((entry) => entry.local_id === draft.template_local_id) ?? null)
    : null;

  return {
    draft: {
      id: draft.local_id,
      roster_id: draft.roster_local_id,
      draft_kind: draft.draft_kind,
      template_id: draft.template_local_id,
      task_entry_classroom_selection_mode: draft.task_entry_classroom_selection_mode,
      smart_enabled: draft.smart_enabled,
      use_history: draft.use_history,
      grouping_seating_distance_enabled: draft.grouping_seating_distance_enabled,
      status: "active",
      revision: draft.revision,
      last_opened_at: draft.last_opened_at,
    },
    roster: {
      id: roster.local_id,
      name: roster.name,
      students: roster.students.map((student) => ({
        id: student.local_id,
        display_name: student.display_name,
      })),
    },
    template: template
      ? {
          id: template.local_id,
          name: template.name,
          grid_cols: template.grid_cols ?? undefined,
          grid_rows: template.grid_rows ?? undefined,
          seats: template.seats,
          fixtures: template.fixtures,
        }
      : null,
    groups: draft.groups,
    group_assignments: draft.group_assignments,
    seat_assignments: draft.seat_assignments,
    history_status: {
      can_undo: false,
      can_redo: false,
    },
  };
}
