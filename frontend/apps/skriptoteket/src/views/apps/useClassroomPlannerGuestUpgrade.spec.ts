/**
 * Klassrumskartan authenticated guest-upgrade gate tests.
 *
 * These tests verify that the authenticated gate previews a ready guest
 * snapshot, clears local browser state only after commit success, and leaves
 * local guest data untouched when the teacher postpones the import.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useClassroomPlannerGuestUpgrade } from "./useClassroomPlannerGuestUpgrade";

const guestUpgradeApiMocks = vi.hoisted(() => ({
  getClassroomPlannerGuestUpgradeConsumptionStatus: vi.fn(),
  runClassroomPlannerGuestUpgrade: vi.fn(),
}));

vi.mock("./classroomPlannerGuestUpgradeApi", () => ({
  getClassroomPlannerGuestUpgradeConsumptionStatus:
    guestUpgradeApiMocks.getClassroomPlannerGuestUpgradeConsumptionStatus,
  runClassroomPlannerGuestUpgrade: guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade,
}));

function mountGuestUpgradeHarness(
  options?: Parameters<typeof useClassroomPlannerGuestUpgrade>[0],
) {
  let exposedState: ReturnType<typeof useClassroomPlannerGuestUpgrade> | null = null;

  const Harness = defineComponent({
    setup() {
      exposedState = useClassroomPlannerGuestUpgrade(options);
      return () => null;
    },
  });

  mount(Harness);
  return {
    getState() {
      if (!exposedState) {
        throw new Error("Guest upgrade harness did not expose state.");
      }
      return exposedState;
    },
  };
}

async function flushGuestUpgradeWork(): Promise<void> {
  await nextTick();
  await Promise.resolve();
  await Promise.resolve();
}

function createReadyGuestStorage() {
  return {
    loadCurrentSnapshot: vi.fn(async () => ({
      status: "ready" as const,
      snapshot: {
        schema_version: 1 as const,
        profile: "public_browser_workspace_with_upgrade" as const,
        snapshot_id: "guest-snapshot-1",
        snapshot_content_hash: "sha256:guest",
        created_at: "2026-04-04T08:00:00.000Z",
        updated_at: "2026-04-04T08:00:00.000Z",
        expires_at: "2026-04-18T08:00:00.000Z",
        rosters: [],
        templates: [],
        smart_rule_sets: [],
        grouping_draft: null,
        seating_draft: null,
        checkpoint_descriptors: [],
        ui_state: {
          selected_roster_local_id: null,
          selected_template_local_id: null,
          current_screen: "class-workspace" as const,
          planner_initial_view: "groups" as const,
          dismissed_grouping_draft_local_id: null,
          dismissed_seating_draft_local_id: null,
          fingerprint: "sha256:ui",
        },
      },
      summary: {
        snapshot_id: "guest-snapshot-1",
        profile: "public_browser_workspace_with_upgrade" as const,
        created_at: "2026-04-04T08:00:00.000Z",
        updated_at: "2026-04-04T08:00:00.000Z",
        expires_at: "2026-04-18T08:00:00.000Z",
        roster_count: 1,
        template_count: 0,
        smart_rule_set_count: 0,
        checkpoint_count: 0,
        has_grouping_draft: false,
        has_seating_draft: false,
      },
    })),
    saveSnapshot: vi.fn(),
    initializeEmptySnapshot: vi.fn(),
    clearCurrentSnapshot: vi.fn(async () => undefined),
    isGuestAuthoringClosed: vi.fn(async () => false),
    markGuestAuthoringClosed: vi.fn(async () => undefined),
  };
}

function createEmptyGuestStorage() {
  return {
    loadCurrentSnapshot: vi.fn(async () => ({
      status: "ready" as const,
      snapshot: {
        schema_version: 1 as const,
        profile: "public_browser_workspace_with_upgrade" as const,
        snapshot_id: "guest-snapshot-empty",
        snapshot_content_hash: "sha256:guest-empty",
        created_at: "2026-04-04T08:00:00.000Z",
        updated_at: "2026-04-04T08:00:00.000Z",
        expires_at: "2026-04-18T08:00:00.000Z",
        rosters: [],
        templates: [],
        smart_rule_sets: [],
        grouping_draft: null,
        seating_draft: null,
        checkpoint_descriptors: [],
        ui_state: {
          selected_roster_local_id: null,
          selected_template_local_id: null,
          current_screen: "class-workspace" as const,
          planner_initial_view: "groups" as const,
          dismissed_grouping_draft_local_id: null,
          dismissed_seating_draft_local_id: null,
          fingerprint: "sha256:ui-empty",
        },
      },
      summary: {
        snapshot_id: "guest-snapshot-empty",
        profile: "public_browser_workspace_with_upgrade" as const,
        created_at: "2026-04-04T08:00:00.000Z",
        updated_at: "2026-04-04T08:00:00.000Z",
        expires_at: "2026-04-18T08:00:00.000Z",
        roster_count: 0,
        template_count: 0,
        smart_rule_set_count: 0,
        checkpoint_count: 0,
        has_grouping_draft: false,
        has_seating_draft: false,
      },
    })),
    saveSnapshot: vi.fn(),
    initializeEmptySnapshot: vi.fn(),
    clearCurrentSnapshot: vi.fn(async () => undefined),
    isGuestAuthoringClosed: vi.fn(async () => false),
    markGuestAuthoringClosed: vi.fn(async () => undefined),
  };
}

describe("useClassroomPlannerGuestUpgrade", () => {
  beforeEach(() => {
    guestUpgradeApiMocks.getClassroomPlannerGuestUpgradeConsumptionStatus.mockReset();
    guestUpgradeApiMocks.getClassroomPlannerGuestUpgradeConsumptionStatus.mockResolvedValue({
      consumed: false,
    });
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade.mockReset();
  });

  it("previews a ready local guest snapshot and shows the prompt", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade.mockResolvedValueOnce({
      mode: "preview",
      snapshot_id: "guest-snapshot-1",
      schema_version: 1,
      submitted_snapshot_content_hash: "sha256:guest",
      server_snapshot_content_hash: "sha256:server",
      created: [],
      reused: [],
      skipped: [],
      conflicted: [],
    });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();

    expect(guestStorage.loadCurrentSnapshot).toHaveBeenCalledOnce();
    expect(guestStorage.markGuestAuthoringClosed).toHaveBeenCalledOnce();
    expect(guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade).toHaveBeenCalledWith({
      mode: "preview",
      snapshot: expect.objectContaining({ snapshot_id: "guest-snapshot-1" }),
    });
    expect(harness.getState().shouldShowPrompt.value).toBe(true);
    expect(harness.getState().previewReceipt.value?.server_snapshot_content_hash).toBe(
      "sha256:server",
    );
  });

  it("clears an empty guest snapshot without calling preview or showing the prompt", async () => {
    const guestStorage = createEmptyGuestStorage();

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();

    expect(guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade).not.toHaveBeenCalled();
    expect(guestStorage.markGuestAuthoringClosed).toHaveBeenCalledOnce();
    expect(guestStorage.clearCurrentSnapshot).toHaveBeenCalledOnce();
    expect(harness.getState().gateState.value).toBe("allowed");
    expect(harness.getState().shouldShowPrompt.value).toBe(false);
    expect(harness.getState().snapshot.value).toBeNull();
    expect(harness.getState().summary.value).toBeNull();
    expect(harness.getState().lastReceipt.value).toBeNull();
  });

  it("clears local guest data only after commit success", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade
      .mockResolvedValueOnce({
        mode: "preview",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [],
      })
      .mockResolvedValueOnce({
        mode: "commit",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [{ entity_type: "roster", local_id: "roster-1" }],
        reused: [],
        skipped: [],
        conflicted: [],
      });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();
    await harness.getState().importGuestWorkspace();

    expect(guestStorage.clearCurrentSnapshot).toHaveBeenCalledOnce();
    expect(harness.getState().plannerRefreshKey.value).toBe(1);
    expect(harness.getState().gateState.value).toBe("allowed");
    expect(harness.getState().snapshot.value).toBeNull();
    expect(harness.getState().lastReceipt.value?.mode).toBe("commit");
  });

  it("keeps local guest data when the commit receipt reports only conflicts", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade
      .mockResolvedValueOnce({
        mode: "preview",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [],
      })
      .mockResolvedValueOnce({
        mode: "commit",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [{ entity_type: "draft", local_id: "draft-grouping-1" }],
      });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();
    await harness.getState().importGuestWorkspace();

    expect(guestStorage.clearCurrentSnapshot).not.toHaveBeenCalled();
    expect(harness.getState().gateState.value).toBe("prompt");
    expect(harness.getState().shouldShowPrompt.value).toBe(true);
    expect(harness.getState().snapshot.value?.snapshot_id).toBe("guest-snapshot-1");
    expect(harness.getState().previewReceipt.value?.conflicted).toHaveLength(1);
    expect(harness.getState().errorMessage.value).toBe(
      "Allt gick inte att spara. Det som blev kvar finns fortfarande i den här webbläsaren.",
    );
    expect(harness.getState().lastReceipt.value).toBeNull();
  });

  it("clears local guest data and keeps the result summary when commit has mixed success and conflicts", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade
      .mockResolvedValueOnce({
        mode: "preview",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [],
      })
      .mockResolvedValueOnce({
        mode: "commit",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [{ entity_type: "roster", local_id: "roster-1" }],
        reused: [],
        skipped: [],
        conflicted: [{ entity_type: "draft", local_id: "draft-grouping-1" }],
      });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();
    await harness.getState().importGuestWorkspace();

    expect(guestStorage.clearCurrentSnapshot).toHaveBeenCalledOnce();
    expect(harness.getState().gateState.value).toBe("allowed");
    expect(harness.getState().lastReceipt.value?.created).toHaveLength(1);
    expect(harness.getState().lastReceipt.value?.conflicted).toHaveLength(1);
    expect(harness.getState().shouldShowPrompt.value).toBe(false);
    expect(harness.getState().errorMessage.value).toBeNull();
  });

  it("allows postponing without clearing local guest data", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade.mockResolvedValueOnce({
        mode: "preview",
      snapshot_id: "guest-snapshot-1",
      schema_version: 1,
      submitted_snapshot_content_hash: "sha256:guest",
      server_snapshot_content_hash: "sha256:server",
      created: [],
      reused: [],
      skipped: [],
      conflicted: [],
    });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();
    harness.getState().postponeGuestWorkspace();

    expect(guestStorage.clearCurrentSnapshot).not.toHaveBeenCalled();
    expect(harness.getState().gateState.value).toBe("allowed");
    expect(harness.getState().snapshot.value?.snapshot_id).toBe("guest-snapshot-1");
  });

  it("allows dismissing the post-import summary after a successful commit", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade
      .mockResolvedValueOnce({
        mode: "preview",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [],
      })
      .mockResolvedValueOnce({
        mode: "commit",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [{ entity_type: "roster", local_id: "roster-1" }],
        reused: [],
        skipped: [],
        conflicted: [],
      });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();
    await harness.getState().importGuestWorkspace();

    expect(harness.getState().lastReceipt.value?.created).toHaveLength(1);

    harness.getState().dismissLastReceiptSummary();

    expect(harness.getState().lastReceipt.value).toBeNull();
  });

  it("keeps a non-empty guest snapshot and avoids success UI when commit returns an all-zero receipt", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade
      .mockResolvedValueOnce({
        mode: "preview",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [],
      })
      .mockResolvedValueOnce({
        mode: "commit",
        snapshot_id: "guest-snapshot-1",
        schema_version: 1,
        submitted_snapshot_content_hash: "sha256:guest",
        server_snapshot_content_hash: "sha256:server",
        created: [],
        reused: [],
        skipped: [],
        conflicted: [],
      });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();
    await harness.getState().importGuestWorkspace();

    expect(guestStorage.clearCurrentSnapshot).not.toHaveBeenCalled();
    expect(harness.getState().gateState.value).toBe("prompt");
    expect(harness.getState().shouldShowPrompt.value).toBe(true);
    expect(harness.getState().snapshot.value?.snapshot_id).toBe("guest-snapshot-1");
    expect(harness.getState().lastReceipt.value).toBeNull();
    expect(harness.getState().errorMessage.value).toBe(
      "Importen skapade inget nytt i kontot. Gästarbetet finns kvar i den här webbläsaren.",
    );
  });

  it("clears stale local guest data silently when the backend ledger says the bridge was consumed", async () => {
    const guestStorage = createReadyGuestStorage();
    guestUpgradeApiMocks.getClassroomPlannerGuestUpgradeConsumptionStatus.mockResolvedValueOnce({
      consumed: true,
    });

    const harness = mountGuestUpgradeHarness({ enabled: true, guestStorage });
    await flushGuestUpgradeWork();

    expect(guestStorage.clearCurrentSnapshot).toHaveBeenCalledOnce();
    expect(guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade).not.toHaveBeenCalled();
    expect(harness.getState().gateState.value).toBe("allowed");
    expect(harness.getState().snapshot.value).toBeNull();
    expect(harness.getState().shouldShowPrompt.value).toBe(false);
  });
});
