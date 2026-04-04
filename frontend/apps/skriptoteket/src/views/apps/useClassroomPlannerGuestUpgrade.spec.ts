/**
 * Klassrumskartan authenticated guest-upgrade gate tests.
 *
 * These tests verify that the authenticated gate previews a ready guest
 * snapshot, clears local browser state only after commit success, and leaves
 * local guest data untouched when the teacher postpones the import.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

import { useClassroomPlannerGuestUpgrade } from "./useClassroomPlannerGuestUpgrade";

const guestUpgradeApiMocks = vi.hoisted(() => ({
  runClassroomPlannerGuestUpgrade: vi.fn(),
}));

vi.mock("./classroomPlannerGuestUpgradeApi", () => ({
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
  };
}

describe("useClassroomPlannerGuestUpgrade", () => {
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
    expect(guestUpgradeApiMocks.runClassroomPlannerGuestUpgrade).toHaveBeenCalledWith({
      mode: "preview",
      snapshot: expect.objectContaining({ snapshot_id: "guest-snapshot-1" }),
    });
    expect(harness.getState().shouldShowPrompt.value).toBe(true);
    expect(harness.getState().previewReceipt.value?.server_snapshot_content_hash).toBe(
      "sha256:server",
    );
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
    expect(harness.getState().gateState.value).toBe("allowed");
    expect(harness.getState().snapshot.value).toBeNull();
    expect(harness.getState().lastReceipt.value?.mode).toBe("commit");
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
});
