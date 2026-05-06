/**
 * Guest grouping-context regression tests for Klassrumskartan.
 *
 * These tests lock the public guest controller seam that must preserve the
 * selected classroom context when the user enters `Grupper` from overview.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createClassroomPlannerGuestSnapshotFromSeed } from "./classroomPlannerGuestSnapshotMapping";
import { summarizeClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import { useClassroomPlannerGuestController } from "./useClassroomPlannerGuestController";

function mountGuestControllerHarness(
  options?: Parameters<typeof useClassroomPlannerGuestController>[0],
) {
  let exposedState: ReturnType<typeof useClassroomPlannerGuestController> | null = null;

  const Harness = defineComponent({
    setup() {
      exposedState = useClassroomPlannerGuestController(options);
      return () => null;
    },
  });

  mount(Harness);
  return {
    getState() {
      if (!exposedState) {
        throw new Error("Guest controller harness did not expose state.");
      }
      return exposedState;
    },
  };
}

async function flushGuestController(): Promise<void> {
  await nextTick();
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
}

describe("useClassroomPlannerGuestController grouping context", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("preserves the selected classroom context when opening grouping from overview", async () => {
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-grouping-context-1",
      created_at: "2026-04-07T12:00:00.000Z",
      updated_at: "2026-04-07T12:00:00.000Z",
      expires_at: "2026-04-21T12:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [
            { id: "student-1", display_name: "Ada" },
            { id: "student-2", display_name: "Bo" },
          ],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "G20",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
      ],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: "template-1",
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    const saveSnapshot = vi.fn(async () => undefined);
    const harness = mountGuestControllerHarness({
      nowIso: () => "2026-04-07T12:30:00.000Z",
      guestStorageFactory: () => ({
        loadCurrentSnapshot: vi.fn(async () => ({
          status: "ready" as const,
          snapshot: readySnapshot,
          summary: summarizeClassroomPlannerGuestSnapshot(readySnapshot),
        })),
        saveSnapshot,
        initializeEmptySnapshot: vi.fn(),
        clearCurrentSnapshot: vi.fn(),
      }),
    });
    await flushGuestController();
    await vi.waitFor(() => {
      expect(harness.getState().selectedRosterId.value).toBe("roster-1");
      expect(harness.getState().isBootstrapping.value).toBe(false);
    });

    await harness.getState().openGroupingWorkspace();

    expect(harness.getState().currentScreen.value).toBe("planner");
    expect(harness.getState().plannerInitialView.value).toBe("groups");
    expect(harness.getState().selectedTemplateId.value).toBe("template-1");
    expect(harness.getState().guestPlannerState.template.value?.id).toBe("template-1");

    const savedSnapshot = (saveSnapshot.mock.calls as unknown[][]).at(-1)?.[0] as
      | {
          grouping_draft: { template_local_id: string | null } | null;
          ui_state: { selected_template_local_id: string | null };
        }
      | undefined;
    expect(savedSnapshot?.grouping_draft?.template_local_id).toBe("template-1");
    expect(savedSnapshot?.ui_state.selected_template_local_id).toBe("template-1");
  });

  it("prepares the selected overview grouping draft without leaving the public overview screen", async () => {
    let snapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-grouping-context-2",
      created_at: "2026-04-07T12:00:00.000Z",
      updated_at: "2026-04-07T12:00:00.000Z",
      expires_at: "2026-04-21T12:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [
            { id: "student-1", display_name: "Ada" },
            { id: "student-2", display_name: "Bo" },
          ],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "G20",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
      ],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: "template-1",
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    const saveSnapshot = vi.fn(async (nextSnapshot: typeof snapshot) => {
      snapshot = nextSnapshot;
    });
    const harness = mountGuestControllerHarness({
      nowIso: () => "2026-04-07T12:30:00.000Z",
      guestStorageFactory: () => ({
        loadCurrentSnapshot: vi.fn(async () => ({
          status: "ready" as const,
          snapshot,
          summary: summarizeClassroomPlannerGuestSnapshot(snapshot),
        })),
        saveSnapshot,
        initializeEmptySnapshot: vi.fn(),
        clearCurrentSnapshot: vi.fn(),
      }),
    });
    await flushGuestController();
    await vi.waitFor(() => {
      expect(harness.getState().selectedRosterId.value).toBe("roster-1");
    });

    const prepared = await harness.getState().prepareOverviewDistributionScope("grouping");

    expect(prepared, harness.getState().plannerActionError.value ?? "prepare returned false").toBe(true);
    expect(harness.getState().currentScreen.value).toBe("class-workspace");
    expect(harness.getState().plannerInitialView.value).toBe("groups");
    expect(harness.getState().guestPlannerState.draft.value?.draft_kind).toBe("grouping");
    expect(harness.getState().guestPlannerState.template.value?.id).toBe("template-1");
    expect(snapshot.ui_state.current_screen).toBe("class-workspace");
    expect(snapshot.ui_state.selected_template_local_id).toBe("template-1");
    expect(snapshot.grouping_draft?.template_local_id).toBe("template-1");
  });
});
