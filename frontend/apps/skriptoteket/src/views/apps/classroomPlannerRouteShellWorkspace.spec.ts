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
  });

  it("prefers the overview-selected template when Regler bootstraps a seating host draft", async () => {
    const selectedRosterId = ref("roster-1");
    const selectedWorkspaceTemplateId = ref<string | null>("template-overview-1");
    const currentScreen = ref<"class-workspace" | "planner">("class-workspace");
    const plannerInitialView = ref<"groups" | "seats" | "rules">("groups");
    const plannerActionError = ref<string | null>(null);
    const classWorkspaceSummary = ref({
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
});
