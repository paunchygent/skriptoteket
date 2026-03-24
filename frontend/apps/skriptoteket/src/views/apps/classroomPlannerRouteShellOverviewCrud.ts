/**
 * Classroom planner route-shell overview CRUD and modal orchestration.
 *
 * This module owns overview-local roster/classroom modal state plus delete
 * confirmations so the main route-shell composable can stay focused on wiring.
 */

import type { Ref } from "vue";
import { ref } from "vue";

import {
  deleteClassroomPlannerRoster,
  deleteClassroomPlannerTemplate,
} from "./classroomPlannerCatalogApi";
import type { PlannerScreen } from "./classroomPlannerOverviewStore";
import { normalizeClassroomPlannerUiError } from "./classroomPlannerRouteShellErrors";
import type { ClassWorkspaceSummary, RoomTemplate, Roster } from "./classroomPlannerTypes";

type ClassroomPlannerOverviewCrudState = {
  availableRosters: Ref<Roster[]>;
  availableTemplates: Ref<RoomTemplate[]>;
  selectedRosterId: Ref<string | null>;
  selectedWorkspaceTemplateId: Ref<string | null>;
  currentScreen: Ref<PlannerScreen>;
  classWorkspaceSummary: Ref<ClassWorkspaceSummary | null>;
  plannerActionError: Ref<string | null>;
};

type ClassroomPlannerOverviewCrudActions = {
  openClassWorkspace: (rosterId: string) => Promise<void>;
  openInitialHomeWorkspace: (preferredRosterId: string | null) => Promise<void>;
  syncWorkspaceTemplateSelection: (options?: { preserveCurrent?: boolean }) => void;
};

