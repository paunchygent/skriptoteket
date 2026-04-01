/**
 * Classroom planner lifecycle actions.
 *
 * Purpose:
 *   Own workspace loading, draft lifecycle endpoints, history orchestration,
 *   and planner transition flows so the Pinia store can stay focused on state
 *   composition.
 *
 * Relationships:
 *   - consumed by `useClassroomState.ts`
 *   - coordinates with `plannerTransitionPolicies.ts`
 *   - depends on session invalidation helpers from
 *     `classroomPlannerStateSupport.ts`
 */

import type { Ref } from "vue";

import {
  normalizeClassroomPlannerSummary,
} from "./classroomPlannerPayloadNormalization";
import {
  preparePlannerAbandonDraft,
  preparePlannerExit,
  preparePlannerExport,
  preparePlannerHistoryAction,
  preparePlannerWorkspaceSwitch,
  type PlannerAbandonResult,
  type PlannerExitResult,
  type PlannerTransitionResult,
} from "./plannerTransitionPolicies";
import type {
  ClassWorkspaceSummary,
  DraftWorkspaceResponse,
  PlanDraft,
  PlanDraftKind,
  ResumablePlanDraft,
  Roster,
  RosterSmartRulesResponse,
} from "./classroomPlannerTypes";
import type { usePlannerSessionController } from "./usePlannerSessionController";

type PlannerSessionController = ReturnType<typeof usePlannerSessionController>;

type CreateClassroomPlannerLifecycleOptions = {
  apiDelete: <T>(url: string) => Promise<T>;
  apiGet: <T>(url: string) => Promise<T>;
  apiPost: <T>(url: string, payload?: Record<string, string | null>) => Promise<T>;
  exitAutosaveTimeoutMs: number;
  smartRuleHydrationFallbackMessage: string;
  draft: Ref<PlanDraft | null>;
  roster: Ref<Roster | null>;
  historyActionInFlight: Ref<boolean>;
  sessionController: PlannerSessionController;
  syncVisibleSessionBindings: () => void;
  createTransitionController: () => {
    draft: PlanDraft | null;
    flushDraftPersistenceLane: () => Promise<{ status: "saved" } | { status: "blocked"; reason: "conflict" | "error"; message: string }>;
    flushSmartRuleLane: () => Promise<{ status: "saved" } | { status: "blocked"; reason: "conflict" | "error"; message: string }>;
    discardDraftPersistenceLane: () => void;
    discardSmartRuleLane: () => void;
  };
  normalizeMutationError: (error: unknown, fallbackMessage: string) => string;
  clearRosterSmartRules: (options?: { resetUiState?: boolean }) => void;
  applyWorkspace: (workspace: DraftWorkspaceResponse) => void;
  applyRosterSmartRules: (rules: RosterSmartRulesResponse) => void;
  clearWorkspace: () => void;
  discardPendingSessionWork: () => void;
  discardPendingDraftChanges: () => void;
  resetBoundDraft: (draftId: string | null) => void;
  bindSmartRuleRoster: (rosterId: string | null) => void;
  markSmartRuleHydrating: () => void;
  failSmartRuleHydration: (message: string) => void;
};

