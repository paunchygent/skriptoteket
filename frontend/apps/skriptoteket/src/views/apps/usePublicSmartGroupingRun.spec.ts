/**
 * Public Smart grouping run orchestration tests.
 *
 * These tests lock the guest-only Smart grouping flow so the browser snapshot
 * is submitted to the public helper route and the accepted solver result is
 * persisted back into guest storage before success is surfaced.
 */

import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import { PUBLIC_SMART_REVISION_CONFLICT_MESSAGE } from "./classroomPlannerPublicSmartRunFeedback";
import type { DraftWorkspaceResponse } from "./classroomPlannerTypes";
import { usePublicSmartGroupingRun } from "./usePublicSmartGroupingRun";

const clientMocks = vi.hoisted(() => ({
  apiPost: vi.fn(),
  isApiError: vi.fn((error: unknown) => {
    return Boolean(error && typeof error === "object" && "status" in error);
  }),
}));

vi.mock("../../api/client", () => ({
  apiPost: clientMocks.apiPost,
  isApiError: clientMocks.isApiError,
}));

function createWorkspace(revision = 5): DraftWorkspaceResponse {
  return {
    draft: {
      id: "draft-1",
      roster_id: "roster-1",
      draft_kind: "grouping",
      template_id: "template-1",
      task_entry_classroom_selection_mode: "optional",
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: true,
      status: "active",
      revision,
      last_opened_at: "2026-04-07T10:00:00Z",
    },
    roster: {
      id: "roster-1",
      name: "SA24D",
      students: [
        { id: "ada", display_name: "Ada" },
        { id: "alan", display_name: "Alan" },
      ],
    },
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [
        { id: "front-left", x: 0, y: 0, zone: null },
        { id: "front-right", x: 1, y: 0, zone: null },
      ],
      fixtures: [],
    },
    groups: [
      { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ],
    group_assignments: [
      { student_id: "ada", group_id: "group-b" },
      { student_id: "alan", group_id: "group-a" },
    ],
    seat_assignments: [],
    history_status: {
      can_undo: false,
      can_redo: false,
    },
  };
}

function createSnapshot(): ClassroomPlannerGuestSnapshot {
  return {
    schema_version: 1,
    profile: "public_browser_workspace_with_upgrade",
    snapshot_id: "snapshot-1",
    snapshot_content_hash: "sha256:snapshot",
    created_at: "2026-04-07T09:00:00Z",
    updated_at: "2026-04-07T10:00:00Z",
    expires_at: "2026-04-21T10:00:00Z",
    rosters: [
      {
        local_id: "roster-1",
        name: "SA24D",
        students: [
          { local_id: "ada", display_name: "Ada" },
          { local_id: "alan", display_name: "Alan" },
        ],
        fingerprint: "sha256:roster",
      },
    ],
    templates: [
      {
        local_id: "template-1",
        name: "Sal 101",
        grid_cols: 4,
        grid_rows: 4,
        seats: [
          { id: "front-left", x: 0, y: 0, zone: null },
          { id: "front-right", x: 1, y: 0, zone: null },
        ],
        fixtures: [],
        fingerprint: "sha256:template",
      },
    ],
    smart_rule_sets: [
      {
        roster_local_id: "roster-1",
        revision: 1,
        seating_preferences: [],
        relationship_rules: [],
        fingerprint: "sha256:rules",
      },
    ],
    grouping_draft: {
      local_id: "draft-1",
      draft_kind: "grouping",
      roster_local_id: "roster-1",
      template_local_id: "template-1",
      task_entry_classroom_selection_mode: "optional",
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: true,
      revision: 5,
      last_opened_at: "2026-04-07T10:00:00Z",
      groups: [
        { id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false },
        { id: "group-b", name: "Grupp 2", sort_order: 1, name_is_custom: false },
      ],
      group_assignments: [
        { student_id: "ada", group_id: "group-a" },
        { student_id: "alan", group_id: "group-b" },
      ],
      seat_assignments: [],
      fingerprint: "sha256:grouping-draft",
    },
    seating_draft: null,
    checkpoint_descriptors: [],
    ui_state: {
      selected_roster_local_id: "roster-1",
      selected_template_local_id: "template-1",
      current_screen: "planner",
      planner_initial_view: "groups",
      dismissed_grouping_draft_local_id: null,
      dismissed_seating_draft_local_id: null,
      fingerprint: "sha256:ui-state",
    },
  };
}

