/**
 * Classroom planner guest controller.
 *
 * This composable owns public Klassrumskartan guest orchestration. It
 * bootstraps the browser-owned guest snapshot, keeps the public route on the
 * overview-authoring lane for checkpoint 2, and delegates pure persistence and
 * overview CRUD details to focused helper modules.
 */

import { computed, onMounted, ref } from "vue";

import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import {
  buildWorkspaceSummary,
  CHECKPOINT_TWO_OVERVIEW_CAPABILITIES,
  hydrateGuestOverviewSnapshot,
  normalizeOverviewSnapshotUiState,
  PUBLIC_ROSTER_IMPORT_PREVIEW_API_PATH,
} from "./classroomPlannerGuestControllerSupport";
import { createClassroomPlannerGuestOverviewCrudFlow } from "./classroomPlannerGuestOverviewCrud";
import { createClassroomPlannerGuestStorage } from "./classroomPlannerGuestStorage";
import type { RoomTemplate, Roster } from "./classroomPlannerTypes";

type ClassroomPlannerGuestStorageAdapter = ReturnType<typeof createClassroomPlannerGuestStorage>;

export function useClassroomPlannerGuestController(options?: {
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

  const overviewCapabilities = CHECKPOINT_TWO_OVERVIEW_CAPABILITIES;
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

  function applyHydratedSnapshot(
    snapshot: ClassroomPlannerGuestSnapshot,
    options?: {
      preserveExplicitTemplateNull?: boolean;
    },
  ): {
    normalizedSelectedRosterId: string | null;
    normalizedSelectedTemplateId: string | null;
  } {
    const hydratedOverviewState = hydrateGuestOverviewSnapshot(snapshot, options);

    availableRosters.value = hydratedOverviewState.rosters;
    availableTemplates.value = hydratedOverviewState.templates;
    selectedRosterId.value = hydratedOverviewState.normalizedSelectedRosterId;
    selectedTemplateId.value = hydratedOverviewState.normalizedSelectedTemplateId;
    currentSnapshotId.value = snapshot.snapshot_id;

    return {
      normalizedSelectedRosterId: hydratedOverviewState.normalizedSelectedRosterId,
      normalizedSelectedTemplateId: hydratedOverviewState.normalizedSelectedTemplateId,
    };
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

  async function persistSnapshotMutation<TResult>(input: {
    mutate: (snapshot: ClassroomPlannerGuestSnapshot, updatedAt: string) => {
      nextSnapshot: ClassroomPlannerGuestSnapshot;
      result: TResult;
    };
  }): Promise<TResult> {
    const currentSnapshot = await ensureReadySnapshot();
    const updatedAt = getNowIso();
    const { nextSnapshot, result } = input.mutate(currentSnapshot, updatedAt);
    await resolveGuestStorage().saveSnapshot(nextSnapshot);
    applyHydratedSnapshot(nextSnapshot, {
      preserveExplicitTemplateNull: nextSnapshot.ui_state.selected_template_local_id === null,
    });
    return result;
  }

  async function persistUiState(input: {
    selectedRosterId: string | null;
    selectedTemplateId: string | null;
  }): Promise<void> {
    await persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        return {
          nextSnapshot: normalizeOverviewSnapshotUiState(snapshot, {
            preferredRosterId: input.selectedRosterId,
            preferredTemplateId: input.selectedTemplateId,
            updatedAt,
            preserveExplicitTemplateNull: input.selectedTemplateId === null,
          }),
          result: undefined,
        };
      },
    });
  }

  const overviewCrudFlow = createClassroomPlannerGuestOverviewCrudFlow(
    {
      availableRosters,
      availableTemplates,
      selectedRosterId,
      selectedTemplateId,
      plannerActionError,
    },
    {
      persistSnapshotMutation,
    },
  );

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
      const {
        normalizedSelectedRosterId,
        normalizedSelectedTemplateId,
      } = applyHydratedSnapshot(snapshot, {
        preserveExplicitTemplateNull: snapshot.ui_state.selected_template_local_id === null,
      });
      const normalizedSnapshot = normalizeOverviewSnapshotUiState(snapshot, {
        preferredRosterId: normalizedSelectedRosterId,
        preferredTemplateId: normalizedSelectedTemplateId,
        updatedAt: getNowIso(),
        preserveExplicitTemplateNull: normalizedSelectedTemplateId === null,
      });

      if (normalizedSnapshot !== snapshot) {
        await resolveGuestStorage().saveSnapshot(normalizedSnapshot);
        applyHydratedSnapshot(normalizedSnapshot, {
          preserveExplicitTemplateNull: normalizedSnapshot.ui_state.selected_template_local_id === null,
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
    rosterImportPreviewApiPath: PUBLIC_ROSTER_IMPORT_PREVIEW_API_PATH,
    selectWorkspaceRoster,
    selectWorkspaceTemplate,
    bootstrapGuestOverview,
    ...overviewCrudFlow,
  };
}