export function createClassroomPlannerLifecycle(
  options: CreateClassroomPlannerLifecycleOptions,
) {
  async function prepareForWorkspaceSwitch(messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }): Promise<PlannerTransitionResult> {
    options.syncVisibleSessionBindings();
    return await preparePlannerWorkspaceSwitch(options.createTransitionController(), messages);
  }

  async function prepareForExport(messages: {
    conflictMessage: string;
    fallbackMessage: string;
  }): Promise<PlannerTransitionResult> {
    options.syncVisibleSessionBindings();
    return await preparePlannerExport(options.createTransitionController(), messages);
  }

  async function prepareForPlannerExit(): Promise<PlannerExitResult> {
    options.syncVisibleSessionBindings();
    return await preparePlannerExit(
      options.createTransitionController(),
      options.exitAutosaveTimeoutMs,
      {
        conflictMessage: "Lös sparkonflikten innan du avslutar Klassrumskartan.",
        fallbackMessage: "Kunde inte avsluta Klassrumskartan just nu.",
      },
    );
  }

  async function retrySmartRuleHydration(): Promise<void> {
    const activeRosterId = options.roster.value?.id ?? null;
    if (!activeRosterId) {
      return;
    }
    const requestSessionToken = options.sessionController.sessionToken.value;
    options.markSmartRuleHydrating();
    try {
      const rules = await options.apiGet<RosterSmartRulesResponse>(
        `/api/v1/apps/classroom.group-seating-studio/rosters/${activeRosterId}/smart-rules`,
      );
      if (
        options.sessionController.sessionToken.value !== requestSessionToken
        || options.roster.value?.id !== activeRosterId
      ) {
        return;
      }
      options.applyRosterSmartRules(rules);
    } catch (error: unknown) {
      if (
        options.sessionController.sessionToken.value !== requestSessionToken
        || options.roster.value?.id !== activeRosterId
      ) {
        return;
      }
      options.failSmartRuleHydration(
        options.normalizeMutationError(error, options.smartRuleHydrationFallbackMessage),
      );
    }
  }

  async function loadWorkspace(draftId: string): Promise<void> {
    const requestId = options.sessionController.createWorkspaceLoadRequest();
    options.sessionController.beginWorkspaceTransition();
    try {
      const workspace = await options.apiGet<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}/workspace`,
      );
      if (!options.sessionController.isCurrentWorkspaceLoadRequest(requestId)) {
        return;
      }

      options.sessionController.replaceSession({
        draftId: workspace.draft.id,
        rosterId: workspace.roster.id,
      });
      options.resetBoundDraft(workspace.draft.id);
      options.bindSmartRuleRoster(workspace.roster.id);
      options.clearRosterSmartRules({ resetUiState: true });
      options.applyWorkspace(workspace);

      try {
        const rules = await options.apiGet<RosterSmartRulesResponse>(
          `/api/v1/apps/classroom.group-seating-studio/rosters/${workspace.roster.id}/smart-rules`,
        );
        if (!options.sessionController.isCurrentWorkspaceLoadRequest(requestId)) {
          return;
        }
        options.applyRosterSmartRules(rules);
      } catch (error: unknown) {
        if (!options.sessionController.isCurrentWorkspaceLoadRequest(requestId)) {
          return;
        }
        options.failSmartRuleHydration(
          options.normalizeMutationError(error, options.smartRuleHydrationFallbackMessage),
        );
      }
    } finally {
      options.sessionController.endWorkspaceTransition();
    }
  }

  async function reloadActiveWorkspace(): Promise<void> {
    if (!options.draft.value) {
      return;
    }
    await loadWorkspace(options.draft.value.id);
  }

  async function runLifecycleLoad(
    url: string,
    payload?: Record<string, string | null>,
  ): Promise<void> {
    options.sessionController.beginWorkspaceTransition();
    try {
      const createdDraft = payload === undefined
        ? await options.apiPost<PlanDraft>(url)
        : await options.apiPost<PlanDraft>(url, payload);
      await loadWorkspace(createdDraft.id);
    } finally {
      options.sessionController.endWorkspaceTransition();
    }
  }

  async function resolveDraft(
    rosterId: string,
    templateId: string | null,
    draftKind: PlanDraftKind = "seating",
  ): Promise<void> {
    await runLifecycleLoad("/api/v1/apps/classroom.group-seating-studio/drafts/resolve", {
      roster_id: rosterId,
      draft_kind: draftKind,
      template_id: templateId,
    });
  }

  async function startNewGroupingDraft(
    rosterId: string,
    templateId: string | null,
  ): Promise<void> {
    await runLifecycleLoad("/api/v1/apps/classroom.group-seating-studio/drafts/grouping/new", {
      roster_id: rosterId,
      template_id: templateId,
    });
  }

  async function startNewSeatingDraft(
    rosterId: string,
    templateId: string,
  ): Promise<void> {
    await runLifecycleLoad("/api/v1/apps/classroom.group-seating-studio/drafts/seating/new", {
      roster_id: rosterId,
      template_id: templateId,
    });
  }

  async function activateGroupingHistoryDraft(draftId: string): Promise<void> {
    await runLifecycleLoad(
      `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${draftId}/activate`,
    );
  }

  async function activateSeatingHistoryDraft(draftId: string): Promise<void> {
    await runLifecycleLoad(
      `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${draftId}/activate`,
    );
  }

  async function deleteGroupingHistoryDraft(draftId: string): Promise<void> {
    options.sessionController.beginWorkspaceTransition();
    try {
      await options.apiDelete<void>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/${draftId}`,
      );
    } finally {
      options.sessionController.endWorkspaceTransition();
    }
  }

  async function deleteSeatingHistoryDraft(draftId: string): Promise<void> {
    options.sessionController.beginWorkspaceTransition();
    try {
      await options.apiDelete<void>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/seating/${draftId}`,
      );
    } finally {
      options.sessionController.endWorkspaceTransition();
    }
  }

  async function runHistoryAction(action: "undo" | "redo"): Promise<void> {
    if (!options.draft.value || options.historyActionInFlight.value) {
      return;
    }

    options.syncVisibleSessionBindings();
    const historyPreparation = await preparePlannerHistoryAction(
      options.createTransitionController(),
    );
    if (historyPreparation.status === "blocked" || !options.draft.value) {
      return;
    }

    options.historyActionInFlight.value = true;
    try {
      const workspace = await options.apiPost<DraftWorkspaceResponse>(
        `/api/v1/apps/classroom.group-seating-studio/drafts/${options.draft.value.id}/${action}`,
      );
      options.applyWorkspace(workspace);
    } finally {
      options.historyActionInFlight.value = false;
    }
  }

  async function undoGroupingDraft(): Promise<void> {
    await runHistoryAction("undo");
  }

  async function redoGroupingDraft(): Promise<void> {
    await runHistoryAction("redo");
  }

  async function undoSeatingDraft(): Promise<void> {
    await runHistoryAction("undo");
  }

  async function redoSeatingDraft(): Promise<void> {
    await runHistoryAction("redo");
  }

  async function getResumableDraft(): Promise<ResumablePlanDraft | null> {
    return await options.apiGet<ResumablePlanDraft | null>(
      "/api/v1/apps/classroom.group-seating-studio/drafts/resumable",
    );
  }

  async function getClassWorkspaceSummary(rosterId: string): Promise<ClassWorkspaceSummary> {
    const summary = await options.apiGet<ClassWorkspaceSummary>(
      `/api/v1/apps/classroom.group-seating-studio/rosters/${rosterId}/workspace-summary`,
    );
    return normalizeClassroomPlannerSummary(summary);
  }

  async function abandonDraft(
    draftId?: string,
    optionsArg: { continueWithoutSavingSmartRules?: boolean } = {},
  ): Promise<PlannerAbandonResult> {
    const targetDraftId = draftId ?? options.draft.value?.id ?? null;
    if (!targetDraftId) {
      options.clearWorkspace();
      return { status: "saved" };
    }

    options.syncVisibleSessionBindings();
    const abandonPreparation = await preparePlannerAbandonDraft(
      options.createTransitionController(),
      {
        continueAnywayMessage:
          "Fortsätter du nu förlorar du osparade klassövergripande smarta regler för klassen.",
      },
    );
    if (
      abandonPreparation.status === "confirm-discard"
      && !optionsArg.continueWithoutSavingSmartRules
    ) {
      return abandonPreparation;
    }

    if (abandonPreparation.status === "confirm-discard") {
      options.discardPendingSessionWork();
    }

    options.discardPendingDraftChanges();
    await options.apiPost<PlanDraft>(
      `/api/v1/apps/classroom.group-seating-studio/drafts/${targetDraftId}/abandon`,
    );
    if (options.draft.value?.id === targetDraftId) {
      options.clearWorkspace();
    }
    return { status: "saved" };
  }

  return {
    prepareForWorkspaceSwitch,
    prepareForExport,
    prepareForPlannerExit,
    retrySmartRuleHydration,
    loadWorkspace,
    reloadActiveWorkspace,
    resolveDraft,
    startNewGroupingDraft,
    startNewSeatingDraft,
    activateGroupingHistoryDraft,
    deleteGroupingHistoryDraft,
    activateSeatingHistoryDraft,
    deleteSeatingHistoryDraft,
    undoGroupingDraft,
    redoGroupingDraft,
    undoSeatingDraft,
    redoSeatingDraft,
    getResumableDraft,
    getClassWorkspaceSummary,
    abandonDraft,
  };
}
