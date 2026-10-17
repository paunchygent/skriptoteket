import { afterEach, beforeEach, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useClassroomState } from "./useClassroomState";
import type { DraftWorkspaceResponse, RosterSmartRulesResponse } from "./classroomPlannerTypes";

const clientMocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  isApiError: vi.fn(() => false),
}));

vi.mock("../../api/client", () => {
  class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  }

  return {
    ApiError,
    apiDelete: clientMocks.apiDelete,
    apiGet: clientMocks.apiGet,
    apiPatch: clientMocks.apiPatch,
    apiPost: clientMocks.apiPost,
    isApiError: clientMocks.isApiError,
  };
});

function createDraft(
  templateId: string | null = "template-1",
  draftKind: "seating" | "grouping" = "seating",
) {
  return {
    id: "draft-1",
    roster_id: "roster-1",
    draft_kind: draftKind,
    template_id: templateId,
    status: "active" as const,
    revision: 4,
    last_opened_at: "2026-03-21T10:00:00Z",
  };
}

function createWorkspaceResponse(
  templateId: string | null = "template-1",
  draftKind: "seating" | "grouping" = "seating",
  historyStatus: { can_undo: boolean; can_redo: boolean } = {
    can_undo: false,
    can_redo: false,
  },
): DraftWorkspaceResponse {
  return {
    draft: createDraft(templateId, draftKind),
    roster: {
      id: "roster-1",
      name: "Klass 9A",
      students: [
        { id: "s1", display_name: "Student 1" },
        { id: "s2", display_name: "Student 2" },
        { id: "s3", display_name: "Student 3" },
      ],
    },
    template:
      templateId === null
        ? null
        : {
            id: "template-1",
            name: "Sal 101",
            seats: [
              { id: "seat-1", x: 0, y: 0, zone: "front" },
              { id: "seat-2", x: 120, y: 0, zone: "front" },
            ],
            fixtures: [],
          },
    groups: [
      { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ],
    group_assignments: [],
    seat_assignments: [],
    history_status: historyStatus,
  };
}

function createSmartRulesResponse(): RosterSmartRulesResponse {
  return {
    roster_id: "roster-1",
    revision: 0,
    seating_preferences: [],
    relationship_rules: [],
  };
}

function createProfileResponse() {
  return {
    user: {
      id: "user-1",
      email: "teacher@example.com",
      role: "user" as const,
      auth_provider: "local" as const,
    },
    profile: {
      user_id: "user-1",
      locale: "sv-SE",
      created_at: "2026-05-09T10:00:00.000Z",
      updated_at: "2026-05-09T10:00:00.000Z",
    },
  };
}

function createWorkspaceVariant(options: {
  draftId?: string;
  rosterId?: string;
  templateId?: string | null;
  draftKind?: "seating" | "grouping";
  historyStatus?: { can_undo: boolean; can_redo: boolean };
} = {}): DraftWorkspaceResponse {
  const workspace = createWorkspaceResponse(
    options.templateId ?? "template-1",
    options.draftKind ?? "seating",
    options.historyStatus,
  );
  const rosterId = options.rosterId ?? workspace.roster.id;
  const draftId = options.draftId ?? workspace.draft.id;
  return {
    ...workspace,
    draft: {
      ...workspace.draft,
      id: draftId,
      roster_id: rosterId,
      template_id: options.templateId ?? workspace.draft.template_id,
    },
    roster: {
      ...workspace.roster,
      id: rosterId,
    },
    template:
      options.templateId === null
        ? null
        : workspace.template,
  };
}

function createDeferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
}

function mockWorkspaceLoad(
  workspace = createWorkspaceResponse(),
  smartRules = createSmartRulesResponse(),
): void {
  clientMocks.apiGet.mockResolvedValueOnce(workspace);
  clientMocks.apiGet.mockResolvedValueOnce(smartRules);
}

function seedWorkspace() {
  const state = useClassroomState();
  state.roster = {
    id: "roster-1",
    name: "Klass 9A",
    students: [
      { id: "s1", display_name: "Student 1" },
      { id: "s2", display_name: "Student 2" },
      { id: "s3", display_name: "Student 3" },
    ],
  };
  state.template = {
    id: "template-1",
    name: "Sal 101",
    seats: [
      { id: "seat-1", x: 0, y: 0, zone: "front" },
      { id: "seat-2", x: 120, y: 0, zone: "front" },
    ],
    fixtures: [],
  };
  state.groups = [
    { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
    { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
  ];
  state.groupAssignmentsByStudentId = {};
  state.seatAssignmentsByStudentId = {};
  state.smartRulesRevision = 0;
  state.smartRuleHydrationStatus = "ready";
  return state;
}

export function setupClassroomStateTests() {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    clientMocks.apiGet.mockReset();
    clientMocks.apiPatch.mockReset();
    clientMocks.apiPost.mockReset();
    clientMocks.apiDelete.mockReset();
    clientMocks.isApiError.mockReset();
    clientMocks.isApiError.mockReturnValue(false);
  });

  afterEach(() => {
    // Pending autosaves belong to this test, never the next test's API mocks.
    vi.clearAllTimers();
    vi.useRealTimers();
  });
}

export {
  clientMocks,
  createDraft,
  createWorkspaceResponse,
  createSmartRulesResponse,
  createProfileResponse,
  createWorkspaceVariant,
  createDeferred,
  mockWorkspaceLoad,
  seedWorkspace,
};