describe("usePublicSmartGroupingRun", () => {
  beforeEach(() => {
    clientMocks.apiPost.mockReset();
    clientMocks.isApiError.mockClear();
  });

  it("commits the visible workspace before the public helper and the accepted result before success", async () => {
    const snapshot = createSnapshot();
    let currentWorkspace = createWorkspace();
    const draft = ref(currentWorkspace.draft);
    const applyWorkspace = vi.fn((workspace: DraftWorkspaceResponse) => {
      currentWorkspace = workspace;
      draft.value = workspace.draft;
    });
    const commitWorkspaceToSnapshot = vi.fn().mockResolvedValueOnce(snapshot).mockResolvedValueOnce({
      ...snapshot,
      grouping_draft: {
        ...snapshot.grouping_draft!,
        revision: 6,
      },
    });
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: createWorkspace(6),
      used_history: false,
      used_live_seating: true,
      message: "Smart gruppindelning klar med stöd från klassens sittschema.",
    });

    const smartRun = usePublicSmartGroupingRun({
      apiPath: "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      getCurrentWorkspace: vi.fn(() => currentWorkspace),
      applyWorkspace,
      commitWorkspaceToSnapshot,
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "applied",
      message: "Smart gruppindelning klar med stöd från klassens sittschema.",
    });
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
      {
        expected_revision: 5,
        snapshot,
      },
    );
    expect(commitWorkspaceToSnapshot).toHaveBeenNthCalledWith(1, createWorkspace(5));
    expect(commitWorkspaceToSnapshot).toHaveBeenNthCalledWith(2, createWorkspace(6));
    expect(commitWorkspaceToSnapshot.mock.invocationCallOrder[0]).toBeLessThan(
      clientMocks.apiPost.mock.invocationCallOrder[0],
    );
    expect(commitWorkspaceToSnapshot.mock.invocationCallOrder[1]).toBeLessThan(
      applyWorkspace.mock.invocationCallOrder[0],
    );
    expect(applyWorkspace).toHaveBeenCalledWith(createWorkspace(6));
    expect(smartRun.tone.value).toBe("success");
  });

  it("sends the committed snapshot revision on a second Smart Slumpa run", async () => {
    let snapshot = createSnapshot();
    let currentWorkspace = createWorkspace(5);
    const draft = ref(currentWorkspace.draft);
    const commitWorkspaceToSnapshot = vi.fn(async (workspace: DraftWorkspaceResponse) => {
      snapshot = {
        ...snapshot,
        grouping_draft: {
          ...snapshot.grouping_draft!,
          revision: workspace.draft.revision,
          group_assignments: workspace.group_assignments,
        },
      };
      return snapshot;
    });
    clientMocks.apiPost
      .mockResolvedValueOnce({
        status: "applied",
        workspace: createWorkspace(6),
        used_history: false,
        used_live_seating: true,
        message: "Smart gruppindelning klar.",
      })
      .mockResolvedValueOnce({
        status: "applied",
        workspace: createWorkspace(7),
        used_history: false,
        used_live_seating: true,
        message: "Smart gruppindelning klar.",
      });

    const smartRun = usePublicSmartGroupingRun({
      apiPath: "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      getCurrentWorkspace: vi.fn(() => currentWorkspace),
      commitWorkspaceToSnapshot,
      applyWorkspace: vi.fn((workspace: DraftWorkspaceResponse) => {
        currentWorkspace = workspace;
        draft.value = workspace.draft;
      }),
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    await smartRun.run();
    await smartRun.run();

    const secondRequest = clientMocks.apiPost.mock.calls[1]?.[1] as {
      expected_revision: number;
      snapshot: ClassroomPlannerGuestSnapshot;
    };
    expect(secondRequest.expected_revision).toBe(6);
    expect(secondRequest.snapshot.grouping_draft?.revision).toBe(6);
    expect(commitWorkspaceToSnapshot).toHaveBeenCalledTimes(4);
  });

  it("blocks success when the accepted workspace cannot be committed to guest storage", async () => {
    const initialWorkspace = createWorkspace();
    let currentWorkspace = initialWorkspace;
    const draft = ref(initialWorkspace.draft);
    const applyWorkspace = vi.fn((workspace: DraftWorkspaceResponse) => {
      currentWorkspace = workspace;
      draft.value = workspace.draft;
    });
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: createWorkspace(6),
      used_history: false,
      used_live_seating: false,
      message: "Smart gruppindelning klar.",
    });

    const smartRun = usePublicSmartGroupingRun({
      apiPath: "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      getCurrentWorkspace: vi.fn(() => currentWorkspace),
      applyWorkspace,
      commitWorkspaceToSnapshot: vi.fn()
        .mockResolvedValueOnce(createSnapshot())
        .mockRejectedValueOnce(new Error("storage unavailable")),
      normalizeErrorMessage: vi.fn(() => "Kunde inte spara Smart-resultatet."),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "blocked",
      message: "Kunde inte spara Smart-resultatet.",
    });
    expect(currentWorkspace).toEqual(initialWorkspace);
    expect(applyWorkspace).not.toHaveBeenCalled();
    expect(draft.value.revision).toBe(5);
    expect(smartRun.message.value).toBe("Kunde inte spara Smart-resultatet.");
    expect(smartRun.tone.value).toBe("warning");
  });

  it("sanitizes public revision-conflict feedback before it reaches the run message", async () => {
    const currentWorkspace = createWorkspace();
    const draft = ref(currentWorkspace.draft);
    clientMocks.apiPost.mockRejectedValue({
      status: 409,
      message: "Draft revision mismatch. Expected 2, got 1.",
    });

    const smartRun = usePublicSmartGroupingRun({
      apiPath: "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      getCurrentWorkspace: vi.fn(() => currentWorkspace),
      commitWorkspaceToSnapshot: vi.fn().mockResolvedValue(createSnapshot()),
      applyWorkspace: vi.fn(),
      normalizeErrorMessage: vi.fn(() => "Draft revision mismatch. Expected 2, got 1."),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "blocked",
      message: PUBLIC_SMART_REVISION_CONFLICT_MESSAGE,
    });
    expect(smartRun.message.value).toBe(PUBLIC_SMART_REVISION_CONFLICT_MESSAGE);
    expect(smartRun.message.value).not.toContain("Draft revision mismatch");
  });
});
