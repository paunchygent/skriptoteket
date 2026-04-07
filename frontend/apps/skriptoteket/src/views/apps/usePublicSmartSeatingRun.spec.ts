/**
 * Public Smart seating run orchestration tests.
 *
 * These tests lock the guest-only Smart seating flow so the browser snapshot
 * is submitted to the public helper route and the accepted solver result is
 * persisted back into guest storage before success is surfaced.
 */

import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import type { DraftWorkspaceResponse } from "./classroomPlannerTypes";
import { usePublicSmartSeatingRun } from "./usePublicSmartSeatingRun";

const clientMocks = vi.hoisted(() => ({
  apiPost: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiPost: clientMocks.apiPost,
}));

function createWorkspace(revision = 5): DraftWorkspaceResponse {
  return {
    draft: {
      id: "draft-1",
      roster_id: "roster-1",
      draft_kind: "seating",
      template_id: "template-1",
      task_entry_classroom_selection_mode: "required",
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: false,
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
    groups: [],
    group_assignments: [],
    seat_assignments: [
      { student_id: "ada", seat_id: "front-right" },
      { student_id: "alan", seat_id: "front-left" },
    ],
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
    grouping_draft: null,
    seating_draft: {
      local_id: "draft-1",
      draft_kind: "seating",
      roster_local_id: "roster-1",
      template_local_id: "template-1",
      task_entry_classroom_selection_mode: "required",
      smart_enabled: true,
      use_history: false,
      grouping_seating_distance_enabled: false,
      revision: 5,
      last_opened_at: "2026-04-07T10:00:00Z",
      groups: [],
      group_assignments: [],
      seat_assignments: [
        { student_id: "ada", seat_id: "front-left" },
        { student_id: "alan", seat_id: "front-right" },
      ],
      fingerprint: "sha256:seating-draft",
    },
    checkpoint_descriptors: [],
    ui_state: {
      selected_roster_local_id: "roster-1",
      selected_template_local_id: "template-1",
      current_screen: "planner",
      planner_initial_view: "seats",
      dismissed_grouping_draft_local_id: null,
      dismissed_seating_draft_local_id: null,
      fingerprint: "sha256:ui-state",
    },
  };
}

describe("usePublicSmartSeatingRun", () => {
  beforeEach(() => {
    clientMocks.apiPost.mockReset();
  });

  it("submits the browser-owned snapshot to the public helper and persists the accepted workspace", async () => {
    const snapshot = createSnapshot();
    let currentWorkspace = createWorkspace();
    const draft = ref(currentWorkspace.draft);
    const applyWorkspace = vi.fn((workspace: DraftWorkspaceResponse) => {
      currentWorkspace = workspace;
      draft.value = workspace.draft;
    });
    const persistAppliedWorkspace = vi.fn().mockResolvedValue({ status: "saved" });
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: createWorkspace(6),
      used_history: false,
      message: "Smart placering klar.",
    });

    const smartRun = usePublicSmartSeatingRun({
      apiPath: "/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run",
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      getSnapshot: vi.fn().mockResolvedValue(snapshot),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      getCurrentWorkspace: vi.fn(() => currentWorkspace),
      applyWorkspace,
      persistAppliedWorkspace,
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "applied",
      message: "Smart placering klar.",
    });
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run",
      {
        expected_revision: 5,
        snapshot,
      },
    );
    expect(applyWorkspace).toHaveBeenCalledWith(createWorkspace(6));
    expect(persistAppliedWorkspace).toHaveBeenCalledTimes(1);
    expect(smartRun.tone.value).toBe("success");
  });

  it("blocks success when the accepted workspace cannot be persisted back into guest storage", async () => {
    const initialWorkspace = createWorkspace();
    let currentWorkspace = initialWorkspace;
    const draft = ref(initialWorkspace.draft);
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: createWorkspace(6),
      used_history: false,
      message: "Smart placering klar.",
    });

    const smartRun = usePublicSmartSeatingRun({
      apiPath: "/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run",
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      getSnapshot: vi.fn().mockResolvedValue(createSnapshot()),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      getCurrentWorkspace: vi.fn(() => currentWorkspace),
      applyWorkspace: vi.fn((workspace: DraftWorkspaceResponse) => {
        currentWorkspace = workspace;
        draft.value = workspace.draft;
      }),
      persistAppliedWorkspace: vi.fn().mockResolvedValue({
        status: "blocked",
        reason: "conflict",
        message: "Lös sparkonflikten innan du fortsätter.",
      }),
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "blocked",
      message: "Lös sparkonflikten innan du fortsätter.",
    });
    expect(currentWorkspace).toEqual(initialWorkspace);
    expect(draft.value.revision).toBe(5);
    expect(smartRun.message.value).toBe("Lös sparkonflikten innan du fortsätter.");
    expect(smartRun.tone.value).toBe("warning");
  });
});
