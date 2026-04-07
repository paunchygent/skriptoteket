/**
 * Classroom planner guest draft snapshot mutations.
 *
 * This module owns the pure browser-owned snapshot mutations and summary
 * builders needed for guest grouping/seating continuity. It keeps draft-local
 * persistence out of the guest controller so checkpoint-3 can extend the
 * public planner without growing the checkpoint-2 overview files into
 * multi-purpose state managers.
 */

import type {
  ClassWorkspaceSummary,
  DraftGroup,
  DraftWorkspaceResponse,
  GroupAssignment,
  PlanDraft,
  PlanDraftKind,
  PlanDraftSummary,
  RelationshipRule,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  SeatAssignment,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import type {
  ClassroomPlannerGuestCheckpointDescriptor,
  ClassroomPlannerGuestSnapshot,
} from "./classroomPlannerGuestSnapshot";
import {
  createClassroomPlannerGuestContentHash,
} from "./classroomPlannerGuestFingerprint";
import {
  hydrateGuestSnapshot,
  createClassroomPlannerGuestCheckpointFingerprint,
  mapDraftWorkspaceToGuestSnapshot,
  mapSmartRulesToGuestSnapshot,
  mapUiStateToGuestSnapshot,
} from "./classroomPlannerGuestSnapshotMapping";

function cloneDraftSummary(
  draft: DraftWorkspaceResponse["draft"],
  template: DraftWorkspaceResponse["template"],
): PlanDraftSummary {
  return {
    id: draft.id,
    draft_kind: draft.draft_kind,
    template_id: template?.id ?? null,
    template_name: template?.name ?? null,
    status: draft.status,
    revision: draft.revision,
    last_opened_at: draft.last_opened_at,
    updated_at: draft.last_opened_at,
  };
}

export function buildGuestWorkspaceSummary(
  snapshot: ClassroomPlannerGuestSnapshot,
  rosterId: string,
): ClassWorkspaceSummary {
  const hydrated = hydrateGuestSnapshot(snapshot);
  const roster = hydrated.rosters.find((entry) => entry.id === rosterId);
  if (!roster) {
    throw new Error("Det gick inte att hitta klassen i den publika arbetsytan.");
  }

  const groupingDraft = hydrated.grouping_draft?.roster.id === rosterId
    ? cloneDraftSummary(hydrated.grouping_draft.draft, hydrated.grouping_draft.template ?? null)
    : null;
  const seatingDraft = hydrated.seating_draft?.roster.id === rosterId
    ? cloneDraftSummary(hydrated.seating_draft.draft, hydrated.seating_draft.template ?? null)
    : null;

  return {
    roster: {
      id: roster.id,
      name: roster.name,
      student_count: roster.students.length,
    },
    task_entry_options: [],
    active_grouping_draft: groupingDraft,
    active_seating_draft: seatingDraft,
    grouping_history: [],
    seating_history: [],
  };
}

function cloneGroups(groups: DraftGroup[]): DraftGroup[] {
  return groups.map((group) => ({ ...group }));
}

function cloneGroupAssignments(assignments: GroupAssignment[]): GroupAssignment[] {
  return assignments.map((assignment) => ({ ...assignment }));
}

function cloneSeatAssignments(assignments: SeatAssignment[]): SeatAssignment[] {
  return assignments.map((assignment) => ({ ...assignment }));
}

export function buildGuestWorkspaceResponse(input: {
  draft: PlanDraft;
  roster: Roster;
  template: RoomTemplate | null;
  groups: DraftGroup[];
  groupAssignments: GroupAssignment[];
  seatAssignments: SeatAssignment[];
}): DraftWorkspaceResponse {
  return {
    draft: { ...input.draft },
    roster: {
      ...input.roster,
      students: input.roster.students.map((student) => ({ ...student })),
    },
    template: input.template
      ? {
          ...input.template,
          seats: input.template.seats.map((seat) => ({ ...seat })),
          fixtures: input.template.fixtures.map((fixture) => ({ ...fixture })),
        }
      : null,
    groups: cloneGroups(input.groups),
    group_assignments: cloneGroupAssignments(input.groupAssignments),
    seat_assignments: cloneSeatAssignments(input.seatAssignments),
    history_status: {
      can_undo: false,
      can_redo: false,
    },
  };
}

function cloneCheckpointDescriptors(
  descriptors: ClassroomPlannerGuestCheckpointDescriptor[],
): ClassroomPlannerGuestCheckpointDescriptor[] {
  return descriptors.map((descriptor) => ({
    ...descriptor,
    group_assignments: descriptor.group_assignments.map((assignment) => ({ ...assignment })),
    seat_assignments: descriptor.seat_assignments.map((assignment) => ({ ...assignment })),
  }));
}

function createGuestCheckpointLocalId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `guest-checkpoint-${Date.now()}`;
}

