/**
 * Classroom planner guest overview CRUD orchestration.
 *
 * This module owns checkpoint-2 public overview modal state, delete
 * confirmations, and snapshot-backed roster/template CRUD. The caller provides
 * snapshot persistence so this module stays guest-lane specific and testable.
 */

import type { Ref } from "vue";
import { ref } from "vue";

import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import {
  hydrateGuestSnapshot,
  replaceGuestSnapshotRosters,
  replaceGuestSnapshotTemplates,
} from "./classroomPlannerGuestSnapshotMapping";
import type { RoomTemplate, Roster } from "./classroomPlannerTypes";
import {
  type SaveGuestRosterPayload,
  type SaveGuestTemplatePayload,
  normalizeOverviewSnapshotUiState,
  sortEntriesByName,
} from "./classroomPlannerGuestControllerSupport";

type GuestOverviewCrudState = {
  availableRosters: Ref<Roster[]>;
  availableTemplates: Ref<RoomTemplate[]>;
  selectedRosterId: Ref<string | null>;
  selectedTemplateId: Ref<string | null>;
  plannerActionError: Ref<string | null>;
};

type GuestSnapshotMutationRunner = <T>(input: {
  mutate: (snapshot: ClassroomPlannerGuestSnapshot, updatedAt: string) => {
    nextSnapshot: ClassroomPlannerGuestSnapshot;
    result: T;
  };
}) => Promise<T>;

type GuestOverviewCrudActions = {
  persistSnapshotMutation: GuestSnapshotMutationRunner;
};

