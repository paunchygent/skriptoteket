/**
 * Guest draft workspace regression tests.
 *
 * These tests lock the guest-only draft reuse path so changing the grouping
 * classroom on an existing guest draft updates both the persisted browser
 * snapshot and the next public Smart payload.
 */

import { computed, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { createClassroomPlannerGuestDraftPersistence } from "./classroomPlannerGuestDraftPersistence";
import { createClassroomPlannerGuestDraftWorkspace } from "./classroomPlannerGuestDraftWorkspace";
import { buildNewGuestDraft } from "./classroomPlannerGuestDraftMutations";
import { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import {
  createClassroomPlannerGuestSnapshotFromSeed,
  hydrateGuestSnapshot,
} from "./classroomPlannerGuestSnapshotMapping";
import type {
  DraftGroup,
  DraftWorkspaceResponse,
  GroupAssignment,
  PlanDraft,
  RoomTemplate,
  Roster,
  SeatAssignment,
} from "./classroomPlannerTypes";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import { usePlannerSessionController } from "./usePlannerSessionController";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";

const NOW_ISO = "2026-04-07T10:00:00.000Z";

function createRoster(): Roster {
  return {
    id: "roster-1",
    name: "SA24D",
    students: [
      { id: "ada", display_name: "Ada" },
      { id: "alan", display_name: "Alan" },
    ],
  };
}

function createTemplate(id: string, name: string): RoomTemplate {
  return {
    id,
    name,
    grid_cols: 4,
    grid_rows: 4,
    seats: [
      { id: `${id}-seat-1`, x: 0, y: 0, zone: null },
      { id: `${id}-seat-2`, x: 1, y: 0, zone: null },
    ],
    fixtures: [],
  };
}

function createGroupingWorkspace(template: RoomTemplate | null): DraftWorkspaceResponse {
  return {
    draft: {
      id: "grouping-draft-1",
      roster_id: "roster-1",
      draft_kind: "grouping",
      template_id: template?.id ?? null,
      task_entry_classroom_selection_mode: "optional",
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: true,
      status: "active",
      revision: 4,
      last_opened_at: NOW_ISO,
    },
    roster: createRoster(),
    template,
    groups: [
      { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ],
    group_assignments: [
      { student_id: "ada", group_id: "group-a" },
      { student_id: "alan", group_id: "group-b" },
    ],
    seat_assignments: [],
    history_status: {
      can_undo: false,
      can_redo: false,
    },
  };
}

describe("classroomPlannerGuestDraftWorkspace", () => {
  it("starts new public guest drafts with available Smart settings enabled", () => {
    const draft = buildNewGuestDraft({
      draftId: "draft-1",
      draftKind: "seating",
      rosterId: "roster-1",
      templateId: "template-1",
      templateRequired: true,
      nowIso: NOW_ISO,
    });

    expect(draft.smart_enabled).toBe(true);
    expect(draft.grouping_seating_distance_enabled).toBe(true);
    expect(draft.use_history).toBe(false);
  });

  it("persists the newly selected grouping classroom when reusing an existing guest draft", async () => {
    const templateTwo = createTemplate("template-2", "Sal 202");
    let snapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-1",
      created_at: "2026-04-07T09:00:00.000Z",
      updated_at: NOW_ISO,
      expires_at: "2026-04-21T10:00:00.000Z",
      rosters: [createRoster()],
      templates: [
        createTemplate("template-1", "Sal 101"),
        templateTwo,
      ],
      smart_rule_sets: [
        {
          roster_id: "roster-1",
          revision: 1,
          seating_preferences: [],
          relationship_rules: [],
        },
      ],
      grouping_draft: createGroupingWorkspace(null),
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: null,
        current_screen: "planner",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    const draft = ref<PlanDraft | null>(null);
    const roster = ref<Roster | null>(null);
    const template = ref<RoomTemplate | null>(null);
    const groups = ref<DraftGroup[]>([]);
    const currentGroupAssignments = ref<GroupAssignment[]>([]);
    const currentSeatAssignments = ref<SeatAssignment[]>([]);

    const sessionController = {
      replaceSession: vi.fn(),
      beginWorkspaceTransition: vi.fn(),
      endWorkspaceTransition: vi.fn(),
    } as unknown as ReturnType<typeof usePlannerSessionController>;
    const draftLane = {
      resetBoundDraft: vi.fn(),
    } as unknown as ReturnType<typeof useDraftPersistenceLane>;
    const smartRuleLane = {
      bindRoster: vi.fn(),
      applyHydratedRules: vi.fn(),
      markHydrating: vi.fn(),
    } as unknown as ReturnType<typeof useRosterSmartRuleLane>;
    const stateSupport = {
      applyWorkspace: vi.fn((workspace: DraftWorkspaceResponse) => {
        draft.value = workspace.draft;
        roster.value = workspace.roster;
        template.value = workspace.template ?? null;
        groups.value = workspace.groups;
        currentGroupAssignments.value = workspace.group_assignments;
        currentSeatAssignments.value = workspace.seat_assignments;
      }),
      clearRosterSmartRules: vi.fn(),
      applyRosterSmartRules: vi.fn(),
      syncVisibleSessionBindings: vi.fn(),
      createTransitionController: vi.fn(),
    } as unknown as ReturnType<typeof createClassroomPlannerStateSupport>;
    const persistence = {
      createNewWorkspace: vi.fn(),
      persistGuestWorkspace: vi.fn(),
      persistGuestSmartRules: vi.fn(),
      getClassWorkspaceSummary: vi.fn(),
      getResumableDraft: vi.fn(),
    } as unknown as ReturnType<typeof createClassroomPlannerGuestDraftPersistence>;

    const workspace = createClassroomPlannerGuestDraftWorkspace({
      options: {
        getSnapshot: vi.fn(async () => snapshot),
        persistSnapshotMutation: vi.fn(async ({ mutate }) => {
          const mutationResult = mutate(snapshot, "2026-04-07T10:05:00.000Z");
          snapshot = mutationResult.nextSnapshot;
          return mutationResult.result;
        }),
        nowIso: () => NOW_ISO,
      },
      draft,
      roster,
      template,
      groups,
      groupAssignments: computed(() => currentGroupAssignments.value),
      seatAssignments: computed(() => currentSeatAssignments.value),
      sessionController,
      draftLane,
      smartRuleLane,
      stateSupport,
      persistence,
      syncWorkspaceHistory: vi.fn(),
    });

    await workspace.resolveDraft("roster-1", "template-2", "grouping");

    const persistedSnapshot = snapshot;
    const hydratedSnapshot = hydrateGuestSnapshot(persistedSnapshot);
    const nextSmartRunPayload = {
      expected_revision: hydratedSnapshot.grouping_draft?.draft.revision ?? 0,
      snapshot: persistedSnapshot,
    };

    expect(persistence.createNewWorkspace).not.toHaveBeenCalled();
    expect(template.value?.id).toBe("template-2");
    expect(draft.value?.template_id).toBe("template-2");
    expect(persistedSnapshot.ui_state.selected_template_local_id).toBe("template-2");
    expect(persistedSnapshot.grouping_draft?.template_local_id).toBe("template-2");
    expect(hydratedSnapshot.grouping_draft?.template?.id).toBe("template-2");
    expect(nextSmartRunPayload.snapshot.ui_state.selected_template_local_id).toBe("template-2");
    expect(nextSmartRunPayload.snapshot.grouping_draft?.template_local_id).toBe("template-2");
  });

  it("directly commits an accepted Smart workspace to the guest snapshot while acknowledging the draft lane", async () => {
    const template = createTemplate("template-1", "Sal 101");
    let snapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-1",
      created_at: "2026-04-07T09:00:00.000Z",
      updated_at: NOW_ISO,
      expires_at: "2026-04-21T10:00:00.000Z",
      rosters: [createRoster()],
      templates: [template],
      smart_rule_sets: [],
      grouping_draft: createGroupingWorkspace(template),
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: "template-1",
        current_screen: "planner",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: "old-grouping-draft",
        dismissed_seating_draft_id: "old-seating-draft",
      },
    });
    const acceptedWorkspace: DraftWorkspaceResponse = {
      ...createGroupingWorkspace(template),
      draft: {
        ...createGroupingWorkspace(template).draft,
        revision: 5,
      },
      group_assignments: [
        { student_id: "ada", group_id: "group-b" },
        { student_id: "alan", group_id: "group-a" },
      ],
    };
    const acknowledgeExternalCommit = vi.fn();
    const markDirty = vi.fn();

    const workspace = createClassroomPlannerGuestDraftWorkspace({
      options: {
        getSnapshot: vi.fn(async () => snapshot),
        persistSnapshotMutation: vi.fn(async ({ mutate }) => {
          const mutationResult = mutate(snapshot, "2026-04-07T10:05:00.000Z");
          snapshot = mutationResult.nextSnapshot;
          return mutationResult.result;
        }),
        nowIso: () => NOW_ISO,
      },
      draft: ref<PlanDraft | null>(acceptedWorkspace.draft),
      roster: ref<Roster | null>(acceptedWorkspace.roster),
      template: ref<RoomTemplate | null>(acceptedWorkspace.template ?? null),
      groups: ref<DraftGroup[]>(acceptedWorkspace.groups),
      groupAssignments: computed(() => acceptedWorkspace.group_assignments),
      seatAssignments: computed(() => acceptedWorkspace.seat_assignments),
      sessionController: {} as ReturnType<typeof usePlannerSessionController>,
      draftLane: {
        acknowledgeExternalCommit,
        markDirty,
      } as unknown as ReturnType<typeof useDraftPersistenceLane>,
      smartRuleLane: {} as ReturnType<typeof useRosterSmartRuleLane>,
      stateSupport: {} as ReturnType<typeof createClassroomPlannerStateSupport>,
      persistence: {} as ReturnType<typeof createClassroomPlannerGuestDraftPersistence>,
      syncWorkspaceHistory: vi.fn(),
    });

    const committedSnapshot = await workspace.commitWorkspaceToGuestSnapshot(acceptedWorkspace);

    expect(committedSnapshot.grouping_draft?.revision).toBe(5);
    expect(committedSnapshot.grouping_draft?.group_assignments).toEqual(
      acceptedWorkspace.group_assignments,
    );
    expect(committedSnapshot.ui_state.current_screen).toBe("planner");
    expect(committedSnapshot.ui_state.planner_initial_view).toBe("groups");
    expect(committedSnapshot.ui_state.selected_roster_local_id).toBe("roster-1");
    expect(committedSnapshot.ui_state.selected_template_local_id).toBe("template-1");
    expect(committedSnapshot.ui_state.dismissed_grouping_draft_local_id).toBe(
      "old-grouping-draft",
    );
    expect(committedSnapshot.ui_state.dismissed_seating_draft_local_id).toBe(
      "old-seating-draft",
    );
    expect(acknowledgeExternalCommit).toHaveBeenCalledWith("grouping-draft-1");
    expect(markDirty).not.toHaveBeenCalled();
  });
});
