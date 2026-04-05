/**
 * Classroom planner guest overview shell.
 *
 * This composable owns checkpoint-1 public Klassrumskartan orchestration. It
 * bootstraps the browser-owned guest snapshot, normalizes the public route to
 * the overview-only lane, and exposes the shared overview presentation state
 * without touching the authenticated route shell or owner-scoped APIs.
 */

import { computed, onMounted, ref } from "vue";

import type { ClassroomPlannerOverviewCapabilities } from "./classroomPlannerOverviewCapabilities";
import { createClassroomPlannerGuestStorage } from "./classroomPlannerGuestStorage";
import {
  hydrateGuestSnapshot,
  replaceGuestSnapshotUiState,
} from "./classroomPlannerGuestSnapshotMapping";
import type {
  ClassWorkspaceSummary,
  RoomTemplate,
  Roster,
} from "./classroomPlannerTypes";

type ClassroomPlannerGuestStorageAdapter = ReturnType<typeof createClassroomPlannerGuestStorage>;

const CHECKPOINT_ONE_OVERVIEW_CAPABILITIES: ClassroomPlannerOverviewCapabilities = {
  show_grouping_option: false,
  show_seating_option: false,
  show_rules_option: false,
  show_roster_actions: false,
  show_template_actions: false,
};

function buildWorkspaceSummary(selectedRoster: Roster | null): ClassWorkspaceSummary | null {
  if (!selectedRoster) {
    return null;
  }

  return {
    roster: {
      id: selectedRoster.id,
      name: selectedRoster.name,
      student_count: selectedRoster.students.length,
    },
    task_entry_options: [],
    active_grouping_draft: null,
    active_seating_draft: null,
    grouping_history: [],
    seating_history: [],
  };
}

function resolveExistingId<T extends { id: string }>(
  preferredId: string | null,
  entries: T[],
): string | null {
  if (preferredId && entries.some((entry) => entry.id === preferredId)) {
    return preferredId;
  }

  return entries[0]?.id ?? null;
}

