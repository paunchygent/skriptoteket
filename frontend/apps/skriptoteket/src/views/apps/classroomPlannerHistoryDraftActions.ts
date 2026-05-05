/**
 * Historical draft lifecycle actions for Klassrumskartan.
 *
 * These actions open or delete saved grouping and seating drafts while keeping
 * route-shell state, busy flags, and transient failure toasts consistent.
 */

import type { Ref } from "vue";

import type { useToast } from "../../composables/useToast";
import type { PlannerScreen, PlannerWorkspaceInitialView } from "./classroomPlannerOverviewStore";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

type HistoryDraftState = {
  selectedRosterId: Ref<string | null>;
  currentScreen: Ref<PlannerScreen>;
  plannerInitialView: Ref<PlannerWorkspaceInitialView>;
  plannerActionError: Ref<string | null>;
  classWorkspaceSummary: Ref<ClassWorkspaceSummary | null>;
  isSeatingLifecycleBusy: Ref<boolean>;
  busySeatingHistoryDraftId: Ref<string | null>;
};

type HistoryDraftActions = {
  loadClassWorkspaceSummary: (rosterId: string) => Promise<void>;
  refreshClassWorkspaceSummaryForSelectedRoster: () => Promise<void>;
};

type HistoryDraftPlannerState = {
  activateGroupingHistoryDraft: (draftId: string) => Promise<unknown>;
  activateSeatingHistoryDraft: (draftId: string) => Promise<unknown>;
  deleteGroupingHistoryDraft: (draftId: string) => Promise<unknown>;
  deleteSeatingHistoryDraft: (draftId: string) => Promise<unknown>;
};

type ToastApi = ReturnType<typeof useToast>;

function currentRosterId(state: HistoryDraftState): string | null {
  return state.selectedRosterId.value ?? state.classWorkspaceSummary.value?.roster.id ?? null;
}

export function createClassroomPlannerHistoryDraftActions(
  state: HistoryDraftState,
  actions: HistoryDraftActions,
  plannerState: HistoryDraftPlannerState,
  toast: ToastApi,
) {
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
    const rosterId = currentRosterId(state);
    if (!rosterId) {
      return;
    }

    state.plannerActionError.value = null;
    try {
      await plannerState.deleteGroupingHistoryDraft(draftId);
      await actions.loadClassWorkspaceSummary(rosterId);
    } catch (error: unknown) {
      toast.failure(
        normalizeClassroomPlannerUiError(
          error,
          "Det gick inte att ta bort det historiska grupputkastet. Försök igen.",
        ),
      );
    }
  }

  async function deleteSeatingHistoryDraft(draftId: string): Promise<void> {
    const rosterId = currentRosterId(state);
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
      toast.failure(
        normalizeClassroomPlannerUiError(
          error,
          "Det gick inte att ta bort det historiska sittschemat. Försök igen.",
        ),
      );
    } finally {
      state.busySeatingHistoryDraftId.value = null;
      state.isSeatingLifecycleBusy.value = false;
    }
  }

  return {
    openGroupingHistoryDraft,
    openSeatingHistoryDraft,
    deleteGroupingHistoryDraft,
    deleteSeatingHistoryDraft,
  };
}