export function createClassroomPlannerOverviewCrudFlow(
  state: ClassroomPlannerOverviewCrudState,
  actions: ClassroomPlannerOverviewCrudActions,
) {
  const isRosterModalOpen = ref(false);
  const isTemplateModalOpen = ref(false);
  const activeRosterModal = ref<Roster | null>(null);
  const activeTemplateModal = ref<RoomTemplate | null>(null);
  const overviewDeleteRosterTarget = ref<Roster | null>(null);
  const overviewDeleteTemplateTarget = ref<RoomTemplate | null>(null);
  const isDeletingOverviewRoster = ref(false);
  const isDeletingOverviewTemplate = ref(false);

  function closeRosterModal(): void {
    isRosterModalOpen.value = false;
    activeRosterModal.value = null;
  }

  function closeTemplateModal(): void {
    isTemplateModalOpen.value = false;
    activeTemplateModal.value = null;
  }

  async function upsertRoster(roster: Roster): Promise<void> {
    const wasCreatingRoster = activeRosterModal.value === null;
    const wasEditingCurrentRoster = activeRosterModal.value?.id === state.classWorkspaceSummary.value?.roster.id;
    const next = state.availableRosters.value.filter((item) => item.id !== roster.id);
    state.availableRosters.value = [...next, roster].sort((left, right) => left.name.localeCompare(right.name, "sv"));
    if (wasEditingCurrentRoster && state.classWorkspaceSummary.value) {
      state.classWorkspaceSummary.value = {
        ...state.classWorkspaceSummary.value,
        roster: {
          ...state.classWorkspaceSummary.value.roster,
          name: roster.name,
          student_count: roster.students.length,
        },
      };
      state.selectedRosterId.value = roster.id;
    } else if (state.currentScreen.value !== "class-workspace") {
      state.selectedRosterId.value = roster.id;
    }
    closeRosterModal();

    if (state.currentScreen.value === "class-workspace" && wasCreatingRoster) {
      await actions.openClassWorkspace(roster.id);
    }
  }

  async function removeRosterFromOverview(rosterId: string): Promise<void> {
    state.availableRosters.value = state.availableRosters.value.filter((roster) => roster.id !== rosterId);
    if (state.selectedRosterId.value === rosterId) {
      await actions.openInitialHomeWorkspace(null);
    }
    closeRosterModal();
  }

  function closeOverviewRosterDelete(): void {
    if (isDeletingOverviewRoster.value) {
      return;
    }
    overviewDeleteRosterTarget.value = null;
  }

  function upsertTemplate(template: RoomTemplate): void {
    const next = state.availableTemplates.value.filter((item) => item.id !== template.id);
    state.availableTemplates.value = [...next, template].sort((left, right) => left.name.localeCompare(right.name, "sv"));
    state.selectedWorkspaceTemplateId.value = template.id;
    closeTemplateModal();
  }

  function removeTemplateFromOverview(templateId: string): void {
    state.availableTemplates.value = state.availableTemplates.value.filter((template) => template.id !== templateId);
    if (state.selectedWorkspaceTemplateId.value === templateId) {
      state.selectedWorkspaceTemplateId.value = null;
      actions.syncWorkspaceTemplateSelection();
    }
    closeTemplateModal();
  }

  function closeOverviewTemplateDelete(): void {
    if (isDeletingOverviewTemplate.value) {
      return;
    }
    overviewDeleteTemplateTarget.value = null;
  }

  function openRosterCreate(): void {
    activeRosterModal.value = null;
    isRosterModalOpen.value = true;
  }

  function openSelectedRosterEdit(): void {
    const activeRoster = state.availableRosters.value.find((roster) => roster.id === state.selectedRosterId.value) ?? null;
    if (!activeRoster) {
      return;
    }
    activeRosterModal.value = activeRoster;
    isRosterModalOpen.value = true;
  }

  function openSelectedRosterDelete(): void {
    const selectedRoster = state.availableRosters.value.find((roster) => roster.id === state.selectedRosterId.value) ?? null;
    if (!selectedRoster) {
      return;
    }
    overviewDeleteRosterTarget.value = selectedRoster;
  }

  function openTemplateCreate(): void {
    activeTemplateModal.value = null;
    isTemplateModalOpen.value = true;
  }

  function selectWorkspaceRoster(rosterId: string): void {
    if (rosterId === state.selectedRosterId.value) {
      return;
    }
    void actions.openClassWorkspace(rosterId);
  }

  function selectWorkspaceTemplate(templateId: string | null): void {
    state.selectedWorkspaceTemplateId.value = templateId;
  }

  function openOverviewTemplateEdit(template?: RoomTemplate): void {
    const nextTemplate =
      template
      ?? state.availableTemplates.value.find(
        (item) => item.id === state.selectedWorkspaceTemplateId.value,
      )
      ?? null;
    if (!nextTemplate) {
      return;
    }
    activeTemplateModal.value = nextTemplate;
    isTemplateModalOpen.value = true;
  }

  function openSelectedTemplateDelete(): void {
    const selectedTemplate = state.availableTemplates.value.find(
      (template) => template.id === state.selectedWorkspaceTemplateId.value,
    );
    if (!selectedTemplate) {
      return;
    }
    overviewDeleteTemplateTarget.value = selectedTemplate;
  }

  async function confirmOverviewTemplateDelete(): Promise<void> {
    if (!overviewDeleteTemplateTarget.value) {
      return;
    }

    isDeletingOverviewTemplate.value = true;
    state.plannerActionError.value = null;
    try {
      await deleteClassroomPlannerTemplate(overviewDeleteTemplateTarget.value.id);
      removeTemplateFromOverview(overviewDeleteTemplateTarget.value.id);
      overviewDeleteTemplateTarget.value = null;
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte ta bort klassrummet just nu.",
      );
    } finally {
      isDeletingOverviewTemplate.value = false;
    }
  }

  async function confirmOverviewRosterDelete(): Promise<void> {
    if (!overviewDeleteRosterTarget.value) {
      return;
    }

    isDeletingOverviewRoster.value = true;
    state.plannerActionError.value = null;
    try {
      await deleteClassroomPlannerRoster(overviewDeleteRosterTarget.value.id);
      await removeRosterFromOverview(overviewDeleteRosterTarget.value.id);
      overviewDeleteRosterTarget.value = null;
    } catch (error: unknown) {
      state.plannerActionError.value = normalizeClassroomPlannerUiError(
        error,
        "Kunde inte ta bort klasslistan just nu.",
      );
    } finally {
      isDeletingOverviewRoster.value = false;
    }
  }

  return {
    isRosterModalOpen,
    isTemplateModalOpen,
    activeRosterModal,
    activeTemplateModal,
    overviewDeleteRosterTarget,
    overviewDeleteTemplateTarget,
    isDeletingOverviewRoster,
    isDeletingOverviewTemplate,
    upsertRoster,
    removeRosterFromOverview,
    closeOverviewRosterDelete,
    upsertTemplate,
    removeTemplateFromOverview,
    closeOverviewTemplateDelete,
    openRosterCreate,
    closeRosterModal,
    openSelectedRosterEdit,
    openSelectedRosterDelete,
    openTemplateCreate,
    closeTemplateModal,
    selectWorkspaceRoster,
    selectWorkspaceTemplate,
    openOverviewTemplateEdit,
    openSelectedTemplateDelete,
    confirmOverviewTemplateDelete,
    confirmOverviewRosterDelete,
  };
}
