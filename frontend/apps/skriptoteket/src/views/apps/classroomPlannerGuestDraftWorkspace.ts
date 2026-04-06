/**
 * Classroom planner guest draft workspace actions.
 *
 * This module owns guest workspace restore, draft switching, and overview
 * persistence. It keeps the checkpoint-3 browser-owned planner transitions out
 * of the main session assembly file while preserving the same shared planner
 * mutation/state helpers.
 */

import type { ComputedRef, Ref } from "vue";

import { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import { hydrateGuestSnapshot } from "./classroomPlannerGuestSnapshotMapping";
import {
  buildGuestWorkspaceResponse,
  replaceGuestSnapshotDraft,
} from "./classroomPlannerGuestDraftMutations";
import type {
  DraftWorkspaceResponse,
  DraftGroup,
  GroupAssignment,
  PlanDraft,
  PlanDraftKind,
  RoomTemplate,
  Roster,
  SeatAssignment,
  RosterSmartRulesResponse,
} from "./classroomPlannerTypes";
import {
  preparePlannerExit,
  preparePlannerWorkspaceSwitch,
  type PlannerTransitionResult,
} from "./plannerTransitionPolicies";
import type { CreateClassroomPlannerGuestDraftSessionOptions } from "./classroomPlannerGuestDraftPersistence";
import { createClassroomPlannerGuestDraftPersistence } from "./classroomPlannerGuestDraftPersistence";
import { useDraftPersistenceLane } from "./useDraftPersistenceLane";
import { usePlannerSessionController } from "./usePlannerSessionController";
import { useRosterSmartRuleLane } from "./useRosterSmartRuleLane";

const EXIT_AUTOSAVE_TIMEOUT_MS = 1500;

type GuestDraftWorkspaceContext = {
  options: CreateClassroomPlannerGuestDraftSessionOptions;
  draft: Ref<PlanDraft | null>;
  roster: Ref<Roster | null>;
  template: Ref<RoomTemplate | null>;
  groups: Ref<DraftGroup[]>;
  groupAssignments: ComputedRef<GroupAssignment[]>;
  seatAssignments: ComputedRef<SeatAssignment[]>;
  sessionController: ReturnType<typeof usePlannerSessionController>;
  draftLane: ReturnType<typeof useDraftPersistenceLane>;
  smartRuleLane: ReturnType<typeof useRosterSmartRuleLane>;
  stateSupport: ReturnType<typeof createClassroomPlannerStateSupport>;
  persistence: ReturnType<typeof createClassroomPlannerGuestDraftPersistence>;
};

export function createClassroomPlannerGuestDraftWorkspace(
  context: GuestDraftWorkspaceContext,
) {
  const {
    options,
    draft,
    roster,
    template,
    groups,
    groupAssignments,
    seatAssignments,
    sessionController,
    draftLane,
    smartRuleLane,
    stateSupport,
    persistence,
  } = context;

  function applyWorkspace(workspace: Awaited<ReturnType<typeof persistence.createNewWorkspace>>): void {
    stateSupport.applyWorkspace(workspace);
    sessionController.replaceSession({
      draftId: workspace.draft.id,
      rosterId: workspace.roster.id,
    });
    draftLane.resetBoundDraft(workspace.draft.id);
    smartRuleLane.bindRoster(workspace.roster.id);
  }

  function applyHydratedSmartRules(rules: RosterSmartRulesResponse | null): void {
    stateSupport.clearRosterSmartRules({ resetUiState: true });
    if (rules) {
      stateSupport.applyRosterSmartRules(rules);
      return;
    }
    smartRuleLane.applyHydratedRules();
  }

  async function persistPlannerWorkspace(
    workspace: DraftWorkspaceResponse,
    input: {
      rosterId: string;
      templateId: string | null;
      plannerInitialView: "groups" | "seats";
    },
  ): Promise<void> {
    await options.persistSnapshotMutation({
      mutate(snapshotState, updatedAt) {
        return {
          nextSnapshot: replaceGuestSnapshotDraft(snapshotState, workspace, {
            updatedAt,
            currentScreen: "planner",
            plannerInitialView: input.plannerInitialView,
            selectedRosterId: input.rosterId,
            selectedTemplateId: input.templateId,
            dismissedGroupingDraftId: null,
            dismissedSeatingDraftId: null,
          }),
          result: undefined,
        };
      },
    });
  }

  function resolveReusableDraft(input: {
    draftKind: PlanDraftKind;
    existingDraft: DraftWorkspaceResponse | null;
    rosterId: string;
    templateId: string | null;
  }): DraftWorkspaceResponse | null {
    if (!input.existingDraft || input.existingDraft.roster.id !== input.rosterId) {
      return null;
    }

    if (input.draftKind === "seating") {
      return (input.existingDraft.template?.id ?? null) === input.templateId
        ? input.existingDraft
        : null;
    }

    return input.existingDraft;
  }

  async function loadWorkspaceFromSnapshot(draftId: string): Promise<void> {
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const workspace =
      hydrated.grouping_draft?.draft.id === draftId
        ? hydrated.grouping_draft
        : hydrated.seating_draft?.draft.id === draftId
          ? hydrated.seating_draft
          : null;
    if (!workspace) {
      throw new Error("Det gick inte att återställa utkastet i den publika arbetsytan.");
    }

    const rules = hydrated.smart_rule_sets.find((entry) => entry.roster_id === workspace.roster.id) ?? null;
    sessionController.beginWorkspaceTransition();
    try {
      applyWorkspace(workspace);
      applyHydratedSmartRules(rules);
    } finally {
      sessionController.endWorkspaceTransition();
    }
  }

  async function resolveDraft(
    rosterId: string,
    templateId: string | null,
    draftKind: PlanDraftKind,
  ): Promise<void> {
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const existingDraft =
      draftKind === "grouping" ? hydrated.grouping_draft : hydrated.seating_draft;
    const reusableDraft = resolveReusableDraft({
      draftKind,
      existingDraft,
      rosterId,
      templateId,
    });
    if (reusableDraft) {
      await persistPlannerWorkspace(reusableDraft, {
        rosterId,
        templateId:
          draftKind === "grouping"
            ? hydrated.ui_state.selected_template_id
            : (reusableDraft.template?.id ?? null),
        plannerInitialView: draftKind === "grouping" ? "groups" : "seats",
      });
      await loadWorkspaceFromSnapshot(reusableDraft.draft.id);
      return;
    }

    const workspace = await persistence.createNewWorkspace(rosterId, templateId, draftKind);
    const rules = hydrated.smart_rule_sets.find((entry) => entry.roster_id === rosterId) ?? null;
    await persistPlannerWorkspace(workspace, {
      rosterId,
      templateId:
        draftKind === "grouping"
          ? hydrated.ui_state.selected_template_id
          : (workspace.template?.id ?? null),
      plannerInitialView: draftKind === "grouping" ? "groups" : "seats",
    });
    applyWorkspace(workspace);
    applyHydratedSmartRules(rules);
  }

  async function startNewGroupingDraft(rosterId: string, templateId: string | null): Promise<void> {
    const workspace = await persistence.createNewWorkspace(rosterId, templateId, "grouping");
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const rules = hydrated.smart_rule_sets.find((entry) => entry.roster_id === rosterId) ?? null;
    await persistPlannerWorkspace(workspace, {
      rosterId,
      templateId: hydrated.ui_state.selected_template_id,
      plannerInitialView: "groups",
    });
    applyWorkspace(workspace);
    applyHydratedSmartRules(rules);
  }

  async function startNewSeatingDraft(rosterId: string, templateId: string): Promise<void> {
    const workspace = await persistence.createNewWorkspace(rosterId, templateId, "seating");
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const rules = hydrated.smart_rule_sets.find((entry) => entry.roster_id === rosterId) ?? null;
    await persistPlannerWorkspace(workspace, {
      rosterId,
      templateId,
      plannerInitialView: "seats",
    });
    applyWorkspace(workspace);
    applyHydratedSmartRules(rules);
  }

  async function retrySmartRuleHydration(): Promise<void> {
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const rosterId = roster.value?.id ?? null;
    if (!rosterId) {
      return;
    }

    smartRuleLane.markHydrating();
    const rules = hydrated.smart_rule_sets.find((entry) => entry.roster_id === rosterId) ?? null;
    if (rules) {
      stateSupport.applyRosterSmartRules(rules);
      return;
    }
    smartRuleLane.applyHydratedRules();
  }

  async function prepareForWorkspaceSwitch(messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }): Promise<PlannerTransitionResult> {
    stateSupport.syncVisibleSessionBindings();
    return await preparePlannerWorkspaceSwitch(stateSupport.createTransitionController(), messages);
  }

  async function prepareForPlannerExit() {
    stateSupport.syncVisibleSessionBindings();
    return await preparePlannerExit(
      stateSupport.createTransitionController(),
      EXIT_AUTOSAVE_TIMEOUT_MS,
      {
        conflictMessage: "Lös sparkonflikten innan du avslutar Klassrumskartan.",
        fallbackMessage: "Kunde inte avsluta Klassrumskartan just nu.",
      },
    );
  }

  async function prepareForExport(messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }): Promise<PlannerTransitionResult> {
    stateSupport.syncVisibleSessionBindings();
    return await preparePlannerWorkspaceSwitch(stateSupport.createTransitionController(), messages);
  }

  async function persistCurrentWorkspaceToOverview(input: {
    selectedRosterId: string | null;
    selectedTemplateId: string | null;
    plannerInitialView: "groups" | "seats" | "rules";
  }): Promise<void> {
    const activeWorkspace = await persistence.persistGuestWorkspace();
    await options.persistSnapshotMutation({
      mutate(snapshotState, updatedAt) {
        return {
          nextSnapshot: replaceGuestSnapshotDraft(snapshotState, activeWorkspace, {
            updatedAt,
            currentScreen: "class-workspace",
            plannerInitialView: input.plannerInitialView,
            selectedRosterId: input.selectedRosterId,
            selectedTemplateId: input.selectedTemplateId,
            dismissedGroupingDraftId: null,
            dismissedSeatingDraftId: null,
          }),
          result: undefined,
        };
      },
    });
  }

  async function persistOverviewUiState(input: {
    selectedRosterId: string | null;
    selectedTemplateId: string | null;
    plannerInitialView: "groups" | "seats" | "rules";
  }): Promise<void> {
    const snapshot = await options.getSnapshot();
    const hydrated = hydrateGuestSnapshot(snapshot);
    const activeWorkspace =
      draft.value && roster.value
        ? buildGuestWorkspaceResponse({
            draft: draft.value,
            roster: roster.value,
            template: template.value,
            groups: groups.value,
            groupAssignments: groupAssignments.value,
            seatAssignments: seatAssignments.value,
          })
        : null;

    await options.persistSnapshotMutation({
      mutate(snapshotState, updatedAt) {
        if (activeWorkspace) {
          return {
            nextSnapshot: replaceGuestSnapshotDraft(snapshotState, activeWorkspace, {
              updatedAt,
              currentScreen: "class-workspace",
              plannerInitialView: input.plannerInitialView,
              selectedRosterId: input.selectedRosterId,
              selectedTemplateId: input.selectedTemplateId,
              dismissedGroupingDraftId: hydrated.ui_state.dismissed_grouping_draft_id,
              dismissedSeatingDraftId: hydrated.ui_state.dismissed_seating_draft_id,
            }),
            result: undefined,
          };
        }

        return {
          nextSnapshot: {
            ...snapshotState,
            updated_at: updatedAt,
          },
          result: undefined,
        };
      },
    });
  }

  return {
    applyWorkspace,
    applyHydratedSmartRules,
    loadWorkspace: loadWorkspaceFromSnapshot,
    resolveDraft,
    startNewGroupingDraft,
    startNewSeatingDraft,
    retrySmartRuleHydration,
    prepareForWorkspaceSwitch,
    prepareForPlannerExit,
    prepareForExport,
    persistCurrentWorkspaceToOverview,
    persistOverviewUiState,
  };
}
