/**
 * Classroom planner guest controller.
 *
 * This composable owns the public Klassrumskartan guest shell for checkpoint 3.
 * It restores the browser-owned guest snapshot, exposes overview CRUD for the
 * public class workspace, and coordinates the guest-local grouping/seating
 * planner without touching authenticated route-shell behavior.
 */

import { computed, onMounted, ref } from "vue";

import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import {
  buildWorkspaceSummary,
  CHECKPOINT_THREE_OVERVIEW_CAPABILITIES,
  hydrateGuestOverviewSnapshot,
  normalizeOverviewSnapshotUiState,
  PUBLIC_ROSTER_IMPORT_PREVIEW_API_PATH,
} from "./classroomPlannerGuestControllerSupport";
import { createClassroomPlannerGuestDraftSession } from "./classroomPlannerGuestDraftSession";
import { resolveGuestGroupingTemplateContext } from "./classroomPlannerGuestTemplateContext";
import { buildGuestWorkspaceSummary } from "./classroomPlannerGuestDraftMutations";
import { createClassroomPlannerGuestOverviewCrudFlow } from "./classroomPlannerGuestOverviewCrud";
import { hydrateGuestSnapshot } from "./classroomPlannerGuestSnapshotMapping";
import {
  createClassroomPlannerGuestStorage,
  type ClassroomPlannerGuestStoragePort,
} from "./classroomPlannerGuestStorage";
import type { ClassroomPlannerGuestPlannerInitialView } from "./classroomPlannerGuestSnapshot";
import type { RoomTemplate, Roster } from "./classroomPlannerTypes";

type OverviewDistributionScope = "grouping" | "seating";

function resolveSnapshotDraftId(
  snapshot: ClassroomPlannerGuestSnapshot,
  initialView: ClassroomPlannerGuestPlannerInitialView,
): string | null {
  const hydrated = hydrateGuestSnapshot(snapshot);
  if (initialView === "seats" || initialView === "rules") {
    return hydrated.seating_draft?.draft.id ?? hydrated.grouping_draft?.draft.id ?? null;
  }
  return hydrated.grouping_draft?.draft.id ?? hydrated.seating_draft?.draft.id ?? null;
}