export function createClassroomPlannerGuestOverviewCrudFlow(
  state: GuestOverviewCrudState,
  actions: GuestOverviewCrudActions,
) {
  const isRosterModalOpen = ref(false);
  const isTemplateModalOpen = ref(false);
  const activeRosterModal = ref<Roster | null>(null);
  const activeTemplateModal = ref<RoomTemplate | null>(null);
  const overviewDeleteRosterTarget = ref<Roster | null>(null);
  const overviewDeleteTemplateTarget = ref<RoomTemplate | null>(null);
  const overviewDeleteRosterError = ref<string | null>(null);
  const overviewDeleteTemplateError = ref<string | null>(null);
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

  function closeOverviewRosterDelete(): void {
    if (isDeletingOverviewRoster.value) {
      return;
    }
    overviewDeleteRosterError.value = null;
    overviewDeleteRosterTarget.value = null;
  }

  function closeOverviewTemplateDelete(): void {
    if (isDeletingOverviewTemplate.value) {
      return;
    }
    overviewDeleteTemplateError.value = null;
    overviewDeleteTemplateTarget.value = null;
  }

  function openRosterCreate(): void {
    activeRosterModal.value = null;
    isRosterModalOpen.value = true;
  }

  function openSelectedRosterEdit(): void {
    const selectedRoster = state.availableRosters.value.find((roster) => roster.id === state.selectedRosterId.value) ?? null;
    if (!selectedRoster) {
      return;
    }
    activeRosterModal.value = selectedRoster;
    isRosterModalOpen.value = true;
  }

  function openSelectedRosterDelete(): void {
    const selectedRoster = state.availableRosters.value.find((roster) => roster.id === state.selectedRosterId.value) ?? null;
    if (!selectedRoster) {
      return;
    }
    overviewDeleteRosterError.value = null;
    overviewDeleteRosterTarget.value = selectedRoster;
  }

  function openTemplateCreate(): void {
    activeTemplateModal.value = null;
    isTemplateModalOpen.value = true;
  }

  function openOverviewTemplateEdit(template?: RoomTemplate): void {
    const selectedTemplate =
      template
      ?? state.availableTemplates.value.find((entry) => entry.id === state.selectedTemplateId.value)
      ?? null;
    if (!selectedTemplate) {
      return;
    }
    activeTemplateModal.value = selectedTemplate;
    isTemplateModalOpen.value = true;
  }

  function openSelectedTemplateDelete(): void {
    const selectedTemplate = state.availableTemplates.value.find((template) => template.id === state.selectedTemplateId.value) ?? null;
    if (!selectedTemplate) {
      return;
    }
    overviewDeleteTemplateError.value = null;
    overviewDeleteTemplateTarget.value = selectedTemplate;
  }

  async function saveRoster(payload: SaveGuestRosterPayload): Promise<Roster> {
    state.plannerActionError.value = null;
    const roster: Roster = {
      id: payload.existingRoster?.id ?? crypto.randomUUID(),
      name: payload.name,
      students: payload.students,
    };

    return await actions.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        const hydratedSnapshot = hydrateGuestSnapshot(snapshot);
        const nextSnapshot = normalizeOverviewSnapshotUiState(
          replaceGuestSnapshotRosters(
            snapshot,
            sortEntriesByName([
              ...hydratedSnapshot.rosters.filter((entry) => entry.id !== roster.id),
              roster,
            ]),
            { updated_at: updatedAt },
          ),
          {
            preferredRosterId: roster.id,
            preferredTemplateId: snapshot.ui_state.selected_template_local_id,
            updatedAt,
          },
        );

        return {
          nextSnapshot,
          result: roster,
        };
      },
    });
  }

  async function deleteRoster(rosterId: string): Promise<void> {
    state.plannerActionError.value = null;
    await actions.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        const hydratedSnapshot = hydrateGuestSnapshot(snapshot);
        const nextSnapshot = normalizeOverviewSnapshotUiState(
          replaceGuestSnapshotRosters(
            snapshot,
            hydratedSnapshot.rosters.filter((roster) => roster.id !== rosterId),
            { updated_at: updatedAt },
          ),
          {
            preferredRosterId:
              snapshot.ui_state.selected_roster_local_id === rosterId
                ? null
                : snapshot.ui_state.selected_roster_local_id,
            preferredTemplateId: snapshot.ui_state.selected_template_local_id,
            updatedAt,
          },
        );

        return {
          nextSnapshot,
          result: undefined,
        };
      },
    });
  }

  async function saveTemplate(payload: SaveGuestTemplatePayload): Promise<RoomTemplate> {
    state.plannerActionError.value = null;
    const template: RoomTemplate = {
      id: payload.existingTemplate?.id ?? crypto.randomUUID(),
      name: payload.name,
      grid_cols: payload.grid_cols,
      grid_rows: payload.grid_rows,
      seats: payload.seats,
      fixtures: payload.fixtures,
    };

    return await actions.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        const hydratedSnapshot = hydrateGuestSnapshot(snapshot);
        const nextSnapshot = normalizeOverviewSnapshotUiState(
          replaceGuestSnapshotTemplates(
            snapshot,
            sortEntriesByName([
              ...hydratedSnapshot.templates.filter((entry) => entry.id !== template.id),
              template,
            ]),
            { updated_at: updatedAt },
          ),
          {
            preferredRosterId: snapshot.ui_state.selected_roster_local_id,
            preferredTemplateId: template.id,
            updatedAt,
          },
        );

        return {
          nextSnapshot,
          result: template,
        };
      },
    });
  }

  async function deleteTemplate(templateId: string): Promise<void> {
    state.plannerActionError.value = null;
    await actions.persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        const hydratedSnapshot = hydrateGuestSnapshot(snapshot);
        const nextSnapshot = normalizeOverviewSnapshotUiState(
          replaceGuestSnapshotTemplates(
            snapshot,
            hydratedSnapshot.templates.filter((template) => template.id !== templateId),
            { updated_at: updatedAt },
          ),
          {
            preferredRosterId: snapshot.ui_state.selected_roster_local_id,
            preferredTemplateId:
              snapshot.ui_state.selected_template_local_id === templateId
                ? null
                : snapshot.ui_state.selected_template_local_id,
            updatedAt,
            preserveExplicitTemplateNull: snapshot.ui_state.selected_template_local_id === templateId,
          },
        );

        return {
          nextSnapshot,
          result: undefined,
        };
      },
    });
  }

  function applySavedRoster(): void {
    closeRosterModal();
  }

  function applyDeletedRoster(): void {
    closeRosterModal();
  }

  function applySavedTemplate(): void {
    closeTemplateModal();
  }

  function applyDeletedTemplate(): void {
    closeTemplateModal();
  }

  async function confirmOverviewRosterDelete(): Promise<void> {
    if (!overviewDeleteRosterTarget.value) {
      return;
    }

    isDeletingOverviewRoster.value = true;
    overviewDeleteRosterError.value = null;
    try {
      await deleteRoster(overviewDeleteRosterTarget.value.id);
      overviewDeleteRosterTarget.value = null;
    } catch (error: unknown) {
      overviewDeleteRosterError.value = error instanceof Error
        ? error.message
        : "Kunde inte ta bort klasslistan i den publika arbetsytan.";
    } finally {
      isDeletingOverviewRoster.value = false;
    }
  }

  async function confirmOverviewTemplateDelete(): Promise<void> {
    if (!overviewDeleteTemplateTarget.value) {
      return;
    }

    isDeletingOverviewTemplate.value = true;
    overviewDeleteTemplateError.value = null;
    try {
      await deleteTemplate(overviewDeleteTemplateTarget.value.id);
      overviewDeleteTemplateTarget.value = null;
    } catch (error: unknown) {
      overviewDeleteTemplateError.value = error instanceof Error
        ? error.message
        : "Kunde inte ta bort klassrummet i den publika arbetsytan.";
    } finally {
      isDeletingOverviewTemplate.value = false;
    }
  }

  return {
    isRosterModalOpen,
    isTemplateModalOpen,
    activeRosterModal,
    activeTemplateModal,
    overviewDeleteRosterTarget,
    overviewDeleteTemplateTarget,
    overviewDeleteRosterError,
    overviewDeleteTemplateError,
    isDeletingOverviewRoster,
    isDeletingOverviewTemplate,
    openRosterCreate,
    closeRosterModal,
    openSelectedRosterEdit,
    openSelectedRosterDelete,
    openTemplateCreate,
    closeTemplateModal,
    openOverviewTemplateEdit,
    openSelectedTemplateDelete,
    closeOverviewRosterDelete,
    closeOverviewTemplateDelete,
    saveRoster,
    deleteRoster,
    saveTemplate,
    deleteTemplate,
    applySavedRoster,
    applyDeletedRoster,
    applySavedTemplate,
    applyDeletedTemplate,
    confirmOverviewRosterDelete,
    confirmOverviewTemplateDelete,
  };
}
