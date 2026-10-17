/**
 * Root planner view tests.
 *
 * These tests verify the top-level Klassrumskartan screen orchestration, with
 * focus on the overview-first home surface, live planner transitions, and the
 * cutover exit-to-origin behavior.
 *
 * Shared planner state, API/router mocks, and reset lifecycle for these workflows.
 */

import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { vi } from "vitest";

import type { PlanDraft, RoomTemplate, Roster } from "./classroomPlannerTypes";

type PlannerStateMock = {
  activateGroupingHistoryDraft: ReturnType<typeof vi.fn>;
  activateSeatingHistoryDraft: ReturnType<typeof vi.fn>;
  deleteGroupingHistoryDraft: ReturnType<typeof vi.fn>;
  deleteSeatingHistoryDraft: ReturnType<typeof vi.fn>;
  roster: Roster | null;
  template: RoomTemplate | null;
  draft: PlanDraft | null;
  abandonDraft: ReturnType<typeof vi.fn>;
  discardPendingSessionWork: ReturnType<typeof vi.fn>;
  clearWorkspace: ReturnType<typeof vi.fn>;
  prepareForPlannerExit: ReturnType<typeof vi.fn>;
  prepareForWorkspaceSwitch: ReturnType<typeof vi.fn>;
  replaceCurrentRoster: ReturnType<typeof vi.fn>;
  replaceCurrentTemplate: ReturnType<typeof vi.fn>;
  getClassWorkspaceSummary: ReturnType<typeof vi.fn>;
  resolveDraft: ReturnType<typeof vi.fn>;
  startNewGroupingDraft: ReturnType<typeof vi.fn>;
  startNewSeatingDraft: ReturnType<typeof vi.fn>;
  loadWorkspace: ReturnType<typeof vi.fn>;
  getResumableDraft: ReturnType<typeof vi.fn>;
};

const clientMocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiGet: vi.fn(),
}));

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    roster: null,
    template: null,
    draft: null,
    activateGroupingHistoryDraft: vi.fn(),
    activateSeatingHistoryDraft: vi.fn(),
    deleteGroupingHistoryDraft: vi.fn(),
    deleteSeatingHistoryDraft: vi.fn(),
    abandonDraft: vi.fn(),
    discardPendingSessionWork: vi.fn(),
    clearWorkspace: vi.fn(),
    prepareForPlannerExit: vi.fn(),
    prepareForWorkspaceSwitch: vi.fn(),
    replaceCurrentRoster: vi.fn(),
    replaceCurrentTemplate: vi.fn(),
    getClassWorkspaceSummary: vi.fn(),
    resolveDraft: vi.fn(),
    startNewGroupingDraft: vi.fn(),
    startNewSeatingDraft: vi.fn(),
    loadWorkspace: vi.fn(),
    getResumableDraft: vi.fn(),
  }))(),
}));

const routerMocks = vi.hoisted(() => ({
  router: {
    replace: vi.fn(),
  },
}));

vi.mock("../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../api/client")>("../../api/client");
  return {
    ...actual,
    apiDelete: clientMocks.apiDelete,
    apiGet: clientMocks.apiGet,
  };
});

vi.mock("vue-router", async () => {
  const actual = await vi.importActual<typeof import("vue-router")>("vue-router");
  return {
    ...actual,
    useRouter: () => routerMocks.router,
  };
});

vi.mock("./useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

async function flushPromises(): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    await Promise.resolve();
    await nextTick();
  }
}

function createDeferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

export function resetPlannerViewState(): void {
  setActivePinia(createPinia());
  vi.restoreAllMocks();
  clientMocks.apiDelete.mockReset();
  clientMocks.apiGet.mockReset();
  routerMocks.router.replace.mockReset();
  stateMocks.plannerState.abandonDraft.mockReset();
  stateMocks.plannerState.activateGroupingHistoryDraft.mockReset();
  stateMocks.plannerState.activateSeatingHistoryDraft.mockReset();
  stateMocks.plannerState.discardPendingSessionWork.mockReset();
  stateMocks.plannerState.clearWorkspace.mockReset();
  stateMocks.plannerState.deleteGroupingHistoryDraft.mockReset();
  stateMocks.plannerState.deleteSeatingHistoryDraft.mockReset();
  stateMocks.plannerState.prepareForPlannerExit.mockReset();
  stateMocks.plannerState.prepareForWorkspaceSwitch.mockReset();
  stateMocks.plannerState.replaceCurrentRoster.mockReset();
  stateMocks.plannerState.replaceCurrentTemplate.mockReset();
  stateMocks.plannerState.getClassWorkspaceSummary.mockReset();
  stateMocks.plannerState.loadWorkspace.mockReset();
  stateMocks.plannerState.resolveDraft.mockReset();
  stateMocks.plannerState.startNewGroupingDraft.mockReset();
  stateMocks.plannerState.startNewSeatingDraft.mockReset();
  stateMocks.plannerState.getResumableDraft.mockReset();
  stateMocks.plannerState.roster = null;
  stateMocks.plannerState.template = null;
  stateMocks.plannerState.draft = null;
  stateMocks.plannerState.prepareForPlannerExit.mockResolvedValue({ status: "saved" });
  stateMocks.plannerState.prepareForWorkspaceSwitch.mockResolvedValue({
    status: "saved",
    message: null,
  });
  localStorage.clear();
  vi.spyOn(window.performance, "getEntriesByType").mockReturnValue([]);
  window.history.replaceState(null, "");
}

export { clientMocks, stateMocks, routerMocks, flushPromises, createDeferred };