function resolveCheckpointWorkspace(input: {
  snapshot: ClassroomPlannerGuestSnapshot;
  draftKind: PlanDraftKind;
  draftId: string;
}): DraftWorkspaceResponse | null {
  const hydrated = hydrateGuestSnapshot(input.snapshot);
  const candidate = input.draftKind === "grouping"
    ? hydrated.grouping_draft
    : hydrated.seating_draft;
  if (!candidate || candidate.draft.id !== input.draftId) {
    return null;
  }
  return candidate;
}

function buildGuestExportCheckpointDescriptor(input: {
  workspace: DraftWorkspaceResponse;
  createdAt: string;
  label: string | null;
}): ClassroomPlannerGuestCheckpointDescriptor {
  return {
    local_id: createGuestCheckpointLocalId(),
    draft_kind: input.workspace.draft.draft_kind,
    created_at: input.createdAt,
    label: input.label,
    source: "export",
    template_local_id: input.workspace.template?.id ?? input.workspace.draft.template_id ?? null,
    group_assignments: cloneGroupAssignments(input.workspace.group_assignments),
    seat_assignments: cloneSeatAssignments(input.workspace.seat_assignments),
    fingerprint: createClassroomPlannerGuestCheckpointFingerprint({
      draft_kind: input.workspace.draft.draft_kind,
      template_local_id: input.workspace.template?.id ?? input.workspace.draft.template_id ?? null,
      group_assignments: input.workspace.group_assignments,
      seat_assignments: input.workspace.seat_assignments,
    }),
  };
}

export function replaceGuestSnapshotDraft(
  snapshot: ClassroomPlannerGuestSnapshot,
  workspace: DraftWorkspaceResponse,
  input: {
    updatedAt: string;
    currentScreen: "class-workspace" | "planner";
    plannerInitialView: "groups" | "seats" | "rules";
    selectedRosterId: string | null;
    selectedTemplateId: string | null;
    dismissedGroupingDraftId: string | null;
    dismissedSeatingDraftId: string | null;
  },
): ClassroomPlannerGuestSnapshot {
  const nextSnapshot = {
    ...snapshot,
    updated_at: input.updatedAt,
    grouping_draft: workspace.draft.draft_kind === "grouping"
      ? mapDraftWorkspaceToGuestSnapshot(workspace)
      : snapshot.grouping_draft,
    seating_draft: workspace.draft.draft_kind === "seating"
      ? mapDraftWorkspaceToGuestSnapshot(workspace)
      : snapshot.seating_draft,
    checkpoint_descriptors: cloneCheckpointDescriptors(snapshot.checkpoint_descriptors),
    ui_state: mapUiStateToGuestSnapshot({
      selected_roster_id: input.selectedRosterId,
      selected_template_id: input.selectedTemplateId,
      current_screen: input.currentScreen,
      planner_initial_view: input.plannerInitialView,
      dismissed_grouping_draft_id: input.dismissedGroupingDraftId,
      dismissed_seating_draft_id: input.dismissedSeatingDraftId,
    }),
  };

  return {
    ...nextSnapshot,
    snapshot_content_hash: createClassroomPlannerGuestContentHash(nextSnapshot),
  };
}

export function replaceGuestSnapshotSmartRules(
  snapshot: ClassroomPlannerGuestSnapshot,
  rules: RosterSmartRulesResponse,
  updatedAt: string,
): ClassroomPlannerGuestSnapshot {
  const nextRuleSet = mapSmartRulesToGuestSnapshot(rules);
  const nextSnapshot = {
    ...snapshot,
    updated_at: updatedAt,
    smart_rule_sets: [
      ...snapshot.smart_rule_sets.filter((entry) => entry.roster_local_id !== rules.roster_id),
      nextRuleSet,
    ],
    checkpoint_descriptors: cloneCheckpointDescriptors(snapshot.checkpoint_descriptors),
  };

  return {
    ...nextSnapshot,
    snapshot_content_hash: createClassroomPlannerGuestContentHash(nextSnapshot),
  };
}

