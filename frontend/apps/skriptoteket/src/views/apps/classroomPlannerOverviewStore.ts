/**
 * Classroom planner overview/catalog Pinia store.
 *
 * This store owns Klassrumskartan's non-draft route-shell state: roster and
 * classroom catalogs, overview selection, current overview summary, shell-level
 * loading/errors, and the dismiss state for resumable overview cards.
 */

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import type {
  ClassWorkspaceSummary,
  RoomTemplate,
  Roster,
} from "./classroomPlannerTypes";

export type PlannerScreen = "class-workspace" | "planner";
export type PlannerWorkspaceInitialView = "groups" | "seats";

export const useClassroomPlannerOverviewStore = defineStore("classroom-planner-overview", () => {
  const availableRosters = ref<Roster[]>([]);
  const availableTemplates = ref<RoomTemplate[]>([]);
  const selectedRosterId = ref<string | null>(null);
  const selectedWorkspaceTemplateId = ref<string | null>(null);
  const currentScreen = ref<PlannerScreen>("class-workspace");
  const plannerInitialView = ref<PlannerWorkspaceInitialView>("groups");
  const isBootstrapping = ref(true);
  const isLoadingClassWorkspace = ref(false);
  const bootstrapError = ref<string | null>(null);
  const plannerActionError = ref<string | null>(null);
  const dismissedOverviewGroupingDraftId = ref<string | null>(null);
  const dismissedOverviewSeatingDraftId = ref<string | null>(null);
  const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>(null);

  const visibleOverviewGroupingDraft = computed(() => {
    const draft = classWorkspaceSummary.value?.active_grouping_draft ?? null;
    if (!draft || dismissedOverviewGroupingDraftId.value === draft.id) {
      return null;
    }
    return draft;
  });

  const visibleOverviewSeatingDraft = computed(() => {
    const draft = classWorkspaceSummary.value?.active_seating_draft ?? null;
    if (!draft || dismissedOverviewSeatingDraftId.value === draft.id) {
      return null;
    }
    return draft;
  });

  function reset(): void {
    availableRosters.value = [];
    availableTemplates.value = [];
    selectedRosterId.value = null;
    selectedWorkspaceTemplateId.value = null;
    currentScreen.value = "class-workspace";
    plannerInitialView.value = "groups";
    isBootstrapping.value = true;
    isLoadingClassWorkspace.value = false;
    bootstrapError.value = null;
    plannerActionError.value = null;
    dismissedOverviewGroupingDraftId.value = null;
    dismissedOverviewSeatingDraftId.value = null;
    classWorkspaceSummary.value = null;
  }

  function setCatalog(rosters: Roster[], templates: RoomTemplate[]): void {
    availableRosters.value = rosters;
    availableTemplates.value = templates;
  }

  function clearOverviewWorkspaceState(): void {
    selectedRosterId.value = null;
    classWorkspaceSummary.value = null;
    selectedWorkspaceTemplateId.value = null;
    dismissedOverviewGroupingDraftId.value = null;
    dismissedOverviewSeatingDraftId.value = null;
  }

  function resolveHomeRosterId(preferredRosterId: string | null): string | null {
    if (preferredRosterId && availableRosters.value.some((roster) => roster.id === preferredRosterId)) {
      return preferredRosterId;
    }

    if (selectedRosterId.value && availableRosters.value.some((roster) => roster.id === selectedRosterId.value)) {
      return selectedRosterId.value;
    }

    return availableRosters.value[0]?.id ?? null;
  }

  function syncWorkspaceTemplateSelection(options?: { preserveCurrent?: boolean }): void {
    const preserveCurrent = options?.preserveCurrent ?? false;
    if (
      preserveCurrent
      && selectedWorkspaceTemplateId.value
      && availableTemplates.value.some((template) => template.id === selectedWorkspaceTemplateId.value)
    ) {
      return;
    }

    const activeTemplateId = classWorkspaceSummary.value?.active_seating_draft?.template_id ?? null;
    const hasActiveTemplate =
      activeTemplateId !== null
      && availableTemplates.value.some((template) => template.id === activeTemplateId);
    selectedWorkspaceTemplateId.value = hasActiveTemplate ? activeTemplateId : null;
  }

  function dismissOverviewGroupingDraft(): void {
    const draftId = classWorkspaceSummary.value?.active_grouping_draft?.id ?? null;
    if (!draftId) {
      return;
    }
    dismissedOverviewGroupingDraftId.value = draftId;
  }

  function dismissOverviewSeatingDraft(): void {
    const draftId = classWorkspaceSummary.value?.active_seating_draft?.id ?? null;
    if (!draftId) {
      return;
    }
    dismissedOverviewSeatingDraftId.value = draftId;
  }

  return {
    availableRosters,
    availableTemplates,
    selectedRosterId,
    selectedWorkspaceTemplateId,
    currentScreen,
    plannerInitialView,
    isBootstrapping,
    isLoadingClassWorkspace,
    bootstrapError,
    plannerActionError,
    dismissedOverviewGroupingDraftId,
    dismissedOverviewSeatingDraftId,
    classWorkspaceSummary,
    visibleOverviewGroupingDraft,
    visibleOverviewSeatingDraft,
    reset,
    setCatalog,
    clearOverviewWorkspaceState,
    resolveHomeRosterId,
    syncWorkspaceTemplateSelection,
    dismissOverviewGroupingDraft,
    dismissOverviewSeatingDraft,
  };
});
