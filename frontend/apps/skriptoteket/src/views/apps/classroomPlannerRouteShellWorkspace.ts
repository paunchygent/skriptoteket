/**
 * Classroom planner route-shell workspace transitions.
 *
 * This module owns transitions between overview, grouping, and seating
 * workspaces, including save guards and history lifecycle actions.
 */

import type { Ref } from "vue";

import type { PlannerScreen, PlannerWorkspaceInitialView } from "./classroomPlannerOverviewStore";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import { flushPlannerRouteShellSave } from "./classroomPlannerRouteShellSaveGuards";
import type { PlannerRouteShellSaveController } from "./classroomPlannerRouteShellSaveGuards";
import type { ClassWorkspaceSummary, PlanDraftSummary } from "./classroomPlannerTypes";

type PlannerRouteShellWorkspaceState = {
  selectedRosterId: Ref<string | null>;
  currentScreen: Ref<PlannerScreen>;
  plannerInitialView: Ref<PlannerWorkspaceInitialView>;
  plannerActionError: Ref<string | null>;
  classWorkspaceSummary: Ref<ClassWorkspaceSummary | null>;
  isSeatingLifecycleBusy: Ref<boolean>;
  busySeatingHistoryDraftId: Ref<string | null>;
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

function activeDraftId(
  summary: ClassWorkspaceSummary | null,
  draftKind: "grouping" | "seating",
): string | null {
  const draft: PlanDraftSummary | null =
    draftKind === "grouping"
      ? (summary?.active_grouping_draft ?? null)
      : (summary?.active_seating_draft ?? null);
  return draft?.id ?? null;
}

export function createClassroomPlannerWorkspaceFlow(
  state: PlannerRouteShellWorkspaceState,
  actions: PlannerRouteShellWorkspaceActions,
  plannerState: PlannerRouteShellWorkspacePlannerState,
) {
  async function openWorkspace(
    payload: OpenWorkspacePayload,
    draftKind: "grouping" | "seating",
    initialView: PlannerWorkspaceInitialView,
    fallbackMessage: string,
  ): Promise<void> {
    if (!state.selectedRosterId.value) {
      return;
    }

    state.plannerActionError.value = null;
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
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(error, fallbackMessage);
    }
  }

  async function openGroupingWorkspace(payload: OpenWorkspacePayload): Promise<void> {
    await openWorkspace(payload, "grouping", "groups", "Kunde inte öppna grupparbetsytan just nu.");
  }

  async function openSeatingWorkspace(payload: OpenWorkspacePayload): Promise<void> {
    await openWorkspace(payload, "seating", "seats", "Kunde inte öppna sittplatserna just nu.");
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
      plannerState.clearWorkspace();
      await actions.loadClassWorkspaceSummary(rosterId);
      state.selectedRosterId.value = rosterId;
      actions.syncWorkspaceTemplateSelection();
      state.currentScreen.value = "class-workspace";
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte återvända till klassarbetsytan just nu.",
      );
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

  async function openGroupingHistoryDraft(draftId: string): Promise<void> {
    state.plannerActionError.value = null;
    try {
      await plannerState.activateGroupingHistoryDraft(draftId);
      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      state.plannerInitialView.value = "groups";
      state.currentScreen.value = "planner";
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte öppna det historiska grupputkastet just nu.",
      );
    }
  }

  async function openSeatingHistoryDraft(draftId: string): Promise<void> {
    if (state.isSeatingLifecycleBusy.value) {
      return;
    }
    state.plannerActionError.value = null;
    state.isSeatingLifecycleBusy.value = true;
    state.busySeatingHistoryDraftId.value = draftId;
    try {
      await plannerState.activateSeatingHistoryDraft(draftId);
      await actions.refreshClassWorkspaceSummaryForSelectedRoster();
      state.plannerInitialView.value = "seats";
      state.currentScreen.value = "planner";
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte öppna det historiska sittschemat just nu.",
      );
    } finally {
      state.busySeatingHistoryDraftId.value = null;
      state.isSeatingLifecycleBusy.value = false;
    }
  }

  async function deleteGroupingHistoryDraft(draftId: string): Promise<void> {
    const rosterId = state.selectedRosterId.value ?? state.classWorkspaceSummary.value?.roster.id ?? null;
    if (!rosterId) {
      return;
    }

    state.plannerActionError.value = null;
    try {
      await plannerState.deleteGroupingHistoryDraft(draftId);
      await actions.loadClassWorkspaceSummary(rosterId);
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte ta bort det historiska grupputkastet just nu.",
      );
    }
  }

  async function deleteSeatingHistoryDraft(draftId: string): Promise<void> {
    const rosterId = state.selectedRosterId.value ?? state.classWorkspaceSummary.value?.roster.id ?? null;
    if (!rosterId || state.isSeatingLifecycleBusy.value) {
      return;
    }

    state.plannerActionError.value = null;
    state.isSeatingLifecycleBusy.value = true;
    state.busySeatingHistoryDraftId.value = draftId;
    try {
      await plannerState.deleteSeatingHistoryDraft(draftId);
      await actions.loadClassWorkspaceSummary(rosterId);
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte ta bort det historiska sittschemat just nu.",
      );
    } finally {
      state.busySeatingHistoryDraftId.value = null;
      state.isSeatingLifecycleBusy.value = false;
    }
  }

  async function selectPlannerWorkspaceMode(mode: "overview" | "grouping" | "seating"): Promise<void> {
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
      await openGroupingWorkspace({ templateId: null });
      return;
    }

    await openSeatingWorkspace({ templateId: null });
  }

  return {
    openGroupingWorkspace,
    openSeatingWorkspace,
    changeGroupingTemplate,
    changeSeatingTemplate,
    startNewGroupingDraft,
    startNewSeatingDraft,
    openGroupingHistoryDraft,
    openSeatingHistoryDraft,
    deleteGroupingHistoryDraft,
    deleteSeatingHistoryDraft,
    selectPlannerWorkspaceMode,
  };
}