export function useClassroomPlannerGuestController(options?: {
  enabled?: boolean;
  guestStorage?: ClassroomPlannerGuestStoragePort;
  guestStorageFactory?: () => ClassroomPlannerGuestStoragePort;
  nowIso?: () => string;
}) {
  const enabled = options?.enabled ?? true;
  let guestStorage: ClassroomPlannerGuestStoragePort | null = options?.guestStorage ?? null;

  const availableRosters = ref<Roster[]>([]);
  const availableTemplates = ref<RoomTemplate[]>([]);
  const selectedRosterId = ref<string | null>(null);
  const selectedTemplateId = ref<string | null>(null);
  const currentScreen = ref<"class-workspace" | "planner">("class-workspace");
  const plannerInitialView = ref<"groups" | "seats" | "rules">("groups");
  const isBootstrapping = ref(enabled);
  const bootstrapError = ref<string | null>(null);
  const plannerActionError = ref<string | null>(null);
  const guestAuthoringClosed = ref(false);
  const currentSnapshot = ref<ClassroomPlannerGuestSnapshot | null>(null);
  const currentSnapshotId = ref<string | null>(null);

  const overviewCapabilities = CHECKPOINT_THREE_OVERVIEW_CAPABILITIES;
  const classWorkspaceSummary = computed(() => {
    if (!currentSnapshot.value || !selectedRosterId.value) {
      const selectedRoster =
        availableRosters.value.find((roster) => roster.id === selectedRosterId.value) ?? null;
      return buildWorkspaceSummary(selectedRoster);
    }

    return buildGuestWorkspaceSummary(currentSnapshot.value, selectedRosterId.value);
  });

  function resolveGuestStorage(): ClassroomPlannerGuestStoragePort {
    if (!guestStorage) {
      guestStorage = options?.guestStorageFactory?.() ?? createClassroomPlannerGuestStorage();
    }
    return guestStorage;
  }

  function getNowIso(): string {
    return options?.nowIso?.() ?? new Date().toISOString();
  }

  function applyGuestAuthoringClosedState(): void {
    guestAuthoringClosed.value = true;
    bootstrapError.value = null;
    plannerActionError.value = null;
    guestPlannerState.clearWorkspace();
    availableRosters.value = [];
    availableTemplates.value = [];
    selectedRosterId.value = null;
    selectedTemplateId.value = null;
    currentScreen.value = "class-workspace";
    plannerInitialView.value = "groups";
    currentSnapshot.value = null;
    currentSnapshotId.value = null;
  }

  async function refreshGuestAuthoringClosedState(): Promise<boolean> {
    const isClosed = await resolveGuestStorage().isGuestAuthoringClosed?.() ?? false;
    if (isClosed) {
      applyGuestAuthoringClosedState();
      return true;
    }
    guestAuthoringClosed.value = false;
    return false;
  }

  function applyHydratedSnapshot(
    snapshot: ClassroomPlannerGuestSnapshot,
    applyOptions?: {
      preserveExplicitTemplateNull?: boolean;
    },
  ): void {
    const hydratedOverviewState = hydrateGuestOverviewSnapshot(snapshot, applyOptions);
    availableRosters.value = hydratedOverviewState.rosters;
    availableTemplates.value = hydratedOverviewState.templates;
    selectedRosterId.value = hydratedOverviewState.normalizedSelectedRosterId;
    selectedTemplateId.value = hydratedOverviewState.normalizedSelectedTemplateId;
    currentScreen.value = snapshot.ui_state.current_screen;
    plannerInitialView.value =
      snapshot.ui_state.planner_initial_view === "seats"
        ? "seats"
        : snapshot.ui_state.planner_initial_view === "rules"
          ? "rules"
          : "groups";
    currentSnapshot.value = snapshot;
    currentSnapshotId.value = snapshot.snapshot_id;
  }

  async function ensureReadySnapshot(): Promise<ClassroomPlannerGuestSnapshot> {
    if (guestAuthoringClosed.value || await refreshGuestAuthoringClosedState()) {
      throw new Error(
        "Det går inte att skapa nya klasser och klassrum i den här webbläsaren eftersom du redan har använt Klassrumskartan inloggad här. Logga in för att fortsätta använda appen.",
      );
    }

    const storage = resolveGuestStorage();
    const current = await storage.loadCurrentSnapshot();
    if (current.status === "ready") {
      return current.snapshot;
    }

    const initialized = await storage.initializeEmptySnapshot();
    if (initialized.status !== "ready") {
      throw new Error("Det gick inte att initiera den publika arbetsytan.");
    }

    return initialized.snapshot;
  }

  async function persistSnapshotMutation<TResult>(input: {
    mutate: (snapshot: ClassroomPlannerGuestSnapshot, updatedAt: string) => {
      nextSnapshot: ClassroomPlannerGuestSnapshot;
      result: TResult;
    };
  }): Promise<TResult> {
    const snapshot = await ensureReadySnapshot();
    const updatedAt = getNowIso();
    const { nextSnapshot, result } = input.mutate(snapshot, updatedAt);
    await resolveGuestStorage().saveSnapshot(nextSnapshot);
    applyHydratedSnapshot(nextSnapshot, {
      preserveExplicitTemplateNull: nextSnapshot.ui_state.selected_template_local_id === null,
    });
    return result;
  }

  async function persistUiState(input: {
    selectedRosterId: string | null;
    selectedTemplateId: string | null;
    currentScreen?: "class-workspace" | "planner";
    plannerInitialView?: "groups" | "seats" | "rules";
  }): Promise<void> {
    await persistSnapshotMutation({
      mutate(snapshot, updatedAt) {
        return {
          nextSnapshot: normalizeOverviewSnapshotUiState(snapshot, {
            preferredRosterId: input.selectedRosterId,
            preferredTemplateId: input.selectedTemplateId,
            updatedAt,
            preserveExplicitTemplateNull: input.selectedTemplateId === null,
            currentScreen: input.currentScreen,
            plannerInitialView: input.plannerInitialView,
          }),
          result: undefined,
        };
      },
    });
  }

  const guestPlannerState = createClassroomPlannerGuestDraftSession({
    getSnapshot: ensureReadySnapshot,
    persistSnapshotMutation,
    nowIso: getNowIso,
  });

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

  async function restorePlannerFromSnapshot(snapshot: ClassroomPlannerGuestSnapshot): Promise<void> {
    if (snapshot.ui_state.current_screen !== "planner") {
      guestPlannerState.clearWorkspace();
      return;
    }

    const draftId = resolveSnapshotDraftId(snapshot, snapshot.ui_state.planner_initial_view);
    if (!draftId) {
      guestPlannerState.clearWorkspace();
      currentScreen.value = "class-workspace";
      plannerInitialView.value = "groups";
      await persistUiState({
        selectedRosterId: selectedRosterId.value,
        selectedTemplateId: selectedTemplateId.value,
        currentScreen: "class-workspace",
        plannerInitialView: "groups",
      });
      return;
    }

    await guestPlannerState.loadWorkspace(draftId);
  }

  async function bootstrapGuestWorkspace(): Promise<void> {
    if (!enabled) {
      guestPlannerState.clearWorkspace();
      isBootstrapping.value = false;
      bootstrapError.value = null;
      plannerActionError.value = null;
      availableRosters.value = [];
      availableTemplates.value = [];
      selectedRosterId.value = null;
      selectedTemplateId.value = null;
      currentScreen.value = "class-workspace";
      plannerInitialView.value = "groups";
      guestAuthoringClosed.value = false;
      currentSnapshot.value = null;
      currentSnapshotId.value = null;
      return;
    }

    isBootstrapping.value = true;
    bootstrapError.value = null;
    plannerActionError.value = null;

    try {
      if (await refreshGuestAuthoringClosedState()) {
        return;
      }

      const snapshot = await ensureReadySnapshot();
      const hydratedOverviewState = hydrateGuestOverviewSnapshot(snapshot, {
        preserveExplicitTemplateNull: snapshot.ui_state.selected_template_local_id === null,
      });
      const normalizedSnapshot = normalizeOverviewSnapshotUiState(snapshot, {
        preferredRosterId: hydratedOverviewState.normalizedSelectedRosterId,
        preferredTemplateId: hydratedOverviewState.normalizedSelectedTemplateId,
        updatedAt: getNowIso(),
        preserveExplicitTemplateNull: hydratedOverviewState.normalizedSelectedTemplateId === null,
      });

      if (normalizedSnapshot !== snapshot) {
        await resolveGuestStorage().saveSnapshot(normalizedSnapshot);
      }
      applyHydratedSnapshot(normalizedSnapshot, {
        preserveExplicitTemplateNull: normalizedSnapshot.ui_state.selected_template_local_id === null,
      });
      await restorePlannerFromSnapshot(normalizedSnapshot);
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

  async function flushPlannerForModeSwitch(
    conflictMessage: string,
    fallbackMessage: string,
  ): Promise<boolean> {
    if (!guestPlannerState.draft.value) {
      return true;
    }

    const result = await guestPlannerState.prepareForWorkspaceSwitch({
      conflictMessage,
      fallbackMessage,
    });
    if (result.status === "blocked") {
      plannerActionError.value = result.message;
      return false;
    }
    return true;
  }

  function activeDraftMatchesDistributionScope(input: {
    scope: OverviewDistributionScope;
    rosterId: string;
    templateId: string | null;
  }): boolean {
    const activeDraft = guestPlannerState.draft.value;
    if (!activeDraft || activeDraft.draft_kind !== input.scope || activeDraft.roster_id !== input.rosterId) {
      return false;
    }

    if (input.scope === "seating") {
      return activeDraft.template_id === input.templateId;
    }

    return (activeDraft.template_id ?? null) === input.templateId;
  }

  async function prepareOverviewDistributionScope(
    scope: OverviewDistributionScope,
  ): Promise<boolean> {
    const rosterId = selectedRosterId.value;
    if (!rosterId) {
      return false;
    }

    const templateId = scope === "seating"
      ? selectedTemplateId.value
      : resolveGuestGroupingTemplateContext(selectedTemplateId.value);
    if (scope === "seating" && !templateId) {
      return false;
    }

    plannerActionError.value = null;
    try {
      if (
        guestPlannerState.draft.value
        && !activeDraftMatchesDistributionScope({ scope, rosterId, templateId })
        && !(await flushPlannerForModeSwitch(
          "Lös sparkonflikten innan du byter underlag för delning.",
          "Kunde inte spara ändringarna innan underlaget för delning byttes.",
        ))
      ) {
        return false;
      }

      if (!activeDraftMatchesDistributionScope({ scope, rosterId, templateId })) {
        await guestPlannerState.resolveDraft(rosterId, templateId, scope);
      }

      const nextPlannerInitialView = scope === "seating" ? "seats" : "groups";
      await guestPlannerState.persistOverviewUiState({
        selectedRosterId: rosterId,
        selectedTemplateId: selectedTemplateId.value,
        plannerInitialView: nextPlannerInitialView,
      });
      currentScreen.value = "class-workspace";
      plannerInitialView.value = nextPlannerInitialView;
      return true;
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : scope === "seating"
          ? "Kunde inte förbereda sittplatser för delning just nu."
          : "Kunde inte förbereda grupper för delning just nu.";
      return false;
    }
  }

  async function openGroupingWorkspace(rosterId: string | null = selectedRosterId.value): Promise<void> {
    if (!rosterId) {
      return;
    }

    plannerActionError.value = null;
    try {
      await guestPlannerState.resolveDraft(
        rosterId,
        resolveGuestGroupingTemplateContext(selectedTemplateId.value),
        "grouping",
      );
      currentScreen.value = "planner";
      plannerInitialView.value = "groups";
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Kunde inte öppna grupparbetsytan just nu.";
    }
  }

  async function openSeatingWorkspace(templateId: string | null): Promise<void> {
    if (!selectedRosterId.value || !templateId) {
      return;
    }

    plannerActionError.value = null;
    try {
      await guestPlannerState.resolveDraft(selectedRosterId.value, templateId, "seating");
      currentScreen.value = "planner";
      plannerInitialView.value = "seats";
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Kunde inte öppna sittplatserna just nu.";
    }
  }

  async function changeGroupingRoster(payload: { rosterId: string }): Promise<void> {
    if (!(await flushPlannerForModeSwitch(
      "Lös sparkonflikten innan du byter klass.",
      "Kunde inte spara ändringarna innan klassen byttes.",
    ))) {
      return;
    }
    await openGroupingWorkspace(payload.rosterId);
  }

  async function changeGroupingTemplate(payload: { templateId: string | null }): Promise<void> {
    if (!(await flushPlannerForModeSwitch(
      "Lös sparkonflikten innan du byter gruppkontext.",
      "Kunde inte spara ändringarna innan gruppkontexten byttes.",
    ))) {
      return;
    }

    if (!selectedRosterId.value) {
      return;
    }

    plannerActionError.value = null;
    try {
      await guestPlannerState.resolveDraft(selectedRosterId.value, payload.templateId, "grouping");
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Kunde inte uppdatera gruppkontexten just nu.";
    }
  }

  async function changeSeatingTemplate(payload: { templateId: string | null }): Promise<void> {
    if (!(await flushPlannerForModeSwitch(
      "Lös sparkonflikten innan du byter klassrum.",
      "Kunde inte spara ändringarna innan klassrummet byttes.",
    ))) {
      return;
    }
    await openSeatingWorkspace(payload.templateId);
  }

  async function startNewGroupingDraft(): Promise<void> {
    if (!selectedRosterId.value) {
      return;
    }
    if (!(await flushPlannerForModeSwitch(
      "Lös sparkonflikten innan du startar ett nytt grupputkast.",
      "Kunde inte spara ändringarna innan nytt grupputkast startades.",
    ))) {
      return;
    }

    plannerActionError.value = null;
    try {
      await guestPlannerState.startNewGroupingDraft(
        selectedRosterId.value,
        resolveGuestGroupingTemplateContext(selectedTemplateId.value),
      );
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Kunde inte starta ett nytt grupputkast just nu.";
    }
  }

  async function startNewSeatingDraft(payload: { templateId: string }): Promise<void> {
    if (!selectedRosterId.value) {
      return;
    }
    if (!(await flushPlannerForModeSwitch(
      "Lös sparkonflikten innan du startar ett nytt sittschema.",
      "Kunde inte spara ändringarna innan nytt sittschema startades.",
    ))) {
      return;
    }

    plannerActionError.value = null;
    try {
      await guestPlannerState.startNewSeatingDraft(selectedRosterId.value, payload.templateId);
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Kunde inte starta ett nytt sittschema just nu.";
    }
  }

  async function openRulesWorkspace(): Promise<void> {
    if (!selectedRosterId.value) {
      return;
    }

    plannerActionError.value = null;
    try {
      const snapshot = await ensureReadySnapshot();
      const hydrated = hydrateGuestSnapshot(snapshot);
      const seatingDraft = hydrated.seating_draft?.roster.id === selectedRosterId.value
        ? hydrated.seating_draft
        : null;
      const groupingDraft = hydrated.grouping_draft?.roster.id === selectedRosterId.value
        ? hydrated.grouping_draft
        : null;

      if (guestPlannerState.draft.value && guestPlannerState.roster.value?.id === selectedRosterId.value) {
        await persistUiState({
          selectedRosterId: selectedRosterId.value,
          selectedTemplateId: guestPlannerState.template.value?.id ?? selectedTemplateId.value,
          currentScreen: "planner",
          plannerInitialView: "rules",
        });
        return;
      }

      if (seatingDraft) {
        await guestPlannerState.loadWorkspace(seatingDraft.draft.id);
      } else if (groupingDraft) {
        await guestPlannerState.loadWorkspace(groupingDraft.draft.id);
      } else {
        const preferredDraftKind = selectedTemplateId.value ? "seating" : "grouping";
        await guestPlannerState.resolveDraft(
          selectedRosterId.value,
          selectedTemplateId.value,
          preferredDraftKind,
        );
      }

      await persistUiState({
        selectedRosterId: selectedRosterId.value,
        selectedTemplateId: guestPlannerState.template.value?.id ?? selectedTemplateId.value,
        currentScreen: "planner",
        plannerInitialView: "rules",
      });
    } catch (error: unknown) {
      plannerActionError.value = error instanceof Error
        ? error.message
        : "Kunde inte öppna reglerna just nu.";
    }
  }

  async function selectPlannerWorkspaceMode(
    mode: "overview" | "grouping" | "seating" | "rules",
  ): Promise<void> {
    if (mode === "overview") {
      plannerActionError.value = null;
      try {
        await guestPlannerState.persistCurrentWorkspaceToOverview({
          selectedRosterId: guestPlannerState.roster.value?.id ?? selectedRosterId.value,
          selectedTemplateId: guestPlannerState.template.value?.id ?? selectedTemplateId.value,
          plannerInitialView: plannerInitialView.value,
        });
        guestPlannerState.clearWorkspace();
      } catch (error: unknown) {
        plannerActionError.value = error instanceof Error
          ? error.message
          : "Kunde inte återvända till klassarbetsytan just nu.";
      }
      return;
    }

    if (mode === "rules") {
      await openRulesWorkspace();
      return;
    }

    if (mode === "grouping") {
      await openGroupingWorkspace();
      return;
    }

    await openSeatingWorkspace(guestPlannerState.template.value?.id ?? selectedTemplateId.value);
  }

  async function saveRoster(
    payload: Parameters<typeof overviewCrudFlow.saveRoster>[0],
  ): Promise<Roster> {
    const roster = await overviewCrudFlow.saveRoster(payload);
    if (guestPlannerState.roster.value?.id === roster.id) {
      guestPlannerState.replaceCurrentRoster(roster);
    }
    return roster;
  }

  async function saveTemplate(
    payload: Parameters<typeof overviewCrudFlow.saveTemplate>[0],
  ): Promise<RoomTemplate> {
    const template = await overviewCrudFlow.saveTemplate(payload);
    if (guestPlannerState.template.value?.id === template.id) {
      guestPlannerState.replaceCurrentTemplate(template);
    }
    return template;
  }

  onMounted(() => {
    void bootstrapGuestWorkspace();
  });

  return {
    availableRosters,
    availableTemplates,
    selectedRosterId,
    selectedTemplateId,
    currentScreen,
    plannerInitialView,
    isBootstrapping,
    bootstrapError,
    plannerActionError,
    guestAuthoringClosed,
    classWorkspaceSummary,
    currentSnapshotId,
    ensureReadySnapshot,
    persistSnapshotMutation,
    overviewCapabilities,
    guestPlannerState,
    rosterImportPreviewApiPath: PUBLIC_ROSTER_IMPORT_PREVIEW_API_PATH,
    selectWorkspaceRoster,
    selectWorkspaceTemplate,
    bootstrapGuestWorkspace,
    openGroupingWorkspace,
    openSeatingWorkspace,
    changeGroupingRoster,
    changeGroupingTemplate,
    changeSeatingTemplate,
    startNewGroupingDraft,
    startNewSeatingDraft,
    openRulesWorkspace,
    prepareOverviewDistributionScope,
    selectPlannerWorkspaceMode,
    ...overviewCrudFlow,
    saveRoster,
    saveTemplate,
  };
}
