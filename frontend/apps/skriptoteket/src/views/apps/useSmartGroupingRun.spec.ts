/**
 * Smart grouping run orchestration tests.
 *
 * These tests lock the frontend-only smart grouping flow so `Slumpa` flushes
 * both persistence lanes before calling the backend smart-run endpoint and
 * preserves the strict applied-or-blocked contract from PR-0167.
 */

import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSmartGroupingRun } from "./useSmartGroupingRun";
import type { DraftWorkspaceResponse } from "./classroomPlannerTypes";

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
      draft_kind: "grouping",
      template_id: "template-1",
      smart_enabled: true,
      use_history: true,
      grouping_seating_distance_enabled: true,
      status: "active",
      revision,
      last_opened_at: "2026-03-30T10:00:00Z",
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
      can_undo: true,
      can_redo: false,
    },
  };
}

describe("useSmartGroupingRun", () => {
  beforeEach(() => {
    clientMocks.apiPost.mockReset();
  });

  it("flushes both lanes before calling the backend smart-run endpoint", async () => {
    const draft = ref(createWorkspace().draft);
    const applyWorkspace = vi.fn((workspace: DraftWorkspaceResponse) => {
      draft.value = workspace.draft;
    });
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: createWorkspace(6),
      used_history: true,
      used_live_seating: true,
      message: "Smart gruppindelning klar med historik och stöd från klassens sittschema.",
    });

    const smartRun = useSmartGroupingRun({
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      applyWorkspace,
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "applied",
      message: "Smart gruppindelning klar med historik och stöd från klassens sittschema.",
    });
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft-1/smart-run",
      { expected_revision: 5 },
    );
    expect(applyWorkspace).toHaveBeenCalledWith(createWorkspace(6));
    expect(smartRun.message.value).toBe(
      "Smart gruppindelning klar med historik och stöd från klassens sittschema.",
    );
    expect(smartRun.tone.value).toBe("success");
  });

  it("blocks the backend call when the smart-rule lane cannot flush honestly", async () => {
    const draft = ref(createWorkspace().draft);
    const smartRun = useSmartGroupingRun({
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({
        status: "blocked",
        reason: "conflict",
        message: "Lös sparkonflikten innan du fortsätter.",
      }),
      applyWorkspace: vi.fn(),
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "blocked",
      message: "Lös sparkonflikten innan du fortsätter.",
    });
    expect(clientMocks.apiPost).not.toHaveBeenCalled();
    expect(smartRun.message.value).toBe("Lös sparkonflikten innan du fortsätter.");
    expect(smartRun.tone.value).toBe("warning");
  });

  it("surfaces the typed no-history block without mutating the workspace", async () => {
    const draft = ref(createWorkspace().draft);
    const applyWorkspace = vi.fn();
    clientMocks.apiPost.mockResolvedValue({
      status: "blocked",
      reason: "no_history",
      workspace: null,
      used_history: false,
      used_live_seating: false,
      message: "För att använda historik behöver du först exportera en gruppindelning för den här klassen.",
    });
    const smartRun = useSmartGroupingRun({
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      applyWorkspace,
      normalizeErrorMessage: vi.fn(() => "fallback"),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "blocked",
      message: "För att använda historik behöver du först exportera en gruppindelning för den här klassen.",
    });
    expect(applyWorkspace).not.toHaveBeenCalled();
    expect(smartRun.tone.value).toBe("warning");
  });
});