export function useClassroomPlannerGuestOverviewShell(options?: {
  enabled?: boolean;
  guestStorage?: ClassroomPlannerGuestStorageAdapter;
  guestStorageFactory?: () => ClassroomPlannerGuestStorageAdapter;
  nowIso?: () => string;
}) {
  const enabled = options?.enabled ?? true;
  let guestStorage: ClassroomPlannerGuestStorageAdapter | null = options?.guestStorage ?? null;

  const availableRosters = ref<Roster[]>([]);
  const availableTemplates = ref<RoomTemplate[]>([]);
  const selectedRosterId = ref<string | null>(null);
  const selectedTemplateId = ref<string | null>(null);
  const isBootstrapping = ref(enabled);
  const bootstrapError = ref<string | null>(null);
  const plannerActionError = ref<string | null>(null);
  const currentSnapshotId = ref<string | null>(null);

  const overviewCapabilities = CHECKPOINT_ONE_OVERVIEW_CAPABILITIES;
  const classWorkspaceSummary = computed(() => {
    const selectedRoster = availableRosters.value.find((roster) => roster.id === selectedRosterId.value) ?? null;
    return buildWorkspaceSummary(selectedRoster);
  });

  function resolveGuestStorage(): ClassroomPlannerGuestStorageAdapter {
    if (!guestStorage) {
      guestStorage = options?.guestStorageFactory?.() ?? createClassroomPlannerGuestStorage();
    }
    return guestStorage;
  }

  function getNowIso(): string {
    return options?.nowIso?.() ?? new Date().toISOString();
  }

  async function ensureReadySnapshot() {
    const storage = resolveGuestStorage();
    const currentSnapshot = await storage.loadCurrentSnapshot();
    if (currentSnapshot.status === "ready") {
      return currentSnapshot.snapshot;
    }

    const initializedSnapshot = await storage.initializeEmptySnapshot();
    if (initializedSnapshot.status !== "ready") {
      throw new Error("Det gick inte att initiera den publika arbetsytan.");
    }

    return initializedSnapshot.snapshot;
  }

  async function persistUiState(input: {
    selectedRosterId: string | null;
    selectedTemplateId: string | null;
  }): Promise<void> {
    const snapshot = await ensureReadySnapshot();
    const nextSnapshot = replaceGuestSnapshotUiState(snapshot, {
      selected_roster_id: input.selectedRosterId,
      selected_template_id: input.selectedTemplateId,
      current_screen: "class-workspace",
      planner_initial_view: "groups",
      dismissed_grouping_draft_id: null,
      dismissed_seating_draft_id: null,
      updated_at: getNowIso(),
    });
    await resolveGuestStorage().saveSnapshot(nextSnapshot);
    currentSnapshotId.value = nextSnapshot.snapshot_id;
  }

  async function bootstrapGuestOverview(): Promise<void> {
    if (!enabled) {
      isBootstrapping.value = false;
      bootstrapError.value = null;
      availableRosters.value = [];
      availableTemplates.value = [];
      selectedRosterId.value = null;
      selectedTemplateId.value = null;
      return;
    }

    isBootstrapping.value = true;
    bootstrapError.value = null;
    plannerActionError.value = null;

    try {
      const snapshot = await ensureReadySnapshot();
      const hydratedSnapshot = hydrateGuestSnapshot(snapshot);
      const normalizedSelectedRosterId = resolveExistingId(
        hydratedSnapshot.ui_state.selected_roster_id,
        hydratedSnapshot.rosters,
      );
      const normalizedSelectedTemplateId = resolveExistingId(
        hydratedSnapshot.ui_state.selected_template_id,
        hydratedSnapshot.templates,
      );

      availableRosters.value = hydratedSnapshot.rosters;
      availableTemplates.value = hydratedSnapshot.templates;
      selectedRosterId.value = normalizedSelectedRosterId;
      selectedTemplateId.value = normalizedSelectedTemplateId;
      currentSnapshotId.value = snapshot.snapshot_id;

      const needsUiStateNormalization =
        snapshot.ui_state.selected_roster_local_id !== normalizedSelectedRosterId
        || snapshot.ui_state.selected_template_local_id !== normalizedSelectedTemplateId
        || snapshot.ui_state.current_screen !== "class-workspace"
        || snapshot.ui_state.planner_initial_view !== "groups"
        || snapshot.ui_state.dismissed_grouping_draft_local_id !== null
        || snapshot.ui_state.dismissed_seating_draft_local_id !== null;

      if (needsUiStateNormalization) {
        await persistUiState({
          selectedRosterId: normalizedSelectedRosterId,
          selectedTemplateId: normalizedSelectedTemplateId,
        });
      }
    } catch (error: unknown) {
      bootstrapError.value = error instanceof Error
        ? error.message
        : "Det gick inte att ladda den publika arbetsytan.";
    } finally {
      isBootstrapping.value = false;
    }
  }

  async function selectWorkspaceRoster(rosterId: string): Promise<void> {
    if (rosterId === selectedRosterId.value) {
      return;
    }

    selectedRosterId.value = rosterId;
    plannerActionError.value = null;

    try {
      await persistUiState({
        selectedRosterId: rosterId,
        selectedTemplateId: selectedTemplateId.value,
      });
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Det gick inte att spara vald klass i den publika arbetsytan.";
    }
  }

  async function selectWorkspaceTemplate(templateId: string | null): Promise<void> {
    if (templateId === selectedTemplateId.value) {
      return;
    }

    selectedTemplateId.value = templateId;
    plannerActionError.value = null;

    try {
      await persistUiState({
        selectedRosterId: selectedRosterId.value,
        selectedTemplateId: templateId,
      });
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Det gick inte att spara valt klassrum i den publika arbetsytan.";
    }
  }

  onMounted(() => {
    void bootstrapGuestOverview();
  });

  return {
    availableRosters,
    availableTemplates,
    selectedRosterId,
    selectedTemplateId,
    isBootstrapping,
    bootstrapError,
    plannerActionError,
    classWorkspaceSummary,
    currentSnapshotId,
    overviewCapabilities,
    selectWorkspaceRoster,
    selectWorkspaceTemplate,
    bootstrapGuestOverview,
  };
}
