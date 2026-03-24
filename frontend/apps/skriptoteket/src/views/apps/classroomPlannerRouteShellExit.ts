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
import { flushPlannerRouteShellSaveForExit } from "./classroomPlannerRouteShellSaveGuards";
import type { PlannerRouteShellSaveController } from "./classroomPlannerRouteShellSaveGuards";

const EXIT_AUTOSAVE_TIMEOUT_MS = 1500;

type ClassroomPlannerExitFlowOptions = {
  plannerActionError: Ref<string | null>;
  currentScreen: Ref<PlannerScreen>;
  router: Pick<Router, "replace">;
  plannerState: PlannerRouteShellSaveController & {
    cancelPendingSave: () => void;
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
      options.plannerState.cancelPendingSave();
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
      const exitSaveResult = await flushPlannerRouteShellSaveForExit(
        options.plannerState,
        EXIT_AUTOSAVE_TIMEOUT_MS,
      );
      if (exitSaveResult === "blocked") {
        options.plannerActionError.value =
          options.plannerState.saveStatus === "conflict"
            ? "Lös sparkonflikten innan du avslutar Klassrumskartan."
            : options.plannerState.saveMessage ?? "Kunde inte avsluta Klassrumskartan just nu.";
        return;
      }

      if (exitSaveResult === "timed-out") {
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
