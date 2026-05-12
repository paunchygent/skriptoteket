/**
 * Smart seating run orchestration tests.
 *
 * These tests lock the frontend-only smart seating flow so `Slumpa` flushes
 * both persistence lanes before calling the backend smart-run endpoint and
 * treats no-history first runs as applied backend results.
 */

import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSmartSeatingRun } from "./useSmartSeatingRun";
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
      draft_kind: "seating",
      template_id: "template-1",
      smart_enabled: true,
      use_history: true,
      status: "active",
      revision,
      last_opened_at: "2026-03-27T10:00:00Z",
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
      can_undo: true,
      can_redo: false,
    },
  };
}

describe("useSmartSeatingRun", () => {
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
      message: "Smart placering klar med stöd av tidigare exporter.",
    });

    const smartRun = useSmartSeatingRun({
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
      message: "Smart placering klar med stöd av tidigare exporter.",
    });
    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/drafts/seating/draft-1/smart-run",
      { expected_revision: 5 },
    );
    expect(applyWorkspace).toHaveBeenCalledWith(createWorkspace(6));
    expect(smartRun.message.value).toBe("Smart placering klar med stöd av tidigare exporter.");
    expect(smartRun.tone.value).toBe("success");
  });

  it("blocks the backend call when the smart-rule lane cannot flush honestly", async () => {
    const draft = ref(createWorkspace().draft);
    const smartRun = useSmartSeatingRun({
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

  it("applies a no-history first-run response without warning", async () => {
    const draft = ref(createWorkspace().draft);
    const applyWorkspace = vi.fn((workspace: DraftWorkspaceResponse) => {
      draft.value = workspace.draft;
    });
    clientMocks.apiPost.mockResolvedValue({
      status: "applied",
      workspace: createWorkspace(6),
      used_history: false,
      message: "Smart placering klar.",
    });
    const smartRun = useSmartSeatingRun({
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
      message: "Smart placering klar.",
    });
    expect(applyWorkspace).toHaveBeenCalledWith(createWorkspace(6));
    expect(smartRun.tone.value).toBe("success");
  });

  it("uses teacher-safe copy for fixed-seat validation failures", async () => {
    const draft = ref(createWorkspace().draft);
    clientMocks.apiPost.mockRejectedValue(
      new Error("Fixed-seat rules must reference classroom seats."),
    );
    const smartRun = useSmartSeatingRun({
      draft,
      smartRulesHydrated: ref(true),
      runningState: ref(false),
      flushDraftLane: vi.fn().mockResolvedValue({ status: "saved" }),
      flushSmartRuleLane: vi.fn().mockResolvedValue({ status: "saved" }),
      applyWorkspace: vi.fn(),
      normalizeErrorMessage: vi.fn(() => "Fixed-seat rules must reference classroom seats."),
    });

    const result = await smartRun.run();

    expect(result).toEqual({
      status: "blocked",
      message:
        "En fast plats kan inte användas längre. Kontrollera eleven och platsen och försök igen.",
    });
    expect(smartRun.message.value).toBe(
      "En fast plats kan inte användas längre. Kontrollera eleven och platsen och försök igen.",
    );
    expect(smartRun.tone.value).toBe("warning");
  });
});
