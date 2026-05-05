/**
 * Classroom planner route-shell workspace transitions.
 *
 * This module owns transitions between overview, grouping, and seating
 * workspaces, including save guards and history lifecycle actions.
 */

import type { Ref } from "vue";

import { useToast } from "../../composables/useToast";
import { createClassroomPlannerHistoryDraftActions } from "./classroomPlannerHistoryDraftActions";
import type { PlannerScreen, PlannerWorkspaceInitialView } from "./classroomPlannerOverviewStore";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import { flushPlannerRouteShellSave } from "./classroomPlannerRouteShellSaveGuards";
import type { PlannerRouteShellSaveController } from "./classroomPlannerRouteShellSaveGuards";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";
import {
  activeDraftId,
  resolveRulesWorkspaceTemplateId,
  resolveSeatingWorkspaceTemplateId,
} from "./classroomPlannerWorkspaceResolution";

type PlannerRouteShellWorkspaceState = {
  selectedRosterId: Ref<string | null>;
  selectedWorkspaceTemplateId: Ref<string | null>;
  currentScreen: Ref<PlannerScreen>;
  plannerInitialView: Ref<PlannerWorkspaceInitialView>;
  plannerActionError: Ref<string | null>;
  classWorkspaceSummary: Ref<ClassWorkspaceSummary | null>;
  isSeatingLifecycleBusy: Ref<boolean>;
  busySeatingHistoryDraftId: Ref<string | null>;
  workspaceTransitionLabel: Ref<string | null>;
  workspaceNotice: Ref<string | null>;
};

type PlannerRouteShellWorkspaceActions = {
  loadClassWorkspaceSummary: (rosterId: string) => Promise<void>;
  refreshClassWorkspaceSummaryForSelectedRoster: () => Promise<void>;
  openInitialHomeWorkspace: (preferredRosterId: string | null) => Promise<void>;
  syncWorkspaceTemplateSelection: (options?: { preserveCurrent?: boolean }) => void;
};

type PlannerRouteShellWorkspacePlannerState = PlannerRouteShellSaveController & {
  roster: { id: string } | null;
  draft: { id: string } | null;
  template: { id: string } | null;
  loadWorkspace: (draftId: string) => Promise<unknown>;
  resolveDraft: (
    rosterId: string,
    templateId: string | null,
    draftKind: "grouping" | "seating",
  ) => Promise<unknown>;
  clearWorkspace: () => void;
  startNewGroupingDraft: (rosterId: string, templateId: string | null) => Promise<unknown>;
  startNewSeatingDraft: (rosterId: string, templateId: string) => Promise<unknown>;
  activateGroupingHistoryDraft: (draftId: string) => Promise<unknown>;
  activateSeatingHistoryDraft: (draftId: string) => Promise<unknown>;
  deleteGroupingHistoryDraft: (draftId: string) => Promise<unknown>;
  deleteSeatingHistoryDraft: (draftId: string) => Promise<unknown>;
};

type OpenWorkspacePayload = {
  templateId: string | null;
};

type StartSeatingDraftPayload = {
  templateId: string;
};

type ChangeGroupingRosterPayload = {
  rosterId: string;
};

