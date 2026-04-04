/**
 * Klassrumskartan guest snapshot contract.
 *
 * This module defines the browser-owned public guest workspace snapshot for
 * Klassrumskartan, including schema versioning, profile semantics, TTL rules,
 * and the durable partitions that later authenticated upgrade flows will
 * translate into backend-owned assets.
 */

import type {
  ClassroomSelectionMode,
  DraftGroup,
  GroupAssignment,
  PlanDraftKind,
  RelationshipRule,
  RoomFixture,
  Seat,
  SeatAssignment,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import {
  createClassroomPlannerGuestContentHash,
  createClassroomPlannerGuestFingerprint,
} from "./classroomPlannerGuestFingerprint";

export const CLASSROOM_PLANNER_GUEST_SNAPSHOT_SCHEMA_VERSION = 1;
export const CLASSROOM_PLANNER_GUEST_SNAPSHOT_TTL_DAYS = 14;
export const CLASSROOM_PLANNER_GUEST_SNAPSHOT_STORAGE_PROFILE =
  "public_browser_workspace_with_upgrade" as const;

export type ClassroomPlannerGuestStorageProfile =
  | "public_stateless"
  | "public_browser_runtime"
  | "public_browser_workspace_with_upgrade";

export type ClassroomPlannerGuestStorageContract = {
  authority: "request" | "browser";
  durable_browser_workspace: boolean;
  supports_authenticated_upgrade: boolean;
};

export type ClassroomPlannerGuestPlannerScreen = "class-workspace" | "planner";
export type ClassroomPlannerGuestPlannerInitialView = "groups" | "seats" | "rules";

export type ClassroomPlannerGuestStudent = {
  local_id: string;
  display_name: string;
};

export type ClassroomPlannerGuestRoster = {
  local_id: string;
  name: string;
  students: ClassroomPlannerGuestStudent[];
  fingerprint: string;
};

export type ClassroomPlannerGuestRoomTemplate = {
  local_id: string;
  name: string;
  grid_cols: number | null;
  grid_rows: number | null;
  seats: Seat[];
  fixtures: RoomFixture[];
  fingerprint: string;
};

export type ClassroomPlannerGuestSmartRuleSet = {
  roster_local_id: string;
  revision: number;
  seating_preferences: StudentSeatingPreference[];
  relationship_rules: RelationshipRule[];
  fingerprint: string;
};

export type ClassroomPlannerGuestDraft = {
  local_id: string;
  draft_kind: PlanDraftKind;
  roster_local_id: string;
  template_local_id: string | null;
  task_entry_classroom_selection_mode: ClassroomSelectionMode;
  smart_enabled: boolean;
  use_history: boolean;
  grouping_seating_distance_enabled: boolean;
  revision: number;
  last_opened_at: string;
  groups: DraftGroup[];
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
  fingerprint: string;
};

export type ClassroomPlannerGuestCheckpointDescriptor = {
  local_id: string;
  draft_kind: PlanDraftKind;
  created_at: string;
  label: string | null;
  source: "export";
  template_local_id: string | null;
  group_assignments: GroupAssignment[];
  seat_assignments: SeatAssignment[];
  fingerprint: string;
};

export type ClassroomPlannerGuestUiState = {
  selected_roster_local_id: string | null;
  selected_template_local_id: string | null;
  current_screen: ClassroomPlannerGuestPlannerScreen;
  planner_initial_view: ClassroomPlannerGuestPlannerInitialView;
  dismissed_grouping_draft_local_id: string | null;
  dismissed_seating_draft_local_id: string | null;
  fingerprint: string;
};

export type ClassroomPlannerGuestSnapshot = {
  schema_version: typeof CLASSROOM_PLANNER_GUEST_SNAPSHOT_SCHEMA_VERSION;
  profile: typeof CLASSROOM_PLANNER_GUEST_SNAPSHOT_STORAGE_PROFILE;
  snapshot_id: string;
  snapshot_content_hash: string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  rosters: ClassroomPlannerGuestRoster[];
  templates: ClassroomPlannerGuestRoomTemplate[];
  smart_rule_sets: ClassroomPlannerGuestSmartRuleSet[];
  grouping_draft: ClassroomPlannerGuestDraft | null;
  seating_draft: ClassroomPlannerGuestDraft | null;
  checkpoint_descriptors: ClassroomPlannerGuestCheckpointDescriptor[];
  ui_state: ClassroomPlannerGuestUiState;
};

export type ClassroomPlannerGuestSnapshotSummary = {
  snapshot_id: string;
  profile: ClassroomPlannerGuestStorageProfile;
  created_at: string;
  updated_at: string;
  expires_at: string;
  roster_count: number;
  template_count: number;
  smart_rule_set_count: number;
  checkpoint_count: number;
  has_grouping_draft: boolean;
  has_seating_draft: boolean;
};

export type ClassroomPlannerGuestSnapshotLoadResult =
  | {
      status: "missing";
      snapshot: null;
      summary: null;
    }
  | {
      status: "ready";
      snapshot: ClassroomPlannerGuestSnapshot;
      summary: ClassroomPlannerGuestSnapshotSummary;
    }
  | {
      status: "expired";
      snapshot: null;
      summary: ClassroomPlannerGuestSnapshotSummary;
    };

export function resolveClassroomPlannerGuestStorageContract(
  profile: ClassroomPlannerGuestStorageProfile,
): ClassroomPlannerGuestStorageContract {
  switch (profile) {
    case "public_stateless":
      return {
        authority: "request",
        durable_browser_workspace: false,
        supports_authenticated_upgrade: false,
      };
    case "public_browser_runtime":
      return {
        authority: "browser",
        durable_browser_workspace: true,
        supports_authenticated_upgrade: false,
      };
    case "public_browser_workspace_with_upgrade":
      return {
        authority: "browser",
        durable_browser_workspace: true,
        supports_authenticated_upgrade: true,
      };
  }
}

export function createEmptyClassroomPlannerGuestSnapshot(args: {
  snapshotId: string;
  nowIso: string;
  expiresAtIso: string;
}): ClassroomPlannerGuestSnapshot {
  const snapshotWithoutHash = {
    schema_version: CLASSROOM_PLANNER_GUEST_SNAPSHOT_SCHEMA_VERSION,
    profile: CLASSROOM_PLANNER_GUEST_SNAPSHOT_STORAGE_PROFILE,
    snapshot_id: args.snapshotId,
    created_at: args.nowIso,
    updated_at: args.nowIso,
    expires_at: args.expiresAtIso,
    rosters: [],
    templates: [],
    smart_rule_sets: [],
    grouping_draft: null,
    seating_draft: null,
    checkpoint_descriptors: [],
    ui_state: {
      selected_roster_local_id: null,
      selected_template_local_id: null,
      current_screen: "class-workspace" as const,
      planner_initial_view: "groups" as const,
      dismissed_grouping_draft_local_id: null,
      dismissed_seating_draft_local_id: null,
      fingerprint: createClassroomPlannerGuestFingerprint({
        selected_roster_local_id: null,
        selected_template_local_id: null,
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_local_id: null,
        dismissed_seating_draft_local_id: null,
      }),
    },
  };

  return {
    ...snapshotWithoutHash,
    schema_version: CLASSROOM_PLANNER_GUEST_SNAPSHOT_SCHEMA_VERSION,
    snapshot_content_hash: createClassroomPlannerGuestContentHash(snapshotWithoutHash),
  };
}

export function summarizeClassroomPlannerGuestSnapshot(
  snapshot: ClassroomPlannerGuestSnapshot,
): ClassroomPlannerGuestSnapshotSummary {
  return {
    snapshot_id: snapshot.snapshot_id,
    profile: snapshot.profile,
    created_at: snapshot.created_at,
    updated_at: snapshot.updated_at,
    expires_at: snapshot.expires_at,
    roster_count: snapshot.rosters.length,
    template_count: snapshot.templates.length,
    smart_rule_set_count: snapshot.smart_rule_sets.length,
    checkpoint_count: snapshot.checkpoint_descriptors.length,
    has_grouping_draft: snapshot.grouping_draft !== null,
    has_seating_draft: snapshot.seating_draft !== null,
  };
}