export function appendGuestExportCheckpointDescriptor(
  snapshot: ClassroomPlannerGuestSnapshot,
  input: {
    draftKind: PlanDraftKind;
    draftId: string;
    updatedAt: string;
    label: string | null;
  },
): ClassroomPlannerGuestSnapshot {
  const workspace = resolveCheckpointWorkspace({
    snapshot,
    draftKind: input.draftKind,
    draftId: input.draftId,
  });
  if (!workspace) {
    return snapshot;
  }

  const descriptor = buildGuestExportCheckpointDescriptor({
    workspace,
    createdAt: input.updatedAt,
    label: input.label,
  });
  if (
    snapshot.checkpoint_descriptors.some((existing) => existing.fingerprint === descriptor.fingerprint)
  ) {
    return snapshot;
  }

  const nextSnapshot = {
    ...snapshot,
    updated_at: input.updatedAt,
    checkpoint_descriptors: [
      ...cloneCheckpointDescriptors(snapshot.checkpoint_descriptors),
      descriptor,
    ],
  };

  return {
    ...nextSnapshot,
    snapshot_content_hash: createClassroomPlannerGuestContentHash(nextSnapshot),
  };
}

export function resolveGuestExportCheckpointDescriptor(
  snapshot: ClassroomPlannerGuestSnapshot,
  input: {
    draftKind: PlanDraftKind;
    draftId: string;
    createdAt: string;
    label: string | null;
  },
): ClassroomPlannerGuestCheckpointDescriptor | null {
  const workspace = resolveCheckpointWorkspace({
    snapshot,
    draftKind: input.draftKind,
    draftId: input.draftId,
  });
  if (!workspace) {
    return null;
  }
  return buildGuestExportCheckpointDescriptor({
    workspace,
    createdAt: input.createdAt,
    label: input.label,
  });
}

export function appendGuestCheckpointDescriptor(
  snapshot: ClassroomPlannerGuestSnapshot,
  input: {
    descriptor: ClassroomPlannerGuestCheckpointDescriptor;
    updatedAt: string;
  },
): ClassroomPlannerGuestSnapshot {
  if (
    snapshot.checkpoint_descriptors.some(
      (existing) => existing.fingerprint === input.descriptor.fingerprint,
    )
  ) {
    return snapshot;
  }

  const nextSnapshot = {
    ...snapshot,
    updated_at: input.updatedAt,
    checkpoint_descriptors: [
      ...cloneCheckpointDescriptors(snapshot.checkpoint_descriptors),
      {
        ...input.descriptor,
        group_assignments: cloneGroupAssignments(input.descriptor.group_assignments),
        seat_assignments: cloneSeatAssignments(input.descriptor.seat_assignments),
      },
    ],
  };

  return {
    ...nextSnapshot,
    snapshot_content_hash: createClassroomPlannerGuestContentHash(nextSnapshot),
  };
}

export function buildGuestSmartRulesResponse(input: {
  rosterId: string;
  revision: number;
  seatingPreferences: StudentSeatingPreference[];
  relationshipRules: RelationshipRule[];
}): RosterSmartRulesResponse {
  return {
    roster_id: input.rosterId,
    revision: input.revision,
    seating_preferences: input.seatingPreferences.map((preference) => ({ ...preference })),
    relationship_rules: input.relationshipRules.map((rule) => ({
      ...rule,
      student_ids: [...rule.student_ids],
    })),
  };
}

export function buildNewGuestDraft(input: {
  draftId: string;
  draftKind: PlanDraftKind;
  rosterId: string;
  templateId: string | null;
  templateRequired: boolean;
  nowIso: string;
  groups?: DraftGroup[];
}): PlanDraft {
  return {
    id: input.draftId,
    roster_id: input.rosterId,
    draft_kind: input.draftKind,
    template_id: input.templateId,
    task_entry_classroom_selection_mode: input.templateRequired ? "required" : "optional",
    smart_enabled: false,
    use_history: false,
    grouping_seating_distance_enabled: false,
    status: "active",
    revision: 1,
    last_opened_at: input.nowIso,
  };
}
