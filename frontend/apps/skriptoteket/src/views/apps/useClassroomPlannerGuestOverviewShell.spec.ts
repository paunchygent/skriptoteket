/**
 * Klassrumskartan guest controller tests.
 *
 * These tests verify that the public guest controller bootstraps from the
 * browser-owned snapshot seam and persists checkpoint-2 overview authoring
 * there instead of relying on the authenticated route shell.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

import { createClassroomPlannerGuestSnapshotFromSeed } from "./classroomPlannerGuestSnapshotMapping";
import { summarizeClassroomPlannerGuestSnapshot } from "./classroomPlannerGuestSnapshot";
import { useClassroomPlannerGuestController } from "./useClassroomPlannerGuestController";

function mountGuestOverviewHarness(
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
        throw new Error("Guest overview harness did not expose state.");
      }
      return exposedState;
    },
  };
}

async function flushGuestOverview(): Promise<void> {
  await nextTick();
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
}

describe("useClassroomPlannerGuestController", () => {
  it("initializes an empty browser-owned snapshot when none exists yet", async () => {
    const emptySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-1",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [],
      templates: [],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: null,
        selected_template_id: null,
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });
    const initializeEmptySnapshot = vi.fn(async () => ({
      status: "ready" as const,
      snapshot: emptySnapshot,
      summary: summarizeClassroomPlannerGuestSnapshot(emptySnapshot),
    }));

    const harness = mountGuestOverviewHarness({
      guestStorageFactory: () => ({
        loadCurrentSnapshot: vi.fn(async () => ({
          status: "missing" as const,
          snapshot: null,
          summary: null,
        })),
        saveSnapshot: vi.fn(),
        initializeEmptySnapshot,
        clearCurrentSnapshot: vi.fn(),
      }),
    });
    await flushGuestOverview();

    expect(initializeEmptySnapshot).toHaveBeenCalledOnce();
    expect(harness.getState().isBootstrapping.value).toBe(false);
    expect(harness.getState().bootstrapError.value).toBeNull();
    expect(harness.getState().availableRosters.value).toEqual([]);
    expect(harness.getState().availableTemplates.value).toEqual([]);
  });

  it("hydrates snapshot-backed overview state and persists later selection changes", async () => {
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-2",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
        {
          id: "roster-2",
          name: "NA25A",
          students: [{ id: "student-2", display_name: "Bo" }],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "Sal 101",
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
        current_screen: "planner",
        planner_initial_view: "rules",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    const saveSnapshot = vi.fn(async () => undefined);
    const harness = mountGuestOverviewHarness({
      nowIso: () => "2026-04-05T09:30:00.000Z",
      guestStorageFactory: () => ({
        loadCurrentSnapshot: vi.fn(async () => ({
          status: "ready" as const,
          snapshot: readySnapshot,
          summary: {
            snapshot_id: readySnapshot.snapshot_id,
            profile: readySnapshot.profile,
            created_at: readySnapshot.created_at,
            updated_at: readySnapshot.updated_at,
            expires_at: readySnapshot.expires_at,
            roster_count: readySnapshot.rosters.length,
            template_count: readySnapshot.templates.length,
            smart_rule_set_count: readySnapshot.smart_rule_sets.length,
            checkpoint_count: readySnapshot.checkpoint_descriptors.length,
            has_grouping_draft: false,
            has_seating_draft: false,
          },
        })),
        saveSnapshot,
        initializeEmptySnapshot: vi.fn(),
        clearCurrentSnapshot: vi.fn(),
      }),
    });
    await flushGuestOverview();

    expect(harness.getState().selectedRosterId.value).toBe("roster-1");
    expect(harness.getState().selectedTemplateId.value).toBe("template-1");
    expect(harness.getState().classWorkspaceSummary.value?.roster.name).toBe("SA24D");
    expect(saveSnapshot).toHaveBeenCalledOnce();
    const firstSavedSnapshot = (saveSnapshot.mock.calls as unknown[][])[0]?.[0] as
      | { ui_state: { current_screen: string; planner_initial_view: string } }
      | undefined;
    expect(firstSavedSnapshot?.ui_state.current_screen).toBe("class-workspace");
    expect(firstSavedSnapshot?.ui_state.planner_initial_view).toBe("groups");

    await harness.getState().selectWorkspaceRoster("roster-2");

    expect(harness.getState().selectedRosterId.value).toBe("roster-2");
    expect(saveSnapshot).toHaveBeenCalledTimes(2);
    const secondSavedSnapshot = (saveSnapshot.mock.calls as unknown[][])[1]?.[0] as
      | { ui_state: { selected_roster_local_id: string | null } }
      | undefined;
    expect(secondSavedSnapshot?.ui_state.selected_roster_local_id).toBe("roster-2");
  });

  it("persists a guest-created roster in the browser-owned snapshot and selects it", async () => {
    const randomUuidSpy = vi
      .spyOn(globalThis.crypto, "randomUUID")
      .mockReturnValue("11111111-1111-4111-8111-111111111111");
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-3",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [],
      templates: [],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: null,
        selected_template_id: null,
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });
    const saveSnapshot = vi.fn(async () => undefined);
    const harness = mountGuestOverviewHarness({
      nowIso: () => "2026-04-05T09:30:00.000Z",
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
    await flushGuestOverview();

    const savedRoster = await harness.getState().saveRoster({
      existingRoster: null,
      name: "SA24D",
      students: [{ id: "student-1", display_name: "Ada" }],
    });

    expect(savedRoster.id).toBe("11111111-1111-4111-8111-111111111111");
    expect(harness.getState().selectedRosterId.value).toBe("11111111-1111-4111-8111-111111111111");
    expect(harness.getState().availableRosters.value).toEqual([
      {
        id: "11111111-1111-4111-8111-111111111111",
        name: "SA24D",
        students: [{ id: "student-1", display_name: "Ada" }],
      },
    ]);
    const savedSnapshot = (saveSnapshot.mock.calls as unknown[][]).at(-1)?.[0] as
      | {
          rosters: Array<{ local_id: string; name: string }>;
          ui_state: { selected_roster_local_id: string | null };
        }
      | undefined;
    expect(savedSnapshot?.rosters).toEqual([
      expect.objectContaining({
        local_id: "11111111-1111-4111-8111-111111111111",
        name: "SA24D",
      }),
    ]);
    expect(savedSnapshot?.ui_state.selected_roster_local_id).toBe("11111111-1111-4111-8111-111111111111");

    randomUuidSpy.mockRestore();
  });

  it("keeps template selection cleared when deleting the currently selected template", async () => {
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-4",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [],
      templates: [
        {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
        {
          id: "template-2",
          name: "Sal 102",
          grid_cols: 9,
          grid_rows: 7,
          seats: [{ id: "seat-2", x: 2, y: 2, zone: "middle" }],
          fixtures: [],
        },
      ],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: null,
        selected_template_id: "template-1",
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });
    const saveSnapshot = vi.fn(async () => undefined);
    const harness = mountGuestOverviewHarness({
      nowIso: () => "2026-04-05T09:30:00.000Z",
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
    await flushGuestOverview();

    await harness.getState().deleteTemplate("template-1");

    expect(harness.getState().selectedTemplateId.value).toBeNull();
    expect(harness.getState().availableTemplates.value).toEqual([
      {
        id: "template-2",
        name: "Sal 102",
        grid_cols: 9,
        grid_rows: 7,
        seats: [{ id: "seat-2", x: 2, y: 2, zone: "middle" }],
        fixtures: [],
      },
    ]);
    const savedSnapshot = (saveSnapshot.mock.calls as unknown[][]).at(-1)?.[0] as
      | { templates: unknown[]; ui_state: { selected_template_local_id: string | null } }
      | undefined;
    expect(savedSnapshot?.templates).toEqual([
      expect.objectContaining({
        local_id: "template-2",
        name: "Sal 102",
      }),
    ]);
    expect(savedSnapshot?.ui_state.selected_template_local_id).toBeNull();
  });

  it("restores the guest planner screen from a browser-owned grouping draft", async () => {
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-5",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
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
      templates: [],
      smart_rule_sets: [],
      grouping_draft: {
        draft: {
          id: "draft-grouping-1",
          roster_id: "roster-1",
          draft_kind: "grouping",
          template_id: null,
          smart_enabled: false,
          use_history: false,
          grouping_seating_distance_enabled: false,
          status: "active",
          revision: 2,
          last_opened_at: "2026-04-05T09:10:00.000Z",
        },
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [
            { id: "student-1", display_name: "Ada" },
            { id: "student-2", display_name: "Bo" },
          ],
        },
        template: null,
        groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
        group_assignments: [{ student_id: "student-1", group_id: "group-1" }],
        seat_assignments: [],
        history_status: { can_undo: false, can_redo: false },
      },
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: null,
        current_screen: "planner",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    const harness = mountGuestOverviewHarness({
      guestStorageFactory: () => ({
        loadCurrentSnapshot: vi.fn(async () => ({
          status: "ready" as const,
          snapshot: readySnapshot,
          summary: summarizeClassroomPlannerGuestSnapshot(readySnapshot),
        })),
        saveSnapshot: vi.fn(),
        initializeEmptySnapshot: vi.fn(),
        clearCurrentSnapshot: vi.fn(),
      }),
    });
    await flushGuestOverview();

    expect(harness.getState().currentScreen.value).toBe("planner");
    expect(harness.getState().plannerInitialView.value).toBe("groups");
    expect(harness.getState().guestPlannerState.draft.value?.id).toBe("draft-grouping-1");
    expect(harness.getState().guestPlannerState.roster.value?.id).toBe("roster-1");
    expect(harness.getState().guestPlannerState.groups.value).toEqual([
      expect.objectContaining({ id: "group-1", name: "Grupp 1" }),
    ]);
  });

  it("returns to the class workspace and clears the injected guest planner state", async () => {
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-6",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
      ],
      smart_rule_sets: [],
      grouping_draft: {
        draft: {
          id: "draft-grouping-2",
          roster_id: "roster-1",
          draft_kind: "grouping",
          template_id: null,
          smart_enabled: false,
          use_history: false,
          grouping_seating_distance_enabled: false,
          status: "active",
          revision: 1,
          last_opened_at: "2026-04-05T09:10:00.000Z",
        },
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
        template: null,
        groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
        group_assignments: [],
        seat_assignments: [],
        history_status: { can_undo: false, can_redo: false },
      },
      seating_draft: null,
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: "template-1",
        current_screen: "planner",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });
    const saveSnapshot = vi.fn(async () => undefined);
    const harness = mountGuestOverviewHarness({
      nowIso: () => "2026-04-05T09:30:00.000Z",
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
    await flushGuestOverview();

    await harness.getState().selectPlannerWorkspaceMode("overview");

    expect(harness.getState().currentScreen.value).toBe("class-workspace");
    expect(harness.getState().guestPlannerState.draft.value).toBeNull();
    const savedSnapshot = (saveSnapshot.mock.calls as unknown[][]).at(-1)?.[0] as
      | { ui_state: { current_screen: string; planner_initial_view: string } }
      | undefined;
    expect(savedSnapshot?.ui_state.current_screen).toBe("class-workspace");
    expect(savedSnapshot?.ui_state.planner_initial_view).toBe("groups");
  });

  it("reopens an existing grouping draft from overview and flips the shell back to planner", async () => {
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-7",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
      ],
      smart_rule_sets: [],
      grouping_draft: {
        draft: {
          id: "draft-grouping-3",
          roster_id: "roster-1",
          draft_kind: "grouping",
          template_id: null,
          smart_enabled: false,
          use_history: false,
          grouping_seating_distance_enabled: false,
          status: "active",
          revision: 1,
          last_opened_at: "2026-04-05T09:10:00.000Z",
        },
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
        template: null,
        groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
        group_assignments: [],
        seat_assignments: [],
        history_status: { can_undo: false, can_redo: false },
      },
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
    const harness = mountGuestOverviewHarness({
      nowIso: () => "2026-04-05T09:30:00.000Z",
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
    await flushGuestOverview();

    expect(harness.getState().currentScreen.value).toBe("class-workspace");
    expect(harness.getState().guestPlannerState.draft.value).toBeNull();

    await harness.getState().openGroupingWorkspace();

    expect(harness.getState().currentScreen.value).toBe("planner");
    expect(harness.getState().plannerInitialView.value).toBe("groups");
    expect(harness.getState().selectedTemplateId.value).toBe("template-1");
    expect(harness.getState().guestPlannerState.draft.value?.id).toBe("draft-grouping-3");
    const savedSnapshot = (saveSnapshot.mock.calls as unknown[][]).at(-1)?.[0] as
      | {
          ui_state: {
            current_screen: string;
            planner_initial_view: string;
            selected_template_local_id: string | null;
          };
        }
      | undefined;
    expect(savedSnapshot?.ui_state.current_screen).toBe("planner");
    expect(savedSnapshot?.ui_state.planner_initial_view).toBe("groups");
    expect(savedSnapshot?.ui_state.selected_template_local_id).toBe("template-1");
  });

  it("creates a fresh seating draft when the requested classroom changed", async () => {
    const randomUuidSpy = vi
      .spyOn(globalThis.crypto, "randomUUID")
      .mockReturnValue("11111111-1111-4111-8111-222222222222");
    const readySnapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-8",
      created_at: "2026-04-05T09:00:00.000Z",
      updated_at: "2026-04-05T09:00:00.000Z",
      expires_at: "2026-04-19T09:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [
            { id: "seat-1", x: 1, y: 1, zone: "front" },
            { id: "seat-2", x: 2, y: 1, zone: "front" },
          ],
          fixtures: [],
        },
        {
          id: "template-2",
          name: "Sal 202",
          grid_cols: 8,
          grid_rows: 6,
          seats: [
            { id: "seat-3", x: 1, y: 1, zone: "front" },
            { id: "seat-4", x: 2, y: 1, zone: "front" },
            { id: "seat-5", x: 3, y: 1, zone: "front" },
          ],
          fixtures: [],
        },
      ],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: {
        draft: {
          id: "draft-seating-1",
          roster_id: "roster-1",
          draft_kind: "seating",
          template_id: "template-1",
          smart_enabled: false,
          use_history: false,
          grouping_seating_distance_enabled: false,
          status: "active",
          revision: 1,
          last_opened_at: "2026-04-05T09:10:00.000Z",
        },
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [{ id: "student-1", display_name: "Ada" }],
        },
        template: {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [
            { id: "seat-1", x: 1, y: 1, zone: "front" },
            { id: "seat-2", x: 2, y: 1, zone: "front" },
          ],
          fixtures: [],
        },
        groups: [],
        group_assignments: [],
        seat_assignments: [],
        history_status: { can_undo: false, can_redo: false },
      },
      checkpoint_descriptors: [],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: "template-2",
        current_screen: "class-workspace",
        planner_initial_view: "seats",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });
    const saveSnapshot = vi.fn(async () => undefined);
    const harness = mountGuestOverviewHarness({
      nowIso: () => "2026-04-05T09:30:00.000Z",
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
    await flushGuestOverview();

    await harness.getState().openSeatingWorkspace("template-2");

    expect(harness.getState().currentScreen.value).toBe("planner");
    expect(harness.getState().plannerInitialView.value).toBe("seats");
    expect(harness.getState().guestPlannerState.draft.value?.id).toBe(
      "11111111-1111-4111-8111-222222222222",
    );
    expect(harness.getState().guestPlannerState.template.value?.id).toBe("template-2");
    const savedSnapshot = (saveSnapshot.mock.calls as unknown[][]).at(-1)?.[0] as
      | {
          ui_state: { current_screen: string; selected_template_local_id: string | null };
          seating_draft: { local_id: string; template_local_id: string | null } | null;
        }
      | undefined;
    expect(savedSnapshot?.ui_state.current_screen).toBe("planner");
    expect(savedSnapshot?.ui_state.selected_template_local_id).toBe("template-2");
    expect(savedSnapshot?.seating_draft?.local_id).toBe("11111111-1111-4111-8111-222222222222");
    expect(savedSnapshot?.seating_draft?.template_local_id).toBe("template-2");

    randomUuidSpy.mockRestore();
  });
});
