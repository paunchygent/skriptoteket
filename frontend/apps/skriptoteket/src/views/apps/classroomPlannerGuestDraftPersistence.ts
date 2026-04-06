/**
 * Classroom planner guest draft persistence.
 *
 * This module owns pure guest snapshot persistence for checkpoint 3. It keeps
 * draft serialization, smart-rule serialization, and new workspace creation in
 * one place so the session assembly can stay focused on wiring shared planner
 * primitives together.
 */

import type { ComputedRef, Ref } from "vue";

import type {
  ClassWorkspaceSummary,
  DraftGroup,
  DraftWorkspaceResponse,
  GroupAssignment,
  PlanDraft,
  PlanDraftKind,
  RelationshipRule,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  SeatAssignment,
  StudentSeatingPreference,
} from "./classroomPlannerTypes";
import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import { hydrateGuestSnapshot } from "./classroomPlannerGuestSnapshotMapping";
import {
  buildGuestSmartRulesResponse,
  buildGuestWorkspaceResponse,
  buildGuestWorkspaceSummary,
  buildNewGuestDraft,
  replaceGuestSnapshotDraft,
  replaceGuestSnapshotSmartRules,
} from "./classroomPlannerGuestDraftMutations";
import { buildDefaultGroupName, createGroupId } from "./classroomPlannerStoreMutations";

export type GuestSnapshotMutationRunner = <T>(input: {
  mutate: (
    snapshot: ClassroomPlannerGuestSnapshot,
    updatedAt: string,
  ) => {
    nextSnapshot: ClassroomPlannerGuestSnapshot;
    result: T;
  };
}) => Promise<T>;

export type CreateClassroomPlannerGuestDraftSessionOptions = {
  getSnapshot: () => Promise<ClassroomPlannerGuestSnapshot>;
  persistSnapshotMutation: GuestSnapshotMutationRunner;
  nowIso: () => string;
  createDraftId?: () => string;
};

type GuestDraftPersistenceContext = {
  options: CreateClassroomPlannerGuestDraftSessionOptions;
  draft: Ref<PlanDraft | null>;
  roster: Ref<Roster | null>;
  template: Ref<RoomTemplate | null>;
  groups: Ref<DraftGroup[]>;
  groupAssignments: ComputedRef<GroupAssignment[]>;
  seatAssignments: ComputedRef<SeatAssignment[]>;
  seatingPreferences: Ref<StudentSeatingPreference[]>;
  relationshipRules: Ref<RelationshipRule[]>;
  smartRulesRevision: Ref<number>;
};

function defaultCreateDraftId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `guest-draft-${Date.now()}`;
}

const DEFAULT_GROUPING_DRAFT_GROUP_COUNT = 4;

function createDefaultGroupingDraftGroups(): DraftGroup[] {
  return Array.from({ length: DEFAULT_GROUPING_DRAFT_GROUP_COUNT }, (_entry, index) => ({
    id: createGroupId(),
    name: buildDefaultGroupName(index),
    sort_order: index,
    name_is_custom: false,
  }));
}

export function createClassroomPlannerGuestDraftPersistence(
  context: GuestDraftPersistenceContext,
) {
  const {
    options,
    draft,
    roster,
    template,
    groups,
    groupAssignments,
    seatAssignments,
    seatingPreferences,
    relationshipRules,
    smartRulesRevision,
  } = context;

  function resolvePersistedSelectedTemplateId(
    snapshot: ClassroomPlannerGuestSnapshot,
    draftKind: PlanDraftKind,
  ): string | null {
    if (draftKind === "grouping") {
      return snapshot.ui_state.selected_template_local_id;
    }

    return template.value?.id ?? null;
  }

  async function persistGuestWorkspace(): Promise<DraftWorkspaceResponse> {
    if (!draft.value || !roster.value) {
      throw new Error("Det finns inget publikt utkast att spara.");
    }

    return await options.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        const workspace = buildGuestWorkspaceResponse({
          draft: {
            ...draft.value!,
            last_opened_at: updatedAt,
          },
          roster: roster.value!,
          template: template.value,
          groups: groups.value,
          groupAssignments: groupAssignments.value,
          seatAssignments: seatAssignments.value,
        });
        return {
          nextSnapshot: replaceGuestSnapshotDraft(snapshot, workspace, {
            updatedAt,
            currentScreen: "planner",
            plannerInitialView: workspace.draft.draft_kind === "grouping" ? "groups" : "seats",
            selectedRosterId: roster.value!.id,
            selectedTemplateId: resolvePersistedSelectedTemplateId(
              snapshot,
              workspace.draft.draft_kind,
            ),
            dismissedGroupingDraftId: null,
            dismissedSeatingDraftId: null,
          }),
          result: workspace,
        };
      },
    });
  }

  async function persistGuestSmartRules(): Promise<RosterSmartRulesResponse> {
    if (!roster.value) {
      throw new Error("Det finns ingen publik klass att spara regler för.");
    }

    const nextRevision = smartRulesRevision.value + 1;
    const rules = buildGuestSmartRulesResponse({
      rosterId: roster.value.id,
      revision: nextRevision,
      seatingPreferences: seatingPreferences.value,
      relationshipRules: relationshipRules.value,
    });

    return await options.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        return {
          nextSnapshot: replaceGuestSnapshotSmartRules(snapshot, rules, updatedAt),
          result: rules,
        };
      },
    });
  }

  async function createNewWorkspace(
    rosterId: string,
    templateId: string | null,
    draftKind: PlanDraftKind,
  ): Promise<DraftWorkspaceResponse> {
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const nextRoster = hydrated.rosters.find((entry) => entry.id === rosterId) ?? null;
    if (!nextRoster) {
      throw new Error("Det gick inte att hitta klassen i den publika arbetsytan.");
    }

    const nextTemplate = templateId
      ? (hydrated.templates.find((entry) => entry.id === templateId) ?? null)
      : null;
    const nextDraft = buildNewGuestDraft({
      draftId: options.createDraftId?.() ?? defaultCreateDraftId(),
      draftKind,
      rosterId,
      templateId: nextTemplate?.id ?? null,
      templateRequired: draftKind === "seating",
      nowIso: options.nowIso(),
    });

    return buildGuestWorkspaceResponse({
      draft: nextDraft,
      roster: nextRoster,
      template: nextTemplate,
      groups: draftKind === "grouping" ? createDefaultGroupingDraftGroups() : [],
      groupAssignments: [],
      seatAssignments: [],
    });
  }

  async function getClassWorkspaceSummary(rosterId: string): Promise<ClassWorkspaceSummary> {
    return buildGuestWorkspaceSummary(await options.getSnapshot(), rosterId);
  }

  async function getResumableDraft() {
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const nextDraft = snapshot.ui_state.planner_initial_view === "seats"
      ? hydrated.seating_draft ?? hydrated.grouping_draft
      : hydrated.grouping_draft ?? hydrated.seating_draft;
    if (!nextDraft) {
      return null;
    }

    return {
      draft: { ...nextDraft.draft },
      roster_name: nextDraft.roster.name,
      template_name: nextDraft.template?.name ?? null,
    };
  }

  return {
    persistGuestWorkspace,
    persistGuestSmartRules,
    createNewWorkspace,
    getClassWorkspaceSummary,
    getResumableDraft,
  };
}
