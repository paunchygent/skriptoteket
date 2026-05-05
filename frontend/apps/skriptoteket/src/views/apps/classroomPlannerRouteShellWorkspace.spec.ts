/**
 * Route-shell workspace flow tests.
 *
 * These tests lock the `Regler` bootstrap branch so overview-selected
 * classroom context is preserved when the route shell has to create the
 * seating host draft on demand.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { createClassroomPlannerWorkspaceFlow } from "./classroomPlannerRouteShellWorkspace";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

const toastMocks = vi.hoisted(() => ({
  failure: vi.fn(),
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

function createDeferred() {
  let resolvePromise!: () => void;
  const promise = new Promise<void>((resolve) => {
    resolvePromise = resolve;
  });
  return {
    promise,
    resolve: resolvePromise,
  };
}

describe("createClassroomPlannerWorkspaceFlow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    toastMocks.failure.mockReset();
  });

  it("prefers the overview-selected template when Regler bootstraps a seating host draft", async () => {
    const selectedRosterId = ref("roster-1");
    const selectedWorkspaceTemplateId = ref<string | null>("template-overview-1");
    const currentScreen = ref<"class-workspace" | "planner">("class-workspace");
    const plannerInitialView = ref<"groups" | "seats" | "rules">("groups");
    const plannerActionError = ref<string | null>(null);
    const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>({
      roster: { id: "roster-1", name: "SA24D", student_count: 28 },
      task_entry_options: [
        { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
        { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    });
    const isSeatingLifecycleBusy = ref(false);
    const busySeatingHistoryDraftId = ref<string | null>(null);
    const workspaceTransitionLabel = ref<string | null>(null);
    const workspaceNotice = ref<string | null>(null);
    const refreshClassWorkspaceSummaryForSelectedRoster = vi.fn().mockResolvedValue(undefined);
    const deferred = createDeferred();

    const plannerState = {
      draft: null,
      roster: null,
      template: null,
      prepareForPlannerExit: vi.fn().mockResolvedValue({ status: "saved" }),
      prepareForWorkspaceSwitch: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      loadWorkspace: vi.fn(),
      resolveDraft: vi.fn().mockImplementation(async () => {
        await deferred.promise;
      }),
      clearWorkspace: vi.fn(),
      startNewGroupingDraft: vi.fn(),
      startNewSeatingDraft: vi.fn(),
      activateGroupingHistoryDraft: vi.fn(),
      activateSeatingHistoryDraft: vi.fn(),
      deleteGroupingHistoryDraft: vi.fn(),
      deleteSeatingHistoryDraft: vi.fn(),
    };

    const flow = createClassroomPlannerWorkspaceFlow(
      {
        selectedRosterId,
        selectedWorkspaceTemplateId,
        currentScreen,
        plannerInitialView,
        plannerActionError,
        classWorkspaceSummary,
        isSeatingLifecycleBusy,
        busySeatingHistoryDraftId,
        workspaceTransitionLabel,
        workspaceNotice,
      },
      {
        loadClassWorkspaceSummary: vi.fn(),
        refreshClassWorkspaceSummaryForSelectedRoster,
        openInitialHomeWorkspace: vi.fn(),
        syncWorkspaceTemplateSelection: vi.fn(),
      },
      plannerState,
    );

    const openRulesPromise = flow.openRulesWorkspace();

    expect(workspaceTransitionLabel.value).toBe(
      "Förbereder Regler genom att starta ett sittschema i bakgrunden...",
    );
    expect(plannerState.resolveDraft).toHaveBeenCalledWith(
      "roster-1",
      "template-overview-1",
      "seating",
    );
    expect(plannerState.loadWorkspace).not.toHaveBeenCalled();

    deferred.resolve();
    await openRulesPromise;

    expect(refreshClassWorkspaceSummaryForSelectedRoster).toHaveBeenCalledOnce();
    expect(plannerInitialView.value).toBe("rules");
    expect(currentScreen.value).toBe("planner");
    expect(workspaceTransitionLabel.value).toBeNull();
    expect(workspaceNotice.value).toBe(
      "Regler använder ett sittschema i bakgrunden. Vi startade ett nytt sittschema för den här klassen.",
    );
    expect(plannerActionError.value).toBeNull();
  });

  it("switches to the overview shell before clearing planner state on overview return", async () => {
    const selectedRosterId = ref("roster-1");
    const selectedWorkspaceTemplateId = ref<string | null>("template-overview-1");
    const currentScreen = ref<"class-workspace" | "planner">("planner");
    const plannerInitialView = ref<"groups" | "seats" | "rules">("groups");
    const plannerActionError = ref<string | null>(null);
    const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>({
      roster: { id: "roster-1", name: "SA24D", student_count: 28 },
      task_entry_options: [
        { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
        { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    });
    const isSeatingLifecycleBusy = ref(false);
    const busySeatingHistoryDraftId = ref<string | null>(null);
    const workspaceTransitionLabel = ref<string | null>(null);
    const workspaceNotice = ref<string | null>(null);
    const loadDeferred = createDeferred();
    const loadClassWorkspaceSummary = vi.fn().mockImplementation(async () => {
      await loadDeferred.promise;
    });
    const syncWorkspaceTemplateSelection = vi.fn();

    const plannerState = {
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "grouping" as const,
        status: "active" as const,
        revision: 1,
        last_opened_at: "2026-03-29T10:00:00Z",
      },
      roster: { id: "roster-1" },
      template: { id: "template-overview-1" },
      prepareForPlannerExit: vi.fn().mockResolvedValue({ status: "saved" }),
      prepareForWorkspaceSwitch: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      loadWorkspace: vi.fn(),
      resolveDraft: vi.fn(),
      clearWorkspace: vi.fn(),
      startNewGroupingDraft: vi.fn(),
      startNewSeatingDraft: vi.fn(),
      activateGroupingHistoryDraft: vi.fn(),
      activateSeatingHistoryDraft: vi.fn(),
      deleteGroupingHistoryDraft: vi.fn(),
      deleteSeatingHistoryDraft: vi.fn(),
    };

    const flow = createClassroomPlannerWorkspaceFlow(
      {
        selectedRosterId,
        selectedWorkspaceTemplateId,
        currentScreen,
        plannerInitialView,
        plannerActionError,
        classWorkspaceSummary,
        isSeatingLifecycleBusy,
        busySeatingHistoryDraftId,
        workspaceTransitionLabel,
        workspaceNotice,
      },
      {
        loadClassWorkspaceSummary,
        refreshClassWorkspaceSummaryForSelectedRoster: vi.fn(),
        openInitialHomeWorkspace: vi.fn(),
        syncWorkspaceTemplateSelection,
      },
      plannerState,
    );

    const returnPromise = flow.selectPlannerWorkspaceMode("overview");
    await vi.waitFor(() => {
      expect(workspaceTransitionLabel.value).toBe("Återgår till Översikt...");
      expect(currentScreen.value).toBe("class-workspace");
      expect(plannerState.clearWorkspace).toHaveBeenCalledOnce();
    });

    loadDeferred.resolve();
    await returnPromise;

    expect(loadClassWorkspaceSummary).toHaveBeenCalledWith("roster-1");
    expect(syncWorkspaceTemplateSelection).toHaveBeenCalledOnce();
    expect(workspaceTransitionLabel.value).toBeNull();
    expect(plannerActionError.value).toBeNull();
  });

  it("uses the overview-selected classroom when the live shell switches from groups to seating", async () => {
    const selectedRosterId = ref("roster-1");
    const selectedWorkspaceTemplateId = ref<string | null>("template-overview-2");
    const currentScreen = ref<"class-workspace" | "planner">("planner");
    const plannerInitialView = ref<"groups" | "seats" | "rules">("groups");
    const plannerActionError = ref<string | null>(null);
    const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>({
      roster: { id: "roster-1", name: "SA24D", student_count: 28 },
      task_entry_options: [
        { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
        { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    });
    const isSeatingLifecycleBusy = ref(false);
    const busySeatingHistoryDraftId = ref<string | null>(null);
    const workspaceTransitionLabel = ref<string | null>(null);
    const workspaceNotice = ref<string | null>(null);

    const plannerState = {
      draft: {
        id: "draft-grouping-1",
        roster_id: "roster-1",
        draft_kind: "grouping" as const,
        status: "active" as const,
        revision: 3,
        last_opened_at: "2026-03-31T08:00:00Z",
      },
      roster: { id: "roster-1" },
      template: null,
      prepareForPlannerExit: vi.fn().mockResolvedValue({ status: "saved" }),
      prepareForWorkspaceSwitch: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      loadWorkspace: vi.fn(),
      resolveDraft: vi.fn().mockResolvedValue(undefined),
      clearWorkspace: vi.fn(),
      startNewGroupingDraft: vi.fn(),
      startNewSeatingDraft: vi.fn(),
      activateGroupingHistoryDraft: vi.fn(),
      activateSeatingHistoryDraft: vi.fn(),
      deleteGroupingHistoryDraft: vi.fn(),
      deleteSeatingHistoryDraft: vi.fn(),
    };

    const flow = createClassroomPlannerWorkspaceFlow(
      {
        selectedRosterId,
        selectedWorkspaceTemplateId,
        currentScreen,
        plannerInitialView,
        plannerActionError,
        classWorkspaceSummary,
        isSeatingLifecycleBusy,
        busySeatingHistoryDraftId,
        workspaceTransitionLabel,
        workspaceNotice,
      },
      {
        loadClassWorkspaceSummary: vi.fn(),
        refreshClassWorkspaceSummaryForSelectedRoster: vi.fn().mockResolvedValue(undefined),
        openInitialHomeWorkspace: vi.fn(),
        syncWorkspaceTemplateSelection: vi.fn(),
      },
      plannerState,
    );

    await flow.selectPlannerWorkspaceMode("seating");

    expect(plannerState.resolveDraft).toHaveBeenCalledWith(
      "roster-1",
      "template-overview-2",
      "seating",
    );
    expect(plannerInitialView.value).toBe("seats");
    expect(currentScreen.value).toBe("planner");
    expect(plannerActionError.value).toBeNull();
  });

  it("switches grouping class from the toolbar selector after flushing the current draft", async () => {
    const selectedRosterId = ref("roster-1");
    const selectedWorkspaceTemplateId = ref<string | null>("template-overview-1");
    const currentScreen = ref<"class-workspace" | "planner">("planner");
    const plannerInitialView = ref<"groups" | "seats" | "rules">("groups");
    const plannerActionError = ref<string | null>(null);
    const classWorkspaceSummary = ref<ClassWorkspaceSummary | null>({
      roster: { id: "roster-1", name: "SA24D", student_count: 28 },
      task_entry_options: [
        { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
        { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    });
    const isSeatingLifecycleBusy = ref(false);
    const busySeatingHistoryDraftId = ref<string | null>(null);
    const workspaceTransitionLabel = ref<string | null>(null);
    const workspaceNotice = ref<string | null>(null);
    const loadClassWorkspaceSummary = vi.fn().mockImplementation(async (rosterId: string) => {
      classWorkspaceSummary.value = {
        roster: {
          id: rosterId,
          name: rosterId === "roster-2" ? "SA24E" : "SA24D",
          student_count: 24,
        },
        task_entry_options: [
          { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
          { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
        ],
        active_grouping_draft: {
          id: "grouping-active-2",
          draft_kind: "grouping" as const,
          template_id: null,
          template_name: null,
          status: "active" as const,
          revision: 7,
          last_opened_at: "2026-03-30T09:00:00Z",
          updated_at: "2026-03-30T09:15:00Z",
        },
        active_seating_draft: null,
        grouping_history: [],
        seating_history: [],
      };
    });
    const refreshClassWorkspaceSummaryForSelectedRoster = vi.fn().mockResolvedValue(undefined);
    const syncWorkspaceTemplateSelection = vi.fn();

    const plannerState = {
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "grouping" as const,
        status: "active" as const,
        revision: 4,
        last_opened_at: "2026-03-30T08:00:00Z",
      },
      roster: { id: "roster-1" },
      template: null,
      prepareForPlannerExit: vi.fn().mockResolvedValue({ status: "saved" }),
      prepareForWorkspaceSwitch: vi.fn().mockResolvedValue({ status: "saved", message: null }),
      loadWorkspace: vi.fn().mockResolvedValue(undefined),
      resolveDraft: vi.fn(),
      clearWorkspace: vi.fn(),
      startNewGroupingDraft: vi.fn(),
      startNewSeatingDraft: vi.fn(),
      activateGroupingHistoryDraft: vi.fn(),
      activateSeatingHistoryDraft: vi.fn(),
      deleteGroupingHistoryDraft: vi.fn(),
      deleteSeatingHistoryDraft: vi.fn(),
    };

    const flow = createClassroomPlannerWorkspaceFlow(
      {
        selectedRosterId,
        selectedWorkspaceTemplateId,
        currentScreen,
        plannerInitialView,
        plannerActionError,
        classWorkspaceSummary,
        isSeatingLifecycleBusy,
        busySeatingHistoryDraftId,
        workspaceTransitionLabel,
        workspaceNotice,
      },
      {
        loadClassWorkspaceSummary,
        refreshClassWorkspaceSummaryForSelectedRoster,
        openInitialHomeWorkspace: vi.fn(),
        syncWorkspaceTemplateSelection,
      },
      plannerState,
    );

    const changeRosterPromise = flow.changeGroupingRoster({ rosterId: "roster-2" });

    expect(workspaceTransitionLabel.value).toBe("Byter klass...");

    await changeRosterPromise;

    expect(loadClassWorkspaceSummary).toHaveBeenCalledWith("roster-2");
    expect(plannerState.loadWorkspace).toHaveBeenCalledWith("grouping-active-2");
    expect(plannerState.resolveDraft).not.toHaveBeenCalled();
    expect(refreshClassWorkspaceSummaryForSelectedRoster).toHaveBeenCalledOnce();
    expect(syncWorkspaceTemplateSelection).toHaveBeenCalledOnce();
    expect(selectedRosterId.value).toBe("roster-2");
    expect(plannerInitialView.value).toBe("groups");
    expect(currentScreen.value).toBe("planner");
    expect(workspaceTransitionLabel.value).toBeNull();
    expect(plannerActionError.value).toBeNull();
  });
});