export function createClassroomPlannerWorkspaceFlow(
  state: PlannerRouteShellWorkspaceState,
  actions: PlannerRouteShellWorkspaceActions,
  plannerState: PlannerRouteShellWorkspacePlannerState,
) {
  const toast = useToast();
  const historyDraftActions = createClassroomPlannerHistoryDraftActions(
    state,
    actions,
    plannerState,
    toast,
  );

  async function openWorkspace(
    payload: OpenWorkspacePayload,
    draftKind: "grouping" | "seating",
    initialView: PlannerWorkspaceInitialView,
    fallbackMessage: string,
    options?: {
      transitionLabel?: string | null;
      workspaceNotice?: string | null;
    },
  ): Promise<void> {
    if (!state.selectedRosterId.value) {
      return;
    }

    state.plannerActionError.value = null;
    state.workspaceTransitionLabel.value = options?.transitionLabel ?? null;
    try {
      const currentDraftId = activeDraftId(state.classWorkspaceSummary.value, draftKind);
      if (currentDraftId) {
        await plannerState.loadWorkspace(currentDraftId);
      } else {
        await plannerState.resolveDraft(state.selectedRosterId.value, payload.templateId, draftKind);
      }
      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      state.plannerInitialView.value = initialView;
      state.currentScreen.value = "planner";
      state.workspaceNotice.value = options?.workspaceNotice ?? null;
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(error, fallbackMessage);
      state.workspaceNotice.value = null;
    } finally {
      state.workspaceTransitionLabel.value = null;
    }
  }

  async function openGroupingWorkspace(
    payload: OpenWorkspacePayload,
    options?: {
      transitionLabel?: string | null;
      workspaceNotice?: string | null;
    },
  ): Promise<void> {
    state.workspaceNotice.value = null;
    await openWorkspace(
      payload,
      "grouping",
      "groups",
      "Kunde inte öppna grupparbetsytan just nu.",
      options,
    );
  }

  async function openSeatingWorkspace(
    payload: OpenWorkspacePayload,
    options?: {
      transitionLabel?: string | null;
      workspaceNotice?: string | null;
    },
  ): Promise<void> {
    state.workspaceNotice.value = null;
    await openWorkspace(
      payload,
      "seating",
      "seats",
      "Kunde inte öppna sittplatserna just nu.",
      options,
    );
  }

  async function openRulesWorkspace(): Promise<void> {
    const bootstrapsSeatingHost = activeDraftId(state.classWorkspaceSummary.value, "seating") === null;
    const currentTemplateId = resolveRulesWorkspaceTemplateId({
      bootstrapsSeatingHost,
      plannerTemplateId: plannerState.template?.id ?? null,
      activeSeatingTemplateId: state.classWorkspaceSummary.value?.active_seating_draft?.template_id ?? null,
      selectedWorkspaceTemplateId: state.selectedWorkspaceTemplateId.value,
    });

    await openWorkspace(
      { templateId: currentTemplateId },
      "seating",
      "rules",
      "Kunde inte öppna reglerna just nu.",
      {
        transitionLabel: bootstrapsSeatingHost
          ? "Förbereder Regler genom att starta ett sittschema i bakgrunden..."
          : "Öppnar Regler...",
        workspaceNotice: bootstrapsSeatingHost
          ? "Regler använder ett sittschema i bakgrunden. Vi startade ett nytt sittschema för den här klassen."
          : null,
      },
    );
  }

  async function prepareOverviewDistributionScope(
    scope: "grouping" | "seating",
  ): Promise<boolean> {
    const rosterId = state.selectedRosterId.value;
    if (!rosterId) {
      return false;
    }

    const templateId =
      scope === "seating"
        ? resolveSeatingWorkspaceTemplateId({
          plannerTemplateId: plannerState.template?.id ?? null,
          activeSeatingTemplateId: state.classWorkspaceSummary.value?.active_seating_draft?.template_id ?? null,
          selectedWorkspaceTemplateId: state.selectedWorkspaceTemplateId.value,
        })
        : null;
    if (scope === "seating" && !templateId) {
      return false;
    }

    state.plannerActionError.value = null;
    try {
      const currentDraftId = activeDraftId(state.classWorkspaceSummary.value, scope);
      if (currentDraftId) {
        await plannerState.loadWorkspace(currentDraftId);
      } else {
        await plannerState.resolveDraft(rosterId, templateId, scope);
      }
      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      return true;
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        scope === "seating"
          ? "Kunde inte förbereda sittplatser för delning just nu."
          : "Kunde inte förbereda grupper för delning just nu.",
      );
      return false;
    }
  }

  async function returnToClassWorkspace(): Promise<void> {
    const rosterId = plannerState.roster?.id ?? state.selectedRosterId.value;
    if (!rosterId) {
      await actions.openInitialHomeWorkspace(null);
      return;
    }

    state.plannerActionError.value = null;
    try {
      const result = await flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "Lös sparkonflikten innan du lämnar arbetsytan.",
        fallbackMessage: "Kunde inte lämna arbetsytan just nu.",
      });
      if (result.status === "blocked") {
        state.plannerActionError.value = result.message;
        return;
      }
      state.workspaceNotice.value = null;
      state.workspaceTransitionLabel.value = "Återgår till Översikt...";
      state.currentScreen.value = "class-workspace";
      plannerState.clearWorkspace();
      await actions.loadClassWorkspaceSummary(rosterId);
      state.selectedRosterId.value = rosterId;
      actions.syncWorkspaceTemplateSelection();
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte återvända till klassarbetsytan just nu.",
      );
    } finally {
      state.workspaceTransitionLabel.value = null;
    }
  }

  async function changeWorkspaceTemplate(
    payload: OpenWorkspacePayload,
    draftKind: "grouping" | "seating",
    initialView: PlannerWorkspaceInitialView,
    messages: {
      conflictMessage: string;
      saveFallbackMessage: string;
      actionFallbackMessage: string;
    },
  ): Promise<void> {
    const rosterId = plannerState.roster?.id ?? state.selectedRosterId.value;
    if (!rosterId) {
      return;
    }

    state.plannerActionError.value = null;
    try {
      const result = await flushPlannerRouteShellSave(plannerState, {
        conflictMessage: messages.conflictMessage,
        fallbackMessage: messages.saveFallbackMessage,
      });
      if (result.status === "blocked") {
        state.plannerActionError.value = result.message;
        return;
      }
      await plannerState.resolveDraft(rosterId, payload.templateId, draftKind);
      state.plannerInitialView.value = initialView;
      state.currentScreen.value = "planner";
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        messages.actionFallbackMessage,
      );
    }
  }

  async function changeGroupingTemplate(payload: OpenWorkspacePayload): Promise<void> {
    await changeWorkspaceTemplate(payload, "grouping", "groups", {
      conflictMessage: "Lös sparkonflikten innan du byter gruppkontext.",
      saveFallbackMessage: "Kunde inte spara ändringarna innan gruppkontexten byttes.",
      actionFallbackMessage: "Kunde inte uppdatera gruppkontexten just nu.",
    });
  }

  async function changeGroupingRoster(payload: ChangeGroupingRosterPayload): Promise<void> {
    const nextRosterId = payload.rosterId;
    const currentRosterId = plannerState.roster?.id ?? state.selectedRosterId.value;
    if (!nextRosterId || nextRosterId === currentRosterId) {
      return;
    }

    state.plannerActionError.value = null;
    state.workspaceTransitionLabel.value = "Byter klass...";
    try {
      const result = await flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "Lös sparkonflikten innan du byter klass.",
        fallbackMessage: "Kunde inte spara ändringarna innan klassen byttes.",
      });
      if (result.status === "blocked") {
        state.plannerActionError.value = result.message;
        return;
      }

      state.selectedRosterId.value = nextRosterId;
      await actions.loadClassWorkspaceSummary(nextRosterId);

      const nextGroupingDraftId = activeDraftId(state.classWorkspaceSummary.value, "grouping");
      if (nextGroupingDraftId) {
        await plannerState.loadWorkspace(nextGroupingDraftId);
      } else {
        await plannerState.resolveDraft(nextRosterId, null, "grouping");
      }

      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      actions.syncWorkspaceTemplateSelection();
      state.plannerInitialView.value = "groups";
      state.currentScreen.value = "planner";
      state.workspaceNotice.value = null;
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte byta klass i grupper just nu.",
      );
    } finally {
      state.workspaceTransitionLabel.value = null;
    }
  }

  async function changeSeatingTemplate(payload: OpenWorkspacePayload): Promise<void> {
    await changeWorkspaceTemplate(payload, "seating", "seats", {
      conflictMessage: "Lös sparkonflikten innan du byter klassrum.",
      saveFallbackMessage: "Kunde inte spara ändringarna innan klassrummet byttes.",
      actionFallbackMessage: "Kunde inte byta klassrum för sittplatserna just nu.",
    });
  }

  async function startNewGroupingDraft(payload: OpenWorkspacePayload): Promise<void> {
    const rosterId = plannerState.roster?.id ?? state.selectedRosterId.value;
    if (!rosterId) {
      return;
    }

    state.plannerActionError.value = null;
    try {
      const result = await flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "Lös sparkonflikten innan du startar ett nytt grupputkast.",
        fallbackMessage: "Kunde inte spara ändringarna innan nytt grupputkast startades.",
      });
      if (result.status === "blocked") {
        state.plannerActionError.value = result.message;
        return;
      }
      await plannerState.startNewGroupingDraft(rosterId, payload.templateId);
      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      state.plannerInitialView.value = "groups";
      state.currentScreen.value = "planner";
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte starta ett nytt grupputkast just nu.",
      );
    }
  }

  async function startNewSeatingDraft(payload: StartSeatingDraftPayload): Promise<void> {
    const rosterId = plannerState.roster?.id ?? state.selectedRosterId.value;
    if (!rosterId || state.isSeatingLifecycleBusy.value) {
      return;
    }

    state.plannerActionError.value = null;
    state.isSeatingLifecycleBusy.value = true;
    try {
      const result = await flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "Lös sparkonflikten innan du startar ett nytt sittschema.",
        fallbackMessage: "Kunde inte spara ändringarna innan nytt sittschema startades.",
      });
      if (result.status === "blocked") {
        state.plannerActionError.value = result.message;
        return;
      }
      await plannerState.startNewSeatingDraft(rosterId, payload.templateId);
      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      state.plannerInitialView.value = "seats";
      state.currentScreen.value = "planner";
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte starta ett nytt sittschema just nu.",
      );
    } finally {
      state.isSeatingLifecycleBusy.value = false;
    }
  }

  async function selectPlannerWorkspaceMode(
    mode: "overview" | "grouping" | "seating" | "rules",
  ): Promise<void> {
    if (mode === "overview") {
      await returnToClassWorkspace();
      return;
    }

    if (plannerState.draft) {
      state.plannerActionError.value = null;
      const result = await flushPlannerRouteShellSave(plannerState, {
        conflictMessage: "Lös sparkonflikten innan du byter arbetsyta.",
        fallbackMessage: "Kunde inte byta arbetsyta just nu.",
      });
      if (result.status === "blocked") {
        state.plannerActionError.value = result.message;
        return;
      }
    }

    if (mode === "grouping") {
      await openGroupingWorkspace(
        { templateId: null },
        state.plannerInitialView.value === "rules"
          ? { transitionLabel: "Öppnar Grupper..." }
          : undefined,
      );
      return;
    }

    if (mode === "rules") {
      await openRulesWorkspace();
      return;
    }

    const seatingTemplateId = resolveSeatingWorkspaceTemplateId({
      plannerTemplateId: plannerState.template?.id ?? null,
      activeSeatingTemplateId: state.classWorkspaceSummary.value?.active_seating_draft?.template_id ?? null,
      selectedWorkspaceTemplateId: state.selectedWorkspaceTemplateId.value,
    });
    if (!seatingTemplateId) {
      return;
    }

    await openSeatingWorkspace(
      { templateId: seatingTemplateId },
      state.plannerInitialView.value === "rules"
        ? { transitionLabel: "Öppnar Sittplatser..." }
        : undefined,
    );
  }

  function dismissWorkspaceNotice(): void {
    state.workspaceNotice.value = null;
  }

  return {
    openGroupingWorkspace,
    openSeatingWorkspace,
    openRulesWorkspace,
    changeGroupingRoster,
    changeGroupingTemplate,
    changeSeatingTemplate,
    startNewGroupingDraft,
    startNewSeatingDraft,
    openGroupingHistoryDraft: historyDraftActions.openGroupingHistoryDraft,
    openSeatingHistoryDraft: historyDraftActions.openSeatingHistoryDraft,
    deleteGroupingHistoryDraft: historyDraftActions.deleteGroupingHistoryDraft,
    deleteSeatingHistoryDraft: historyDraftActions.deleteSeatingHistoryDraft,
    prepareOverviewDistributionScope,
    selectPlannerWorkspaceMode,
    dismissWorkspaceNotice,
  };
}
