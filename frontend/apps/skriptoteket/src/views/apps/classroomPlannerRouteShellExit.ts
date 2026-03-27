/**
 * Classroom planner route-shell exit orchestration.
 *
 * This module owns trusted-entry detection plus the exit confirmation flow used
 * when Klassrumskartan returns the teacher to the dashboard or catalog.
 */

import type { Ref } from "vue";
import { ref } from "vue";
import type { Router } from "vue-router";

import {
  type ClassroomPlannerEntryOrigin,
  isReloadNavigation,
  readClassroomPlannerEntryOriginFromHistoryState,
  resolveClassroomPlannerExitTarget,
} from "./classroomPlannerNavigation";
import type { PlannerScreen } from "./classroomPlannerOverviewStore";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";

type ClassroomPlannerExitFlowOptions = {
  plannerActionError: Ref<string | null>;
  currentScreen: Ref<PlannerScreen>;
  router: Pick<Router, "replace">;
  plannerState: {
    prepareForPlannerExit: () => Promise<
      | { status: "saved" }
      | { status: "blocked"; reason: "conflict" | "error"; message: string }
      | { status: "confirm-discard" }
    >;
    discardPendingSessionWork: () => void;
    clearWorkspace: () => void;
  };
  clearOverviewWorkspaceState: () => void;
};

export function createClassroomPlannerExitFlow(options: ClassroomPlannerExitFlowOptions) {
  const entryOrigin = ref<ClassroomPlannerEntryOrigin | null>(null);
  const isExitConfirmationOpen = ref(false);
  const isExitingWithoutSave = ref(false);

  function readCurrentEntryOrigin(): ClassroomPlannerEntryOrigin | null {
    const navigationEntries = window.performance.getEntriesByType("navigation").filter(
      (entry): entry is PerformanceNavigationTiming => typeof (entry as { type?: unknown }).type === "string",
    );
    if (isReloadNavigation(navigationEntries)) {
      return null;
    }

    return readClassroomPlannerEntryOriginFromHistoryState(window.history.state);
  }

  async function finishExitToEntryOrigin(): Promise<void> {
    options.plannerState.clearWorkspace();
    options.clearOverviewWorkspaceState();
    options.currentScreen.value = "class-workspace";
    await options.router.replace(resolveClassroomPlannerExitTarget(entryOrigin.value));
  }

  function initializeEntryOrigin(): void {
    entryOrigin.value = readCurrentEntryOrigin();
  }

  function closeExitConfirmation(): void {
    if (isExitingWithoutSave.value) {
      return;
    }
    isExitConfirmationOpen.value = false;
  }

  async function confirmExitWithoutWaiting(): Promise<void> {
    isExitingWithoutSave.value = true;
    options.plannerActionError.value = null;
    try {
      options.plannerState.discardPendingSessionWork();
      await finishExitToEntryOrigin();
    } catch (error: unknown) {
      options.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte lämna Klassrumskartan just nu.",
      );
    } finally {
      isExitingWithoutSave.value = false;
      isExitConfirmationOpen.value = false;
    }
  }

  async function exitPlannerApp(): Promise<void> {
    options.plannerActionError.value = null;
    try {
      const exitSaveResult = await options.plannerState.prepareForPlannerExit();
      if (exitSaveResult.status === "blocked") {
        options.plannerActionError.value = exitSaveResult.message;
        return;
      }

      if (exitSaveResult.status === "confirm-discard") {
        isExitConfirmationOpen.value = true;
        return;
      }

      await finishExitToEntryOrigin();
    } catch (error: unknown) {
      options.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte lämna Klassrumskartan just nu.",
      );
    }
  }

  return {
    isExitConfirmationOpen,
    isExitingWithoutSave,
    initializeEntryOrigin,
    closeExitConfirmation,
    confirmExitWithoutWaiting,
    exitPlannerApp,
  };
}
